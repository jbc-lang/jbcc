"""Translate a staged playground workspace to C for Emscripten."""

import argparse
import posixpath
import re
import sys
from pathlib import Path

from jbcc.compiler import Diagnostic, SourceLimitError, compile_program

PART = re.compile(r"[A-Za-z0-9_.-]+")


def resolve_include(source, name, _, token):
    if any(not PART.fullmatch(part) for part in name.split("/")):
        raise Diagnostic(
            f"{source}:{token.line}:{token.column}: invalid include path '{name}'"
        )
    relative = posixpath.normpath(
        posixpath.join(source.parent.as_posix(), name)
    )
    if relative == ".." or relative.startswith("../"):
        raise Diagnostic(
            f"{source}:{token.line}:{token.column}: include escapes project root"
        )
    if Path(relative).is_file():
        return Path(relative)
    root = posixpath.normpath(name)
    if root != ".." and not root.startswith("../") and Path(root).is_file():
        return Path(root)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("sources", nargs="+", type=Path)
    args = parser.parse_args()
    remaining = 1024 * 1024

    def count_expansion(path, source):
        nonlocal remaining
        # Count staged bytes, including CRLF and repeated includes across units.
        remaining -= path.stat().st_size
        if remaining < 0:
            raise SourceLimitError(
                f"{path}:1:1: expanded source limit exceeded"
            )
        return source

    try:
        source, _ = compile_program(
            args.sources,
            [],
            browser=True,
            include_resolver=resolve_include,
            include_depth=16,
            source_filter=count_expansion,
        )
        args.output.write_text(source, encoding="utf-8")
    except SourceLimitError as error:
        print(error, file=sys.stderr)
        return 2
    except RecursionError:
        print("source nesting exceeds the compiler limit", file=sys.stderr)
        return 2
    except (Diagnostic, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
