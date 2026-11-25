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


def fix_t24_source(path, source, *, root, fixes):
    if path.name not in T24_SOURCE_FIXES and path.name not in R07_SOURCE_FIXES:
        return source
    try:
        relative = path.resolve().relative_to(root)
    except ValueError:
        return source
    rule = None
    if relative == Path(path.name):
        rule = T24_SOURCE_FIXES.get(path.name)
    elif root.name == "200707-R07" and relative.parent == Path("GLOBUS.BP"):
        if (
            path.name != "COMPARE.DB.JBASE"
            or (root / "GLOBUS.BP/JBC.h").is_file()
        ):
            rule = R07_SOURCE_FIXES.get(path.name)
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


class IncludeIndex:
    def __init__(self, catalogue, root):
        self.root = root
        self.scopes = {}
        self.includes = {}
        uri = catalogue.resolve().as_uri() + "?mode=ro"
        with closing(sqlite3.connect(uri, uri=True)) as db:
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
        entry.update(status="missing")
        return None


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument(
        "-I", dest="includes", action="append", type=Path, default=[]
    )
    parser.add_argument("-j", type=int, default=1, metavar="JOBS")
    parser.add_argument(
        "--source-encoding",
        choices=COMPILER.SOURCE_ENCODINGS,
        default="utf-8",
        help="decode source as UTF-8 or preserve literal source bytes (default: utf-8)",
    )
    parser.add_argument(
        "--defer-unassigned-reads",
        action="store_true",
        help="report warnings for scalar variable reads checked at runtime",
    )
    parser.add_argument(
        "--t24-source-fixes",
        action="store_true",
        help="apply the known T24 source fixes in memory and include them in the report",
    )
    parser.add_argument(
        "--stub-r07-la-parameter",
        action="store_true",
        help="use a translation-only fallback for missing I_F.LA.PARAMETER and report its use",
    )
    parser.add_argument(
        "--quiet-next-warnings",
        action="store_true",
        help="replace individual FOR/NEXT name mismatch warnings with a total on stderr",
    )
    parser.add_argument(
        "--api-catalogue",
        type=Path,
        metavar="SPEC_DIR",
        help="include API coverage using the jbc-language spec directory",
    )
    parser.add_argument(
        "--t24-catalog",
        type=Path,
        metavar="SQLITE",
        help="classify files using the catalog entries for the corpus directory name",
    )
    parser.add_argument(
        "--t24-indexed-includes",
        action="store_true",
        help="resolve includes by component and release, and report each lookup",
    )
    parser.add_argument(
        "--t24-component-calls",
        action="store_true",
        help="check qualified references against catalogued component declarations",
    )
    parser.add_argument(
        "--source-prefix",
        action="append",
        default=[],
        metavar="RELATIVE_PATH",
        help="scan catalogued production sources under this path (repeatable)",
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
    if options.t24_component_calls and options.t24_catalog is None:
        parser.error("--t24-component-calls requires --t24-catalog")
    if options.t24_catalog is not None:
        try:
            file_kinds = read_file_kinds(options.t24_catalog, root.name)
            if options.t24_indexed_includes:
                include_index = IncludeIndex(options.t24_catalog, root)
            if options.t24_component_calls:
                component_members = read_component_members(
                    options.t24_catalog, root
                )
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
        report["api_coverage"] = coverage.report(scan_settings)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
