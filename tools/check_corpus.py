"""Translate individual corpus units and ask cc to validate their generated C."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from functools import partial
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess

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


def check(relative, root, directories, source_encoding='utf-8', defer_unassigned_reads=False, t24_source_fixes=False):
    path = root / relative
    fixes = []
    if path.name.startswith("I_"):
        return relative, "include fragment", "", [], fixes
    try:
        source_filter = partial(fix_t24_source, root=root, fixes=fixes) if t24_source_fixes else None
        unit = COMPILER["compile_unit"](path, directories, source_encoding=source_encoding,
                                       separate_external_arities=True,
                                       defer_unassigned_reads=defer_unassigned_reads, source_filter=source_filter)
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
            return relative, "C diagnostic", result.stderr.splitlines()[0], [], fixes
        warnings = [warning.replace(str(root) + os.sep, "") for warning in unit.warnings]
        return relative, "translated", linkage_diagnostic, warnings, fixes
    except COMPILER["Diagnostic"] as error:
        detail = str(error).replace(str(root) + os.sep, "")
        return relative, "rejected", detail, [], fixes
    except COMPILER["SourceEncodingError"] as error:
        return relative, "encoding", str(error).replace(str(root) + os.sep, ""), [], fixes
    except OSError as error:
        return relative, "I/O error", str(error), [], fixes


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
    options = parser.parse_args()
    root = options.directory.resolve()
    if not root.is_dir() or options.j < 1:
        parser.error("expected a corpus directory and a positive job count")
    if not shutil.which("cc"):
        parser.error("cc is required to check generated C")
    paths = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    scan = partial(check, root=root, directories=[root, *options.includes], source_encoding=options.source_encoding,
                   defer_unassigned_reads=options.defer_unassigned_reads, t24_source_fixes=options.t24_source_fixes)
    counts = Counter()
    blockers = Counter()
    files = {}
    with ProcessPoolExecutor(max_workers=options.j) as pool:
        for name, status, diagnostic, warnings, fixes in pool.map(scan, paths, chunksize=16):
            counts[status] += 1
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
    print(json.dumps(dict(counts=counts, first_blockers=dict(blockers.most_common()), files=files),
                     indent=2))


if __name__ == "__main__":
    main()
