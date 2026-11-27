"""Translate individual corpus units and ask cc to validate their generated C."""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from decimal import Decimal
from functools import partial
from importlib import import_module
from pathlib import Path

if __package__:
    from .api_coverage import Coverage, read_catalogues, record_calls
    from .t24_components import read_component_members
else:
    from api_coverage import Coverage, read_catalogues, record_calls
    from t24_components import read_component_members

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
COMPILER = import_module("jbcc.compiler")
RUNTIME = COMPILER.read_runtime()
R07_LA_PARAMETER_STUB = ROOT / "tools/corpus_stubs/r07/I_F.LA.PARAMETER"

T24_SOURCE_FIXES = {
    "STEST.AZ.PD.DATES.CHK": (
        re.compile(
            r"^[ \t]*[\w.]+[ \t]*=[ \t]*[\w.]+<(?P<edit>\.AZ\.SLS\.TYPE\.I)(?=[ \t]*,)",
            re.M,
        ),
        "AZ.SLS.TYPE.I",
    ),
    "TK.VALIDATE.SYSGEN.FILES": (
        re.compile(
            r"^[ \t]*(?:IF[ \t]+)?(?P<edit>1ST\.RECORD)(?=[ \t]*=|[ \t]+THEN\b)",
            re.M,
        ),
        "FIRST.RECORD",
    ),
    "LIST.DATA": (
        re.compile(
            r'^[ \t]*THE\.ARGS[ \t]*=[ \t]*"F\.\.\.":[ \t]*(?P<edit>FM)(?=[ \t]*:"F\.\.\.")',
            re.M,
        ),
        "@FM",
    ),
}

R07_DECIMAL_COEFFICIENT = (
    re.compile(
        r"^[ \t]*[A-Za-z]+[0-9]+[ \t]*=[ \t]*"
        r"(?P<edit>[+-]?[0-9]+\.[0-9]+[Ee][+-]?[0-9]{1,3})[ \t]*$",
        re.M,
    ),
    lambda value: format(Decimal(value), "f"),
)

R07_SOURCE_FIXES = {
    "STEST.AZ.PD.DATES.CHK": T24_SOURCE_FIXES["STEST.AZ.PD.DATES.CHK"],
    "COMPARE.DB.JBASE": (
        re.compile(
            r"^[ \t]*\$INCLUDE[ \t]+(?P<edit>/usr/jbc/include/JBC\.h)(?=[ \t]*(?:;|$))",
            re.M,
        ),
        "JBC.h",
    ),
    "MG.EOD.REDEFINE.CONTRACT.RATES": (
        re.compile(
            r"^[ \t]*CHECK\.DATE[ \t]*=[ \t]*CR\.REC\(CR\.EVENT\.DATE"
            r"(?P<edit>,[ \t]*1)(?=\)<1,[ \t]*I>)",
            re.M,
        ),
        "",
    ),
    "TU.LIB.STD.CDF": R07_DECIMAL_COEFFICIENT,
    "TU.LIB.STD.INV": R07_DECIMAL_COEFFICIENT,
}

R13_SOURCE_FIXES = {
    "STEST.AZ.PD.DATES.CHK": T24_SOURCE_FIXES["STEST.AZ.PD.DATES.CHK"],
}

# R19 keeps each source in a module tree, so its fixes name the path from
# the extract root.
R19_SOURCE_FIXES = {
    # Two assignments on one line without a separator.
    "CALEND/CALEND_ReserveAccounts/Source/Private/CALEND.PAY.RESERVE.ACCOUNT.LOAD.b": (
        re.compile(
            r"^[ \t]*CalendParameterRecord[ \t]*=[ \t]*''(?P<edit>[ \t]+)(?=ParamError[ \t]*=)",
            re.M,
        ),
        "; ",
    ),
    # PRINT ... : '      :     ' FMT(...) lacks the : before the second FMT.
    "ATMFRM/ATMFRM_Mapping/Source/Private/AT.GEN.ISO.RES.MSG.b": (
        re.compile(
            r"^[ \t]*PRINT FMT\(CURR\.HEAD\.ELEMENT, '3\" \"L'\)[ \t]*:[ \t]*'      :     '(?P<edit>[ \t]+)(?=FMT\()",
            re.M,
        ),
        " : ",
    ),
    # The leading-dot selector seen in R07, R10 and R13, in the SEAT test.
    "SE/SE_TestRetail/Source/Private/STEST.AZ.PD.DATES.CHK.b": T24_SOURCE_FIXES[
        "STEST.AZ.PD.DATES.CHK"
    ],
    # Two DAS inserts end an EQU with a comma and start the next line with
    # EQU again. The local reference (jpp, 201015.001) reports a syntax
    # error, while R19's own compiler evidently accepts it. Drop the comma.
    **{
        f"AA/{module}/Source/Public/I_DAS.{table}": (
            re.compile(
                r"^[ \t]*EQU[ \t]+\S+[ \t]+TO[ \t]+\S+?(?P<edit>,)[ \t]*\r?$(?=\n[ \t]*EQU\b)",
                re.M,
            ),
            "",
        )
        for module, table in (
            ("AA_ProductManagement", "AA.PRODUCT.DESIGNER"),
            ("AA_ProductFramework", "AA.PRODUCT.LINE"),
        )
    },
}

# Release extracts with the folder that holds the fixed files (None when
# fixes name paths from the root) and the fixes for that release.
RELEASE_SOURCE_FIXES = {
    "200707-R07": (Path("GLOBUS.BP"), R07_SOURCE_FIXES),
    "201307-R13": (Path("T24.BP"), R13_SOURCE_FIXES),
    "201809-R19": (None, R19_SOURCE_FIXES),
}

# R19's test framework components (SE_TestFramework, SE_TestBankingFramework,
# SE_TestOtherApplication, SE_TestRetail, SE_TestToolsFramework) hold the
# SEAT test harness and its tests, which are out of scope for production
# translation.
TEST_FRAMEWORK = re.compile(r"^SE/SE_Test[^/]*/")
TEST_FRAMEWORK_REASON = "T24 test framework component"


def excluded_reason(release, relative):
    local = LOCAL_ROUTINES.get(release, {})
    return local.get(relative, TEST_FRAMEWORK_REASON)


# Component members stubbed for testing with --t24-stub-members: each
# accepts any arguments, as scalars or matrices, and every use is reported.
T24_MEMBER_STUBS = {
    # A Java varargs helper: declared with 3 parameters, called by the SEAT
    # tests with 2 to 8 (instance, "getTermRate", currency, ...).
    "TF.L3Helper.testPublishedMethod": "function",
    # Declarations that omit the () matrix marker on a parameter every
    # caller passes with MAT, as in TransferBalance's "MatrAccount string"
    # for MAT R.MATACCOUNT.
    **{
        name: "subroutine"
        for name in (
            "AA.ActivityMessaging.FullScheduleDetails",
            "AU.API.TransferBalance",
            "GA.Foundation.OfsPublishUpdate",
            "MI.AverageBalances.BookDatePcEntriesBuild",
        )
    },
    # Methods R19 calls that no component definition in the dump declares.
    **{
        name: "subroutine"
        for name in (
            "OA.Decision.DecisionDefaultValues",
            "PP.InwardCreditTransferInitiationService.mapSingleToPORTransaction",
            "PP.InwardGenericTransactions.PpInCreditTransferWrite",
            "PP.OutwardInterfaceService.doOutwardInstMapping",
            "PP.StaticDataGUI.LanguageMapping",
            "PP.StaticDataGUI.WritePPCompany",
            "PW.Foundation.ProcessDefCatalogueCheckFields",
            "TF.Core.DumpCommon",
            "USREGS.RegD.RegdGenerateDealslip",
            # EB.CODE.DIAGNOSTICS.ACTION drives TF.Core's coverage and call
            # recording; TF.Core declares none of these.
            "TF.Core.CoverageReport",
            "TF.Core.CoverageReset",
            "TF.Core.CoverageStop",
            "TF.Core.DumpCalls",
            "TF.Core.StartRecordCalls",
            "TF.Core.StopRecordCalls",
            # MessageAcceptanceService.processInward writes each inward
            # message type through PP.InwardGenericTransactions.
            *(
                f"PP.InwardGenericTransactions.PpIn{table}Write"
                for table in (
                    "CancellationRequest",
                    "DdReversalInitiation",
                    "DirectDebit",
                    "DirectDebitInit",
                    "DirectDebitReturn",
                    "DirectDebitReversal",
                    "Return",
                    "Roi",
                )
            ),
            "PP.InwardCreditTransferInitiationService.mapSingleToPORPartyDebit",
            "PP.LocalClearingService.doOutwardMapping",
            "PP.OutwardInterfaceService.doOutwardRTGSMapping",
        )
    },
    # The OB_PMT mapping routines call 40 mappers, map<message>toPOR<part>;
    # the only PP.InwardGenericTransactions definition in the dump declares
    # none of them. Names as the sources spell them.
    **{
        f"PP.InwardGenericTransactions.map{message}toPOR{part}": "subroutine"
        for message, parts in {
            "CT": "AdditionalInf PartyCredit PartyDebit RemInfStruct",
            "DD": "AdditionalInf DebitAuthInfo PartyCredit PartyDebit RemInfStruct",
            "DDR": "AdditionalInfo DebitAuthInf PartyCredit PartyDebit RemInfStruct",
            "DDRDRF": "AdditionalInfo DebitAuthInf PartyCredit PartyDebit RemInfStruct",
            "RDDI": "AdditionalInf DebitAuthInfo PartyCredit PartyDebit RemInfStruct",
            "RT": "AdditionalInf PartyCredit PartyDebit RemInfStruct",
        }.items()
        for part in ("Transaction", "Information", *parts.split())
    },
}


def stub_component_members(members):
    for name, kind in T24_MEMBER_STUBS.items():
        owner = name.rsplit(".", 1)[0].casefold()
        members[name.casefold()] = ("public", kind, None, owner)
    return members


# Files kept in an extract that are not part of the Temenos release.
LOCAL_ROUTINES = {
    "201307-R13": {
        # Its own header and CVS log name Raiffeisen Bank Polska, and its
        # I_F.PL.* includes are not in the dump.
        "T24.BP/V.PL.B2LIM.NET": "Raiffeisen Bank Polska local routine",
    },
}


def fix_t24_source(path, source, *, root, fixes):
    if path.name not in T24_SOURCE_FIXES and not any(
        path.name in release_fixes
        or any(Path(key).name == path.name for key in release_fixes)
        for _, release_fixes in RELEASE_SOURCE_FIXES.values()
    ):
        return source
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return source
    rule = None
    if relative == Path(path.name):
        rule = T24_SOURCE_FIXES.get(path.name)
    elif root.name in RELEASE_SOURCE_FIXES:
        folder, release_fixes = RELEASE_SOURCE_FIXES[root.name]
        if folder is None:
            rule = release_fixes.get(relative.as_posix())
        elif relative.parent == folder and (
            path.name != "COMPARE.DB.JBASE"
            or (root / folder / "JBC.h").is_file()
        ):
            rule = release_fixes.get(path.name)
    if rule is None:
        return source
    pattern, replacement = rule

    def replace(match):
        start = match.start("edit")
        before = match["edit"]
        after = replacement(before) if callable(replacement) else replacement
        fix = {
            "file": relative.as_posix(),
            "line": source.count("\n", 0, start) + 1,
            "column": start - source.rfind("\n", 0, start),
            "before": before,
            "after": after,
        }
        if fix not in fixes:
            fixes.append(fix)
        return (
            source[match.start() : start]
            + after
            + source[match.end("edit") : match.end()]
        )

    return pattern.sub(replace, source)


def group(message):
    # Preserve keyword spellings for unsupported statements. Group arbitrary
    # user identifiers together and retain full diagnostics in the file report.
    for prefix in (
        "unknown variable or unsupported function",
        "unknown label",
        "include file",
        "ambiguous include file",
        "unassigned variable",
    ):
        if message.startswith(prefix):
            return prefix
    return message


def read_file_kinds(catalogue, extract):
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        kinds = dict(
            db.execute(
                "SELECT rel, kind FROM file_path WHERE extract = ?", (extract,)
            )
        )
    if not kinds:
        raise ValueError(f"no files for extract '{extract}' in {catalogue}")
    return kinds


def display_path(path, root):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


DOMAIN_INSERT = re.compile(r"I_([A-Za-z0-9]+)_([A-Za-z0-9]+)")


def read_domain_classes(db, extract):
    """Map (service, class) to the field lists of matching .domain classes.

    T24 generates I_<Service>_<Class> from the class in the .domain model of
    the component whose name ends in <Service>. A component's .component and
    .domain files share a folder, normally Definition. The catalog lists the
    fields in declaration order; associations count as fields."""
    services = {}
    for relative, name in db.execute(
        "SELECT rel, component_name FROM file_path WHERE extract = ? AND kind = 'component'",
        (extract,),
    ):
        if name:
            folder = Path(relative).parent
            services.setdefault(folder, set()).add(name.rsplit(".", 1)[-1])
    fields = {}
    for relative, cls, name in db.execute(
        "SELECT f.rel, d.class, d.name FROM domain_field d "
        "JOIN file_path f ON f.id = d.file_id WHERE f.extract = ? "
        "ORDER BY f.rel, d.class, d.position",
        (extract,),
    ):
        for service in services.get(Path(relative).parent, ()):
            fields.setdefault((service, cls), {}).setdefault(
                relative, []
            ).append(name)
    return fields


def domain_insert_text(name, cls, service, relative, fields):
    lines = [
        "*" + "-" * 88,
        f"* Insert describing the complex type: {cls} used by the service: {service}",
        f"* Generated by the jbcc corpus checker from {relative}",
        "*" + "-" * 88,
    ]
    lines += [f"EQU {cls}.{field} TO {n}" for n, field in enumerate(fields, 1)]
    return "\n".join(lines) + "\n"


class IncludeIndex:
    def __init__(self, catalogue, root, domain_inserts=None):
        self.root = root
        self.scopes = {}
        self.includes = {}
        self.domain_inserts = (
            domain_inserts.resolve() if domain_inserts else None
        )
        self.domain_classes = {}
        uri = catalogue.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as db:
            if domain_inserts is not None:
                self.domain_classes = read_domain_classes(db, root.name)
            rows = db.execute(
                "SELECT rel, kind, module, component FROM file_path WHERE extract = ? "
                "AND kind IN ('jbc_source', 'jbc_include') ORDER BY rel",
                (root.name,),
            )
            for relative, kind, module, component in rows:
                path = Path(relative)
                if component:
                    self.scopes[path] = (module, component)
                if kind == "jbc_include":
                    self.includes.setdefault(path.name, []).append(path)

    def resolve(self, path, name, directories, token, lookups):
        source = display_path(path, self.root)
        entry = {
            "file": source,
            "line": token.line,
            "column": token.column,
            "target": name,
        }
        lookups.append(entry)

        def found(candidate, rule):
            candidate = candidate.resolve()
            entry.update(
                status="resolved",
                rule=rule,
                resolved=display_path(candidate, self.root),
            )
            return candidate

        def choose(candidates, rule):
            if len(candidates) == 1:
                return found(self.root / candidates[0], rule)
            names = [candidate.as_posix() for candidate in candidates]
            # Byte-identical copies, as R19's two I_DAS.POR.CLG.IN.SETTLEMENT
            # .PENDING, make the choice irrelevant: take the first, report all.
            contents = {(self.root / c).read_bytes() for c in candidates}
            if len(contents) == 1:
                result = found(self.root / candidates[0], rule)
                entry.update(identical_copies=names)
                return result
            entry.update(status="ambiguous", rule=rule, candidates=names)
            COMPILER.directive_error(
                token, f"ambiguous include file '{name}': {', '.join(names)}"
            )

        candidate = path.parent / name
        if candidate.is_file():
            return found(
                candidate,
                "source directory"
                if not Path(name).is_absolute()
                else "absolute path",
            )
        candidates = [
            relative
            for relative in self.includes.get(name, [])
            if (self.root / relative).is_file()
        ]
        scope = self.scopes.get(Path(source))
        local = [
            relative
            for relative in candidates
            if scope and self.scopes.get(relative) == scope
        ]
        if local:
            return choose(local, "component")
        for directory in directories:
            candidate = directory / name
            if candidate.is_file():
                return found(candidate, "include search path")
        if candidates:
            return choose(candidates, "release index")
        generated = self.generate_domain_insert(name, token, entry)
        if generated is not None:
            return generated
        entry.update(status="missing")
        if self.domain_inserts is not None and DOMAIN_INSERT.fullmatch(name):
            # A generated insert whose class no catalogued .domain declares.
            entry.update(domain_class="absent")
        return None

    def generate_domain_insert(self, name, token, entry):
        match = DOMAIN_INSERT.fullmatch(name)
        if self.domain_inserts is None or not match:
            return None
        service, cls = match.groups()
        models = self.domain_classes.get((service, cls), {})
        layouts = {tuple(fields) for fields in models.values()}
        if len(layouts) > 1:
            names = sorted(models)
            entry.update(
                status="ambiguous", rule="domain model", candidates=names
            )
            COMPILER.directive_error(
                token,
                f"ambiguous domain class for '{name}': {', '.join(names)}",
            )
        if not layouts:
            return None
        relative = sorted(models)[0]
        path = self.domain_inserts / name
        text = domain_insert_text(
            name, cls, service, relative, models[relative]
        )
        if not path.is_file() or path.read_text() != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{name}.{os.getpid()}")
            temporary.write_text(text)
            temporary.replace(path)
        entry.update(status="generated", rule="domain model", domain=relative)
        return path.resolve()


worker_include_index = None
worker_component_members = None


def initialize_worker(include_index, component_members):
    global worker_include_index, worker_component_members
    worker_include_index = include_index
    worker_component_members = component_members


def check(
    relative,
    root,
    directories,
    source_encoding='utf-8',
    defer_unassigned_reads=False,
    t24_source_fixes=False,
    quiet_next_warnings=False,
    collect_apis=False,
    *,
    catalog_kind=None,
    stub_r07_la_parameter=False,
    stub_void_results=False,
    relax_access=False,
    exclude_local_routines=False,
    exclude_test_framework=False,
    exclude_missing_domains=False,
    include_index=None,
    component_members=None,
):
    path = root / relative
    fixes = []
    calls = []
    stubs = []
    lookups = []
    package_directives = []
    if catalog_kind == "jbc_include" or (
        catalog_kind is None and path.name.startswith("I_")
    ):
        return (
            relative,
            "include fragment",
            "",
            [],
            fixes,
            0,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    if catalog_kind == "c_header":
        return (
            relative,
            "C header",
            "",
            [],
            fixes,
            0,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    if (
        exclude_local_routines
        and relative in LOCAL_ROUTINES.get(root.name, {})
        or exclude_test_framework
        and TEST_FRAMEWORK.match(relative)
    ):
        return (
            relative,
            "excluded",
            "",
            [],
            fixes,
            0,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    if catalog_kind not in (None, "jbc_source"):
        return (
            relative,
            "other catalog file",
            "",
            [],
            fixes,
            0,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    suppressed_next_warnings = 0

    def count_next_warning(_message):
        nonlocal suppressed_next_warnings
        suppressed_next_warnings += 1

    def filter_source(source_path, source):
        if (
            stub_r07_la_parameter
            and source_path.name == R07_LA_PARAMETER_STUB.name
            and source_path.resolve() == R07_LA_PARAMETER_STUB
            and not stubs
        ):
            stubs.append(source_path.name)
        if t24_source_fixes:
            return fix_t24_source(source_path, source, root=root, fixes=fixes)
        return source

    try:
        if stub_r07_la_parameter:
            directories = [*directories, R07_LA_PARAMETER_STUB.parent]
        source_filter = (
            filter_source if t24_source_fixes or stub_r07_la_parameter else None
        )
        resolver = (
            partial(include_index.resolve, lookups=lookups)
            if include_index is not None
            else None
        )
        unit = COMPILER.compile_unit(
            path,
            directories,
            source_encoding=source_encoding,
            separate_external_arities=True,
            defer_unassigned_reads=defer_unassigned_reads,
            source_filter=source_filter,
            include_resolver=resolver,
            package_directives=package_directives,
            component_members=component_members,
            # Corpus results reflect the headers given with -I, never
            # jbcc's built-in JBC.h.
            builtin_includes=False,
            stub_void_results=stub_void_results,
            relax_access=relax_access,
            next_warning=count_next_warning if quiet_next_warnings else None,
            api_call=record_calls(calls) if collect_apis else None,
        )
        externals = {}
        first_signatures = {}
        linkage_diagnostic = ""
        for target, kinds, is_function in unit.calls:
            if unit.routine and unit.routine.word == target.word:
                formals = tuple(unit.formals.values())
                if (
                    is_function != unit.is_function
                    or not COMPILER.compatible_call_kinds(kinds, formals)
                ):
                    unit.error(
                        "recursive call has incompatible signature", target
                    )
                kinds = formals
            else:
                first_arity, first_is_function = first_signatures.setdefault(
                    target.word, (len(kinds), is_function)
                )
                if is_function != first_is_function:
                    unit.error("external calls disagree on signature", target)
                if len(kinds) != first_arity and not linkage_diagnostic:
                    linkage_diagnostic = (
                        f"{target.path}:{target.line}:{target.column}: calls to '{target.word}' "
                        f"use different argument counts ({first_arity} and {len(kinds)})"
                    )
                    linkage_diagnostic = linkage_diagnostic.replace(
                        str(root) + os.sep, ""
                    )
            symbol = unit.call_symbol(target.word, kinds)
            if symbol in externals:
                previous, _ = externals[symbol]
                if any(
                    a is not None and b is not None and a != b
                    for a, b in zip(previous, kinds)
                ):
                    unit.error("external calls disagree on signature", target)
                kinds = tuple(
                    b if a is None else a for a, b in zip(previous, kinds)
                )
            externals[symbol] = kinds, is_function
        prototypes = [
            COMPILER.routine_signature(symbol, kinds, is_function) + ";"
            for symbol, (kinds, is_function) in externals.items()
        ]
        if unit.routine and (unit.has_indirect_call or unit.uses_callonexit):
            prototypes.append(unit.signature() + ";")
        prototypes.append(COMPILER.render_indirect_calls([unit]))
        prototypes.append(COMPILER.render_exit_callbacks([unit]))
        prototypes.append(COMPILER.render_subroutine_exists([unit]))
        prototypes.append(
            COMPILER.render_empty_arguments(
                [unit], {name: kinds for name, (kinds, _) in externals.items()}
            )
        )
        generated = "\n".join(
            [COMPILER.runtime_features([unit]), RUNTIME]
            + prototypes
            + [unit.render()]
        )
        result = subprocess.run(
            [
                "cc",
                "-std=c99",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-fsyntax-only",
                "-x",
                "c",
                "-",
            ],
            input=generated,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            return (
                relative,
                "C diagnostic",
                result.stderr.splitlines()[0],
                [],
                fixes,
                suppressed_next_warnings,
                calls,
                stubs,
                lookups,
                package_directives,
            )
        warnings = [
            warning.replace(str(root) + os.sep, "") for warning in unit.warnings
        ]
        return (
            relative,
            "translated",
            linkage_diagnostic,
            warnings,
            fixes,
            suppressed_next_warnings,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    except COMPILER.Diagnostic as error:
        detail = str(error).replace(str(root) + os.sep, "")
        absent = [
            lookup["target"]
            for lookup in lookups
            if lookup.get("domain_class") == "absent"
        ]
        if exclude_missing_domains and absent:
            return (
                relative,
                "excluded",
                f"generated insert {absent[0]} has no .domain class in the dump",
                [],
                fixes,
                suppressed_next_warnings,
                calls,
                stubs,
                lookups,
                package_directives,
            )
        return (
            relative,
            "rejected",
            detail,
            [],
            fixes,
            suppressed_next_warnings,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    except COMPILER.SourceEncodingError as error:
        detail = str(error).replace(str(root) + os.sep, "")
        return (
            relative,
            "encoding",
            detail,
            [],
            fixes,
            suppressed_next_warnings,
            calls,
            stubs,
            lookups,
            package_directives,
        )
    except OSError as error:
        return (
            relative,
            "I/O error",
            str(error),
            [],
            fixes,
            suppressed_next_warnings,
            calls,
            stubs,
            lookups,
            package_directives,
        )


def check_entry(relative, kind, **options):
    *result, directives = check(
        relative,
        catalog_kind=kind,
        include_index=worker_include_index,
        component_members=worker_component_members,
        **options,
    )
    metadata = [
        {
            "kind": token.kind,
            "name": token.word,
            "line": token.line,
            "column": token.column,
            "file": display_path(token.path, options["root"]),
        }
        for token in directives
    ]
    return (*result, metadata)


def main():
    h = COMPILER.option_help
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=COMPILER.BlockHelpFormatter,
        epilog=h(
            """
            T24 flags:
              The T24 extracts carry typos, files missing from the dump,
              generated code the dump does not define and inconsistent
              component exports. The T24 flags let a scan use as much of
              those sources as possible. They affect only this checker,
              never edit the extract, and report every use in the JSON
              report. The README section "T24 corpus flags" describes each
              one and every source fix.

            example (full R19 scan with every testing flag):
              python3 tools/check_corpus.py ../t24-extract/201809-R19 \\
                -I .cache/PB201214/include \\
                --t24-catalog ../t24-extract/catalog.sqlite \\
                --t24-indexed-includes \\
                --t24-domain-inserts .cache/domain-inserts/201809-R19 \\
                --t24-component-calls --t24-stub-members \\
                --t24-stub-void-results --t24-relax-access \\
                --source-encoding bytes --defer-unassigned-reads \\
                --quiet-next-warnings --t24-source-fixes -j 8 > report.json
            """
        ),
    )
    parser.add_argument(
        "directory",
        type=Path,
        help=h(
            """
            Corpus root. Every file under it is scanned, or with
            --t24-catalog the catalogued production sources. The report, in
            JSON, goes to stdout.
            """
        ),
    )
    general = parser.add_argument_group("general")
    general.add_argument(
        "-I",
        dest="includes",
        action="append",
        type=Path,
        default=[],
        metavar="DIR",
        help=h(
            """
            Search DIR for $INSERT and INCLUDE files, after the corpus root.
            Repeatable. jbcc's built-in JBC.h is never used here, so give the
            real headers, such as .cache/PB201214/include.
            """
        ),
    )
    general.add_argument(
        "-j",
        type=int,
        default=1,
        metavar="JOBS",
        help="Check JOBS units at a time (default: 1).",
    )
    general.add_argument(
        "--source-encoding",
        choices=COMPILER.SOURCE_ENCODINGS,
        default="utf-8",
        help=h(
            """
            utf-8 (default) decodes sources as UTF-8. bytes keeps every
            source byte, as the T24 scans need.
            """
        ),
    )
    general.add_argument(
        "--defer-unassigned-reads",
        action="store_true",
        help=h(
            """
            Turn a read that jbcc cannot prove is assigned, including a
            CONVERT or CHANGE target, into a runtime check and a warnings
            entry instead of a rejection. T24 relies on COMMON and on
            assignments in other routines.
            """
        ),
    )
    general.add_argument(
        "--quiet-next-warnings",
        action="store_true",
        help="Print one total on stderr for FOR/NEXT name mismatch warnings.",
    )
    general.add_argument(
        "--api-catalogue",
        type=Path,
        metavar="SPEC_DIR",
        help=h(
            """
            Add API coverage to the report, using the jbc-language spec
            directory (see COVERAGE.md).
            """
        ),
    )
    sources = parser.add_argument_group("T24 source handling")
    sources.add_argument(
        "--t24-source-fixes",
        action="store_true",
        help=h(
            """
            Apply the known corrections to T24 sources in memory, each bound
            to one file of one release, and report them as source_fixes.
            """
        ),
    )
    sources.add_argument(
        "--stub-r07-la-parameter",
        action="store_true",
        help=h(
            """
            Supply a translation-only I_F.LA.PARAMETER, which the R07 dump
            lacks, and report each use as include_stubs.
            """
        ),
    )
    selection = parser.add_argument_group("T24 selection and exclusion")
    selection.add_argument(
        "--t24-catalog",
        type=Path,
        metavar="SQLITE",
        help=h(
            """
            Classify files with the t24-extract catalog and scan only the
            production sources of the release named by the corpus directory.
            """
        ),
    )
    selection.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        metavar="RELATIVE_PATH",
        help=h(
            """
            With --t24-catalog, scan only sources under RELATIVE_PATH (whole
            path segments). Repeatable.
            """
        ),
    )
    selection.add_argument(
        "--t24-exclude-local-routines",
        action="store_true",
        help=h(
            """
            Report routines that are not Temenos code, such as R13's
            V.PL.B2LIM.NET, as excluded with a reason.
            """
        ),
    )
    selection.add_argument(
        "--t24-exclude-test-framework",
        action="store_true",
        help=h(
            """
            Report R19's test framework components, SE/SE_Test*, as excluded
            with a reason.
            """
        ),
    )
    components = parser.add_argument_group("T24 R19 components")
    components.add_argument(
        "--t24-indexed-includes",
        action="store_true",
        help=h(
            """
            Resolve includes through the catalog: the including directory,
            its component, the include paths, then a release-wide index.
            Report each lookup; identical copies resolve to the first.
            """
        ),
    )
    components.add_argument(
        "--t24-domain-inserts",
        type=Path,
        metavar="DIR",
        help=h(
            """
            With --t24-indexed-includes, generate the missing
            I_<Service>_<Class> inserts from catalogued .domain classes into
            DIR.
            """
        ),
    )
    components.add_argument(
        "--t24-exclude-missing-domains",
        action="store_true",
        help=h(
            """
            With --t24-domain-inserts, report a unit as excluded when it
            includes an I_<Service>_<Class> insert whose class no catalogued
            .domain file declares, naming the insert in the reason.
            """
        ),
    )
    components.add_argument(
        "--t24-component-calls",
        action="store_true",
        help=h(
            """
            Check Component.member(...) calls against the catalogued
            .component declarations: visibility, argument count, scalar and
            matrix positions. Standard operations on undeclared tables and
            undeclared get/set/clear accessors are accepted with a warning.
            """
        ),
    )
    testing = parser.add_argument_group(
        "T24 testing stubs",
        h(
            """
            These accept code that T24 shipped but the dump cannot explain,
            so that the rest of each unit is checked. Each use is a warning.
            """
        ),
    )
    testing.add_argument(
        "--t24-stub-members",
        action="store_true",
        help=h(
            """
            Accept any arguments for the members listed in T24_MEMBER_STUBS,
            such as the varargs TF.L3Helper.testPublishedMethod.
            """
        ),
    )
    testing.add_argument(
        "--t24-stub-void-results",
        action="store_true",
        help=h(
            """
            Where a method without a result is used as a value, as in
            AF = EB.SystemTables.setAf(X), make the call and use 0.
            """
        ),
    )
    testing.add_argument(
        "--t24-relax-access",
        action="store_true",
        help=h(
            """
            Report a call to a private or module member from another package
            as a warning instead of an error.
            """
        ),
    )
    options = parser.parse_args()
    root = options.directory.resolve()
    if not root.is_dir() or options.j < 1:
        parser.error("expected a corpus directory and a positive job count")
    if not shutil.which("cc"):
        parser.error("cc is required to check generated C")
    file_kinds = {}
    include_index = None
    component_members = None
    if (
        options.source_prefix or options.t24_indexed_includes
    ) and options.t24_catalog is None:
        parser.error(
            "--source-prefix and --t24-indexed-includes require --t24-catalog"
        )
    if (
        options.t24_domain_inserts is not None
        and not options.t24_indexed_includes
    ):
        parser.error("--t24-domain-inserts requires --t24-indexed-includes")
    if options.t24_component_calls and options.t24_catalog is None:
        parser.error("--t24-component-calls requires --t24-catalog")
    if options.t24_catalog is not None:
        try:
            file_kinds = read_file_kinds(options.t24_catalog, root.name)
            if options.t24_indexed_includes:
                include_index = IncludeIndex(
                    options.t24_catalog, root, options.t24_domain_inserts
                )
            if options.t24_component_calls:
                component_members = read_component_members(
                    options.t24_catalog, root
                )
                if options.t24_stub_members:
                    stub_component_members(component_members)
        except (sqlite3.Error, OSError, ValueError) as error:
            parser.error(str(error))
    coverage = None
    if options.api_catalogue is not None:
        try:
            coverage = Coverage(read_catalogues(options.api_catalogue), root)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    prefix_paths = [Path(prefix) for prefix in options.source_prefix]
    if any(
        prefix.is_absolute() or ".." in prefix.parts for prefix in prefix_paths
    ):
        parser.error("--source-prefix must be a path inside the corpus")
    prefixes = [prefix.as_posix() for prefix in prefix_paths]
    if prefixes or include_index is not None or options.t24_component_calls:
        paths = sorted(
            relative
            for relative, kind in file_kinds.items()
            if kind == "jbc_source"
            and (
                not prefixes
                or any(
                    p == "." or relative == p or relative.startswith(p + "/")
                    for p in prefixes
                )
            )
        )
        if not paths:
            parser.error("no catalogued production sources match the selection")
    else:
        paths = sorted(
            str(p.relative_to(root))
            for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
    scan = partial(
        check_entry,
        root=root,
        directories=[root, *options.includes],
        source_encoding=options.source_encoding,
        defer_unassigned_reads=options.defer_unassigned_reads,
        t24_source_fixes=options.t24_source_fixes,
        quiet_next_warnings=options.quiet_next_warnings,
        collect_apis=coverage is not None,
        stub_r07_la_parameter=options.stub_r07_la_parameter,
        stub_void_results=options.t24_stub_void_results,
        relax_access=options.t24_relax_access,
        exclude_local_routines=options.t24_exclude_local_routines,
        exclude_test_framework=options.t24_exclude_test_framework,
        exclude_missing_domains=options.t24_exclude_missing_domains,
    )
    counts = Counter()
    blockers = Counter()
    include_counts = Counter()
    files = {}
    suppressed_next_warnings = 0
    with ProcessPoolExecutor(
        max_workers=options.j,
        initializer=initialize_worker,
        initargs=(include_index, component_members),
    ) as pool:
        entries = pool.map(
            scan, paths, map(file_kinds.get, paths), chunksize=16
        )
        for (
            name,
            status,
            diagnostic,
            warnings,
            fixes,
            suppressed,
            calls,
            stubs,
            lookups,
            package_directives,
        ) in entries:
            suppressed_next_warnings += suppressed
            counts[status] += 1
            if coverage is not None:
                coverage.add_unit(name, status, calls)
            files[name] = {"status": status}
            if status == "excluded":
                files[name]["reason"] = diagnostic or excluded_reason(
                    root.name, name
                )
                diagnostic = ""
            if fixes:
                files[name]["source_fixes"] = fixes
            if stubs:
                files[name]["include_stubs"] = stubs
            if lookups:
                files[name]["include_lookups"] = lookups
                include_counts.update(lookup["status"] for lookup in lookups)
            if package_directives:
                files[name]["package_directives"] = package_directives
            if warnings:
                files[name]["warnings"] = warnings
            if status == "translated" and diagnostic:
                files[name]["linkage_diagnostic"] = diagnostic
            elif diagnostic:
                files[name]["diagnostic"] = diagnostic
                reason = re.sub(r"^.*?:\d+:\d+: ", "", diagnostic)
                blockers[group(reason) if status == "rejected" else status] += 1
    if options.quiet_next_warnings:
        print(
            f"Suppressed {suppressed_next_warnings} FOR/NEXT name mismatch warnings.",
            file=sys.stderr,
        )
    report = dict(
        counts=counts, first_blockers=dict(blockers.most_common()), files=files
    )
    if prefixes or include_index is not None or options.t24_component_calls:
        report["selection"] = {
            "source_prefixes": prefixes,
            "indexed_includes": include_index is not None,
        }
        if options.t24_domain_inserts is not None:
            report["selection"]["domain_inserts"] = True
        if options.t24_component_calls:
            report["selection"]["component_calls"] = True
    if include_index is not None:
        report["include_lookups"] = dict(include_counts)
    if coverage is not None:
        for path in sorted((ROOT / "tests/snippets").glob("*.b")):
            calls = []
            name = str(path.relative_to(ROOT))
            try:
                COMPILER.compile_unit(path, [], api_call=record_calls(calls))
            except (COMPILER.Diagnostic, UnicodeError, OSError) as error:
                coverage.fixture_scan_failures.append(
                    {"file": name, "diagnostic": str(error)}
                )
                continue
            coverage.add_snippet(name, calls)
        scan_settings = {
            "corpus": str(root),
            "includes": [str(path.resolve()) for path in options.includes],
            "source_encoding": options.source_encoding,
            "defer_unassigned_reads": options.defer_unassigned_reads,
            "t24_source_fixes": options.t24_source_fixes,
        }
        scan_settings.update(report.get("selection", {}))
        if options.t24_catalog is not None:
            scan_settings["t24_catalog"] = str(options.t24_catalog.resolve())
        if options.stub_r07_la_parameter:
            scan_settings["stub_r07_la_parameter"] = True
        if options.t24_stub_void_results:
            scan_settings["t24_stub_void_results"] = True
        if options.t24_stub_members:
            scan_settings["t24_stub_members"] = True
        if options.t24_relax_access:
            scan_settings["t24_relax_access"] = True
        if options.t24_exclude_local_routines:
            scan_settings["t24_exclude_local_routines"] = True
        if options.t24_exclude_test_framework:
            scan_settings["t24_exclude_test_framework"] = True
        if options.t24_exclude_missing_domains:
            scan_settings["t24_exclude_missing_domains"] = True
        report["api_coverage"] = coverage.report(scan_settings)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
