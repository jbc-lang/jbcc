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


def group(message):
    # Preserve keyword spellings for unsupported statements. Group arbitrary
    # user identifiers together and retain full diagnostics in the file report.
    for prefix in ("unknown variable or unsupported function", "unknown label",
                   "include file", "unassigned variable"):
        if message.startswith(prefix):
            return prefix
    return message


def check(relative, root, directories, source_encoding='utf-8'):
    path = root / relative
    if path.name.startswith("I_"):
        return relative, "include fragment", ""
    try:
        unit = COMPILER["compile_unit"](path, directories, source_encoding=source_encoding)
        externals = {}
        for target, kinds, is_function in unit.calls:
            if unit.routine and unit.routine.word == target.word:
                if (kinds, is_function) != (tuple(unit.formals.values()), unit.is_function):
                    unit.error("recursive call has incompatible signature", target)
            signature = (kinds, is_function)
            if externals.setdefault(target.word, signature) != signature:
                unit.error("external calls disagree on signature", target)
        prototypes = [COMPILER["routine_signature"](name, kinds, is_function) + ";"
                      for name, (kinds, is_function) in externals.items()]
        if unit.routine and (unit.has_indirect_call or unit.uses_callonexit):
            prototypes.append(unit.signature() + ";")
        prototypes.append(COMPILER["render_indirect_calls"]([unit]))
        prototypes.append(COMPILER["render_exit_callbacks"]([unit]))
        generated = "\n".join([COMPILER["runtime_features"]([unit]), RUNTIME] + prototypes + [unit.render()])
        result = subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                                 "-pedantic", "-fsyntax-only", "-x", "c", "-"],
                                input=generated, text=True, capture_output=True)
        if result.returncode:
            return relative, "C diagnostic", result.stderr.splitlines()[0]
        return relative, "translated", ""
    except COMPILER["Diagnostic"] as error:
        detail = str(error).replace(str(root) + os.sep, "")
        return relative, "rejected", detail
    except COMPILER["SourceEncodingError"] as error:
        return relative, "encoding", str(error).replace(str(root) + os.sep, "")
    except OSError as error:
        return relative, "I/O error", str(error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("-I", dest="includes", action="append", type=Path, default=[])
    parser.add_argument("-j", type=int, default=1, metavar="JOBS")
    parser.add_argument("--source-encoding", choices=COMPILER["SOURCE_ENCODINGS"], default="utf-8",
                        help="decode source as UTF-8 or preserve literal source bytes (default: utf-8)")
    options = parser.parse_args()
    root = options.directory.resolve()
    if not root.is_dir() or options.j < 1:
        parser.error("expected a corpus directory and a positive job count")
    if not shutil.which("cc"):
        parser.error("cc is required to check generated C")
    paths = sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    scan = partial(check, root=root, directories=[root, *options.includes], source_encoding=options.source_encoding)
    counts = Counter()
    blockers = Counter()
    files = {}
    with ProcessPoolExecutor(max_workers=options.j) as pool:
        for name, status, diagnostic in pool.map(scan, paths, chunksize=16):
            counts[status] += 1
            files[name] = {"status": status}
            if diagnostic:
                files[name]["diagnostic"] = diagnostic
                reason = re.sub(r"^.*?:\d+:\d+: ", "", diagnostic)
                blockers[group(reason) if status == "rejected" else status] += 1
    print(json.dumps(dict(counts=counts, first_blockers=dict(blockers.most_common()), files=files),
                     indent=2))


if __name__ == "__main__":
    main()
