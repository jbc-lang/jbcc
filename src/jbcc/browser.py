"""Python API for translating jBC projects to C for a browser host."""

from pathlib import Path
from typing import Callable, Optional, Sequence

from .compiler import (
    Diagnostic,
    SourceLimitError,
    compile_program,
    read_runtime,
)

__all__ = ["Diagnostic", "SourceLimitError", "read_runtime", "translate"]

IncludeResolver = Callable[[Path, str, int, int], Optional[Path]]
SourceFilter = Callable[[Path, str], str]


def translate(
    paths: Sequence[Path],
    *,
    include_resolver: IncludeResolver,
    include_depth: Optional[int] = None,
    source_filter: Optional[SourceFilter] = None,
    emulation: str = 'prime',
) -> str:
    """Return standalone C for a main program and its linked routines.

    emulation is 'prime' (the default, as T24 runs) or 'jbase'.
    """

    def resolve(source, name, _directories, token):
        return include_resolver(source, name, token.line, token.column)

    source, _ = compile_program(
        paths,
        [],
        browser=True,
        include_resolver=resolve,
        include_depth=include_depth,
        source_filter=source_filter,
        emulation=emulation,
    )
    return source
