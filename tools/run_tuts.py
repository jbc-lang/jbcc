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
from collections import Counter, OrderedDict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing, redirect_stderr
from functools import partial
from pathlib import Path

if __package__:
    from . import check_corpus
    from .t24_components import read_component_members, read_component_properties, read_component_tables
else:
    import check_corpus
    from t24_components import read_component_members, read_component_properties, read_component_tables

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


# Set in each worker by initialize_worker.
properties = {}
tables = {}
unit_cache = OrderedDict()
CACHE_SIZE = 3000
synthesized = None
next_index = 0


def initialize_worker(include_index, members, accessors, table_files):
    global properties, tables, synthesized
    check_corpus.initialize_worker(include_index, members)
    properties, tables = accessors, table_files
    synthesized = Path(tempfile.mkdtemp(prefix="tut-units-"))


def compile_cached(path, root, directories, *, cache=True):
    """A compiled unit, from the worker's cache when it has one. Each unit
    gets an index of its own, so cached units link together."""
    global next_index
    if cache and path in unit_cache:
        unit_cache.move_to_end(path)
        return unit_cache[path]
    next_index += 1
    resolver = check_corpus.worker_include_index
    unit = COMPILER.compile_unit(
        path,
        directories,
        next_index,
        source_encoding="bytes",
        defer_unassigned_reads=True,
        source_filter=lambda source_path, source: check_corpus.fix_t24_source(
            source_path, source, root=root, fixes=[]
        ),
        include_resolver=partial(resolver.resolve, lookups=[]) if resolver else None,
        builtin_includes=False,
        component_members=check_corpus.worker_component_members,
        stub_void_results=True,
        relax_access=True,
        next_warning=lambda _message: None,
    )
    if cache:
        unit_cache[path] = unit
        if len(unit_cache) > CACHE_SIZE:
            unit_cache.popitem(last=False)
    return unit


def accessor_source(name, binding):
    """jBC for a component property accessor, such as
    EB.SystemTables.setRNew(field, value) over R.NEW in I_COMMON."""
    operation, insert, variable, rank = binding
    indices = [f"I{i + 1}" for i in range(rank)]
    element = f"{variable}({', '.join(indices)})" if rank else variable
    if operation == "get":
        header, body = f"FUNCTION {name}({', '.join(indices)})", f"RETURN {element}"
    elif operation == "set":
        header = f"SUBROUTINE {name}({', '.join(indices + ['VALUE'])})"
        body = f"{element} = VALUE"
    elif operation == "clear":
        header = f"SUBROUTINE {name}()"
        body = f"MAT {variable} = ''" if rank else f"{variable} = ''"
    elif operation == "getDynArrayFrom":
        header = f"FUNCTION {name}()"
        body = f"MATBUILD RESULT FROM {variable}\nRETURN RESULT"
    else:
        header = f"SUBROUTINE {name}(VALUE)"
        body = f"MATPARSE {variable} FROM VALUE"
    tail = "" if header.startswith("FUNCTION") else "\nRETURN"
    # I_COMMON and I_EQUATE first, as T24 routines include them: other
    # inserts size their COMMON matrices with I_COMMON's EQU C$SYSDIM.
    inserts = "".join(
        f"$INSERT {name}\n" for name in dict.fromkeys(["I_COMMON", "I_EQUATE", insert])
    )
    return f"{header}\n{inserts}{body}{tail}\nEND\n"


def synthesized_path(name, source):
    path = synthesized / (name.encode("utf-8").hex() + ".b")
    if not path.exists():
        path.write_text(source, encoding="utf-8")
    return path


PROPERTY_CHANGE = re.compile(
    rb"""UTF\.addStubPropertyChange\(\s*[^,()]+,\s*(["'])([\w.]+)\1\s*,\s*(["'])(\w+)\3"""
)


def link_units(test, target, root, directories):
    """The test, its target and the component property accessors they
    use, as synthesized units. Every other routine they call is a stub
    that the UTF runtime answers (TUT.md)."""
    units = [
        compile_cached(test, root, directories, cache=False),
        compile_cached(target, root, directories),
    ]
    accessors = {call.word for unit in units for call, _, _ in unit.calls}
    accessors.update(
        f"{match[2].decode()}.set{match[4].decode()}".casefold()
        for match in PROPERTY_CHANGE.finditer(test.read_bytes())
    )
    for name in sorted(accessors):
        if name in properties:
            path = synthesized_path(name, accessor_source(name, properties[name]))
            units.append(compile_cached(path, root, directories))
    return units


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

    try:
        # jbcc's warnings about the corpus sources are not the test's result.
        with redirect_stderr(io.StringIO()):
            units = link_units(path, target_path, root, directories)
            used = {
                call.word.rsplit(".", 1)[0] for unit in units for call, _, _ in unit.calls
            }
            source, libraries = COMPILER.link_units(
                units,
                utf_aliases=aliases,
                stub_missing=True,
                utf_tables={table: tables[table] for table in used if table in tables},
            )
    except COMPILER.Diagnostic as error:
        detail = first_line(str(error).replace(str(root) + os.sep, ""))
        if UNLINKED.search(detail) or "disagree" in detail or "argument" in detail:
            return relative, "unlinked", target, detail
        return relative, "rejected", target, detail
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
        except subprocess.TimeoutExpired as expired:
            output = (expired.stdout or b"") + (expired.stderr or b"")
            if keep:
                (keep / Path(relative).with_suffix(".log").name).write_bytes(output)
            return relative, "timeout", target, last_line((expired.stderr or b"").decode("latin-1"))[:200]
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
        accessors = read_component_properties(options.t24_catalog, root)
        table_files = read_component_tables(options.t24_catalog, root)
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
        initializer=initialize_worker,
        initargs=(include_index, members, accessors, table_files),
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
