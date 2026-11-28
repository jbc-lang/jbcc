"""Build and run T24 R19's unit tests (*.tut) with their targets (TUT.md).

Each test is linked with the routine it names in UTF.setTarget, both read
in place from the corpus with the R19 scan's settings (R19-CORPUS.md), then
built with cc and run with a time limit. The JSON report gives each test
one state:

  no target     no UTF.setTarget with a literal name, directly or through
                a variable assigned once
  target missing  no catalogued routine has the target's name
  rejected      jbcc rejected the test or the target
  unlinked      the program calls a routine that isn't linked (TUT.md step 4)
  not built     cc rejected the generated C
  passed, failed, unsupported, not run
                the UTF runtime's verdict (the last "UTF:" line on stderr)
  error         the program stopped without a verdict, such as at a runtime
                error
  crashed, timeout

The corpus is proprietary: the report holds paths, states and diagnostics,
and belongs outside the repository.
"""

import argparse
import io
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing, redirect_stderr
from functools import partial
from pathlib import Path

if __package__:
    from . import check_corpus
    from .t24_components import read_component_members
else:
    import check_corpus
    from t24_components import read_component_members

COMPILER = check_corpus.COMPILER

TARGET_LITERAL = re.compile(rb"""UTF\.setTarget\(\s*(["'])([^"'\r\n]+)\1\s*\)""")
TARGET_VARIABLE = re.compile(rb"UTF\.setTarget\(\s*([A-Za-z][\w.$]*)\s*\)")
UNLINKED = re.compile(r"unknown (?:subroutine|function) '([^']+)'")
VERDICT = re.compile(r"^UTF: (passed|failed|unsupported|not run)\b ?(.*)$")
STATES = (
    "no target",
    "target missing",
    "rejected",
    "unlinked",
    "not built",
    "passed",
    "failed",
    "unsupported",
    "not run",
    "error",
    "crashed",
    "timeout",
)


def test_target(source):
    """The routine a test names in UTF.setTarget: a literal, or a variable
    assigned a literal exactly once."""
    literal = TARGET_LITERAL.search(source)
    if literal:
        return literal[2].decode("latin-1").strip()
    variable = TARGET_VARIABLE.search(source)
    if not variable:
        return None
    name = re.escape(variable[1])
    values = {
        match[2]
        for match in re.finditer(
            rb"^[ \t]*" + name + rb"""[ \t]*=[ \t]*(["'])([^"'\r\n]+)\1[ \t\r]*(?:;|$)""",
            source,
            re.M,
        )
    }
    return values.pop().decode("latin-1").strip() if len(values) == 1 else None


def read_targets(catalogue, extract):
    """(target name -> corpus path, component method -> routine name). A
    target is a routine, or an R19 component method such as
    AA.Account.AccountMaintain, which the component's definition maps to
    the routine that implements it (AA.ACCOUNT.MAINTAIN)."""
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        rows = db.execute(
            "SELECT routine_name, rel FROM file_path WHERE extract = ? AND kind = 'jbc_source'"
            " AND routine_name IS NOT NULL ORDER BY rel",
            (extract,),
        ).fetchall()
        methods = db.execute(
            "SELECT f.component_name, m.name, m.jbc FROM method m JOIN file_path f ON f.id = m.file_id"
            " WHERE f.extract = ? AND m.jbc IS NOT NULL ORDER BY f.rel",
            (extract,),
        ).fetchall()
    targets = {}
    for name, rel in rows:
        targets.setdefault(name, rel)
    aliases = {}
    for component, method, routine in methods:
        alias = f"{component}.{method}"
        if routine in targets and alias not in targets:
            aliases.setdefault(alias, routine)
            targets.setdefault(alias, targets[routine])
    return targets, aliases


def first_line(text):
    return next((line for line in text.splitlines() if line.strip()), "")


def last_line(text):
    return next((line for line in reversed(text.splitlines()) if line.strip()), "")


def run_test(relative, *, root, directories, targets, aliases, timeout, keep):
    """(relative path, state, target, detail) for one test."""
    path = root / relative
    target = test_target(path.read_bytes())
    if target is None:
        return relative, "no target", None, ""
    target_path = targets.get(target)
    if target_path is None:
        # A component method the exported definitions leave out: the test
        # is named after its routine, as AA.ACCOUNT.VALIDATE.BUNDLE.HIERARCHY_1
        # tests AA.Account.ValidateBundleHierarchy.
        routine = re.sub(r"_\d+$", "", path.stem)
        if target.count(".") < 2 or target.upper() == target or routine not in targets:
            return relative, "target missing", target, ""
        target_path = targets[routine]
        aliases = {**aliases, target: routine}
    target_path = root / target_path

    def source_filter(source_path, source):
        return check_corpus.fix_t24_source(source_path, source, root=root, fixes=[])

    resolver = check_corpus.worker_include_index
    try:
        # jbcc's warnings about the corpus sources are not the test's result.
        with redirect_stderr(io.StringIO()):
            source, libraries = COMPILER.compile_program(
                [path, target_path],
                directories,
                source_encoding="bytes",
                defer_unassigned_reads=True,
                source_filter=source_filter,
                include_resolver=partial(resolver.resolve, lookups=[]) if resolver else None,
                builtin_includes=False,
                link_packages=True,
                unit_options={
                    "component_members": check_corpus.worker_component_members,
                    "stub_void_results": True,
                    "relax_access": True,
                    "next_warning": lambda _message: None,
                },
                utf_aliases=aliases,
            )
    except COMPILER.Diagnostic as error:
        detail = str(error).replace(str(root) + os.sep, "")
        missing = UNLINKED.search(detail)
        if missing:
            return relative, "unlinked", target, missing[1]
        return relative, "rejected", target, first_line(detail)
    with tempfile.TemporaryDirectory(prefix="tut-") as work:
        work = Path(work)
        c_file = work / "test.c"
        program = work / "test"
        c_file.write_text(source, encoding="utf-8")
        built = subprocess.run(
            ["cc", "-std=c99", "-w", str(c_file), *libraries, "-o", str(program)],
            capture_output=True,
            text=True,
        )
        if built.returncode:
            return relative, "not built", target, first_line(built.stderr)
        try:
            ran = subprocess.run(
                [str(program)],
                cwd=work,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return relative, "timeout", target, ""
        if keep:
            (keep / Path(relative).with_suffix(".log").name).write_bytes(ran.stdout + ran.stderr)
    stderr = ran.stderr.decode("latin-1").replace(str(root) + os.sep, "")
    if ran.returncode < 0:
        name = signal.Signals(-ran.returncode).name
        return relative, "crashed", target, name
    verdict = next(
        (VERDICT.match(line) for line in reversed(stderr.splitlines()) if line.startswith("UTF: ")),
        None,
    )
    if verdict:
        return relative, verdict[1], target, verdict[2]
    return relative, "error", target, last_line(stderr)


def main():
    parser = argparse.ArgumentParser(description="Build and run T24 R19's unit tests with their targets.")
    parser.add_argument("corpus", type=Path, help="the R19 extract, such as ../t24-extract/201809-R19")
    parser.add_argument("tests", nargs="*", help="tests to run, relative to the corpus (default: all)")
    parser.add_argument("--t24-catalog", type=Path, required=True, help="the extract's catalog.sqlite")
    parser.add_argument("-I", dest="includes", action="append", type=Path, default=[], help="include directory")
    parser.add_argument("--t24-domain-inserts", type=Path, help="generated domain inserts, as for the R19 scan")
    parser.add_argument("--list", type=Path, help="a file of tests to run, one per line")
    parser.add_argument("--limit", type=int, help="run only the first N selected tests")
    parser.add_argument("--timeout", type=float, default=10, help="seconds per test run (default 10)")
    parser.add_argument("--keep-logs", type=Path, help="write each run's output to this directory")
    parser.add_argument("-j", type=int, default=os.cpu_count(), help="parallel workers")
    parser.add_argument("-o", "--output", type=Path, required=True, help="the JSON report")
    options = parser.parse_args()

    root = options.corpus.resolve()
    try:
        kinds = check_corpus.read_file_kinds(options.t24_catalog, root.name)
        include_index = check_corpus.IncludeIndex(options.t24_catalog, root, options.t24_domain_inserts)
        members = read_component_members(options.t24_catalog, root)
        check_corpus.stub_component_members(members)
        targets, aliases = read_targets(options.t24_catalog, root.name)
    except (sqlite3.Error, OSError, ValueError) as error:
        parser.error(str(error))
    tests = list(options.tests)
    if options.list:
        tests += [line.strip() for line in options.list.read_text().splitlines() if line.strip()]
    if not tests:
        tests = sorted(rel for rel, kind in kinds.items() if kind == "jbc_test")
    if options.limit is not None:
        tests = tests[: options.limit]
    if options.keep_logs:
        options.keep_logs.mkdir(parents=True, exist_ok=True)

    run = partial(
        run_test,
        root=root,
        directories=[root, *options.includes],
        targets=targets,
        aliases=aliases,
        timeout=options.timeout,
        keep=options.keep_logs.resolve() if options.keep_logs else None,
    )
    started = time.monotonic()
    counts = Counter()
    results = {}
    with ProcessPoolExecutor(
        max_workers=options.j,
        initializer=check_corpus.initialize_worker,
        initargs=(include_index, members),
    ) as pool:
        for relative, state, target, detail in pool.map(run, tests, chunksize=4):
            counts[state] += 1
            entry = {"state": state}
            if target:
                entry["target"] = target
            if detail:
                entry["detail"] = detail
            results[relative] = entry
    report = {
        "counts": {state: counts[state] for state in STATES if counts[state]},
        "seconds": round(time.monotonic() - started, 1),
        "settings": {
            "corpus": str(root),
            "catalog": str(options.t24_catalog.resolve()),
            "includes": [str(path.resolve()) for path in options.includes],
            "timeout": options.timeout,
        },
        "tests": results,
    }
    options.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    summary = ", ".join(f"{counts[state]} {state}" for state in STATES if counts[state])
    print(f"{len(tests)} tests: {summary}; wrote {options.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
