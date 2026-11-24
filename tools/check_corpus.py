"""Translate individual corpus units and ask cc to validate their generated C."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from functools import partial
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sqlite3
import subprocess
import sys

if __package__:
    from .api_coverage import Coverage, read_catalogues, record_calls
else:
    from api_coverage import Coverage, read_catalogues, record_calls

ROOT = Path(__file__).resolve().parents[1]
COMPILER = runpy.run_path(str(ROOT / "jbcc"))
RUNTIME = (ROOT / "runtime/jbc.c").read_text()

T24_SOURCE_FIXES = {
    "STEST.AZ.PD.DATES.CHK": (
        re.compile(r"^[ \t]*[\w.]+[ \t]*=[ \t]*[\w.]+<(?P<edit>\.AZ\.SLS\.TYPE\.I)(?=[ \t]*,)", re.M),
        "AZ.SLS.TYPE.I",
    ),
    "TK.VALIDATE.SYSGEN.FILES": (
        re.compile(r"^[ \t]*(?:IF[ \t]+)?(?P<edit>1ST\.RECORD)(?=[ \t]*=|[ \t]+THEN\b)", re.M),
        "FIRST.RECORD",
    ),
    "LIST.DATA": (
        re.compile(r'^[ \t]*THE\.ARGS[ \t]*=[ \t]*"F\.\.\.":[ \t]*(?P<edit>FM)(?=[ \t]*:"F\.\.\.")', re.M),
        "@FM",
    ),
}


def fix_t24_source(path, source, *, root, fixes):
    rule = T24_SOURCE_FIXES.get(path.name)
    if rule is None or path.resolve() != root / path.name:
        return source
    pattern, replacement = rule

    def replace(match):
        start = match.start("edit")
        fix = {"file": path.name, "line": source.count("\n", 0, start) + 1,
               "column": start - source.rfind("\n", 0, start),
               "before": match["edit"], "after": replacement}
        if fix not in fixes:
            fixes.append(fix)
        return source[match.start():start] + replacement

    return pattern.sub(replace, source)


def group(message):
    # Preserve keyword spellings for unsupported statements. Group arbitrary
    # user identifiers together and retain full diagnostics in the file report.
    for prefix in ("unknown variable or unsupported function", "unknown label",
                   "include file", "unassigned variable"):
        if message.startswith(prefix):
            return prefix
    return message


def read_file_kinds(catalogue, extract):
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        kinds = dict(db.execute("SELECT rel, kind FROM file_path WHERE extract = ?", (extract,)))
    if not kinds:
        raise ValueError(f"no files for extract '{extract}' in {catalogue}")
    return kinds


def check(relative, root, directories, source_encoding='utf-8', defer_unassigned_reads=False,
          t24_source_fixes=False, quiet_next_warnings=False, collect_apis=False, *, catalog_kind=None):
    path = root / relative
    fixes = []
    calls = []
    if catalog_kind == "jbc_include" or (catalog_kind is None and path.name.startswith("I_")):
        return relative, "include fragment", "", [], fixes, 0, calls
    if catalog_kind == "c_header":
        return relative, "C header", "", [], fixes, 0, calls
    if catalog_kind not in (None, "jbc_source"):
        return relative, "other catalog file", "", [], fixes, 0, calls
    suppressed_next_warnings = 0

    def count_next_warning(_message):
        nonlocal suppressed_next_warnings
        suppressed_next_warnings += 1

    try:
        source_filter = partial(fix_t24_source, root=root, fixes=fixes) if t24_source_fixes else None
        unit = COMPILER["compile_unit"](path, directories, source_encoding=source_encoding,
                                       separate_external_arities=True,
                                       defer_unassigned_reads=defer_unassigned_reads, source_filter=source_filter,
                                       next_warning=count_next_warning if quiet_next_warnings else None,
                                       api_call=record_calls(calls) if collect_apis else None)
        externals = {}
        first_signatures = {}
        linkage_diagnostic = ""
        for target, kinds, is_function in unit.calls:
            if unit.routine and unit.routine.word == target.word:
                formals = tuple(unit.formals.values())
                if is_function != unit.is_function or not COMPILER["compatible_call_kinds"](kinds, formals):
                    unit.error("recursive call has incompatible signature", target)
                kinds = formals
            else:
                first_arity, first_is_function = first_signatures.setdefault(target.word, (len(kinds), is_function))
                if is_function != first_is_function:
                    unit.error("external calls disagree on signature", target)
                if len(kinds) != first_arity and not linkage_diagnostic:
                    linkage_diagnostic = (f"{target.path}:{target.line}:{target.column}: calls to '{target.word}' "
                                          f"use different argument counts ({first_arity} and {len(kinds)})")
                    linkage_diagnostic = linkage_diagnostic.replace(str(root) + os.sep, "")
            symbol = unit.call_symbol(target.word, kinds)
            if symbol in externals:
                previous, _ = externals[symbol]
                if any(a is not None and b is not None and a != b for a, b in zip(previous, kinds)):
                    unit.error("external calls disagree on signature", target)
                kinds = tuple(b if a is None else a for a, b in zip(previous, kinds))
            externals[symbol] = kinds, is_function
        prototypes = [COMPILER["routine_signature"](symbol, kinds, is_function) + ";"
                      for symbol, (kinds, is_function) in externals.items()]
        if unit.routine and (unit.has_indirect_call or unit.uses_callonexit):
            prototypes.append(unit.signature() + ";")
        prototypes.append(COMPILER["render_indirect_calls"]([unit]))
        prototypes.append(COMPILER["render_exit_callbacks"]([unit]))
        prototypes.append(COMPILER["render_subroutine_exists"]([unit]))
        prototypes.append(COMPILER["render_empty_arguments"]([unit], {name: kinds for name, (kinds, _) in externals.items()}))
        generated = "\n".join([COMPILER["runtime_features"]([unit]), RUNTIME] + prototypes + [unit.render()])
        result = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                 "-pedantic", "-fsyntax-only", "-x", "c", "-"],
                                input=generated, text=True, capture_output=True)
        if result.returncode:
            return relative, "C diagnostic", result.stderr.splitlines()[0], [], fixes, suppressed_next_warnings, calls
        warnings = [warning.replace(str(root) + os.sep, "") for warning in unit.warnings]
        return relative, "translated", linkage_diagnostic, warnings, fixes, suppressed_next_warnings, calls
    except COMPILER["Diagnostic"] as error:
        detail = str(error).replace(str(root) + os.sep, "")
        return relative, "rejected", detail, [], fixes, suppressed_next_warnings, calls
    except COMPILER["SourceEncodingError"] as error:
        return relative, "encoding", str(error).replace(str(root) + os.sep, ""), [], fixes, suppressed_next_warnings, calls
    except OSError as error:
        return relative, "I/O error", str(error), [], fixes, suppressed_next_warnings, calls


def check_entry(relative, kind, **options):
    return check(relative, catalog_kind=kind, **options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("-I", dest="includes", action="append", type=Path, default=[])
    parser.add_argument("-j", type=int, default=1, metavar="JOBS")
    parser.add_argument("--source-encoding", choices=COMPILER["SOURCE_ENCODINGS"], default="utf-8",
                        help="decode source as UTF-8 or preserve literal source bytes (default: utf-8)")
    parser.add_argument("--defer-unassigned-reads", action="store_true",
                        help="report warnings for scalar variable reads checked at runtime")
    parser.add_argument("--t24-source-fixes", action="store_true",
                        help="apply the known T24 source fixes in memory and include them in the report")
    parser.add_argument("--quiet-next-warnings", action="store_true",
                        help="replace individual FOR/NEXT name mismatch warnings with a total on stderr")
    parser.add_argument("--api-catalogue", type=Path, metavar="SPEC_DIR",
                        help="include API coverage using the jbc-language spec directory")
    parser.add_argument("--t24-catalog", type=Path, metavar="SQLITE",
                        help="classify files using the catalog entries for the corpus directory name")
    options = parser.parse_args()
    root = options.directory.resolve()
    if not root.is_dir() or options.j < 1:
        parser.error("expected a corpus directory and a positive job count")
    if not shutil.which("cc"):
        parser.error("cc is required to check generated C")
    file_kinds = {}
    if options.t24_catalog is not None:
        try:
            file_kinds = read_file_kinds(options.t24_catalog, root.name)
        except (sqlite3.Error, OSError, ValueError) as error:
            parser.error(str(error))
    coverage = None
    if options.api_catalogue is not None:
        try:
            coverage = Coverage(read_catalogues(options.api_catalogue), root)
        except (OSError, ValueError) as error:
            parser.error(str(error))
    paths = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    scan = partial(check_entry, root=root, directories=[root, *options.includes], source_encoding=options.source_encoding,
                   defer_unassigned_reads=options.defer_unassigned_reads, t24_source_fixes=options.t24_source_fixes,
                   quiet_next_warnings=options.quiet_next_warnings, collect_apis=coverage is not None)
    counts = Counter()
    blockers = Counter()
    files = {}
    suppressed_next_warnings = 0
    with ProcessPoolExecutor(max_workers=options.j) as pool:
        entries = pool.map(scan, paths, map(file_kinds.get, paths), chunksize=16)
        for name, status, diagnostic, warnings, fixes, suppressed, calls in entries:
            suppressed_next_warnings += suppressed
            counts[status] += 1
            if coverage is not None:
                coverage.add_unit(name, status, calls)
            files[name] = {"status": status}
            if fixes:
                files[name]["source_fixes"] = fixes
            if warnings:
                files[name]["warnings"] = warnings
            if status == "translated" and diagnostic:
                files[name]["linkage_diagnostic"] = diagnostic
            elif diagnostic:
                files[name]["diagnostic"] = diagnostic
                reason = re.sub(r"^.*?:\d+:\d+: ", "", diagnostic)
                blockers[group(reason) if status == "rejected" else status] += 1
    if options.quiet_next_warnings:
        print(f"Suppressed {suppressed_next_warnings} FOR/NEXT name mismatch warnings.", file=sys.stderr)
    report = dict(counts=counts, first_blockers=dict(blockers.most_common()), files=files)
    if coverage is not None:
        for path in sorted((ROOT / "tests/snippets").glob("*.b")):
            calls = []
            name = str(path.relative_to(ROOT))
            try:
                COMPILER["compile_unit"](path, [], api_call=record_calls(calls))
            except (COMPILER["Diagnostic"], UnicodeError, OSError) as error:
                coverage.fixture_scan_failures.append({"file": name, "diagnostic": str(error)})
                continue
            coverage.add_snippet(name, calls)
        scan_settings = {
            "corpus": str(root), "includes": [str(path.resolve()) for path in options.includes],
            "source_encoding": options.source_encoding, "defer_unassigned_reads": options.defer_unassigned_reads,
            "t24_source_fixes": options.t24_source_fixes,
        }
        if options.t24_catalog is not None:
            scan_settings["t24_catalog"] = str(options.t24_catalog.resolve())
        report["api_coverage"] = coverage.report(scan_settings)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
