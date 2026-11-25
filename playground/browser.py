"""Stage a single project in Pyodide and translate it with jbcc."""

import io
import json
import os
import posixpath
import re
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory

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


def translate(sources):
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

    source, _ = compile_program(
        sources,
        [],
        browser=True,
        include_resolver=resolve_include,
        include_depth=16,
        source_filter=count_expansion,
    )
    return source


def project_files(project):
    files = project["files"]
    if len(files) > 32:
        raise Diagnostic("project exceeds 32 files")
    sources = {}
    total = 0
    for file in files:
        path = file["path"]
        if (
            len(path) > 240
            or path.startswith("-")
            or any(
                part in (".", "..") or not PART.fullmatch(part)
                for part in path.split("/")
            )
        ):
            raise Diagnostic("invalid project file path")
        if path in sources:
            raise Diagnostic("duplicate project file path")
        data = file["source"].encode("utf-8")
        total += len(data)
        if len(data) > 64 * 1024 or total > 256 * 1024:
            raise Diagnostic("source exceeds project size limit")
        sources[path] = data

    for path in sources:
        if any(str(parent) in sources for parent in Path(path).parents):
            raise Diagnostic("file path conflicts with a project directory")
    return sources


def compile_project(raw):
    diagnostics = io.StringIO()
    source = None
    try:
        project = json.loads(raw)
        files = project_files(project)
        units = [project["entry"], *project["units"]]
        if len(units) != len(set(units)) or any(
            unit not in files for unit in units
        ):
            raise Diagnostic(
                "entry and linked units must name distinct project files"
            )
        with TemporaryDirectory() as workspace:
            for path, data in files.items():
                file = Path(workspace, path)
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
            previous = os.getcwd()
            try:
                os.chdir(workspace)
                with redirect_stderr(diagnostics):
                    source = translate(list(map(Path, units)))
            finally:
                os.chdir(previous)
    except (Diagnostic, OSError, UnicodeError) as error:
        print(error, file=diagnostics)
    except RecursionError:
        print("source nesting exceeds the compiler limit", file=diagnostics)
    return json.dumps({"source": source, "diagnostics": diagnostics.getvalue()})
