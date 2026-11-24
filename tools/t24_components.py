"""Read the component declarations used by the R19 corpus checker."""
from collections import Counter
from contextlib import closing
import re
import sqlite3


MEMBER = r"^[ \t]*(public|module|private)[ \t]+"
NAME = r"[A-Za-z][A-Za-z0-9_]*"
METHOD = re.compile(
    MEMBER + rf"method[ \t]+({NAME})\s*\(((?:[^(){{}}]|\(\))*)\)"
    r"\s*(?::\s*(string))?\s*\{", re.M
)
PARAMETER = re.compile(r"(?:INOUT|IN|OUT)\s+[A-Za-z][A-Za-z0-9._$%]*\s+string(\(\))?")
PROPERTY = re.compile(
    MEMBER + rf"property[ \t]+(readonly|readwrite|writeonly)[ \t]+({NAME})"
    r"(?:\s*:\s*string\s*\{([^{}]*)\}|[ \t]*$)",
    re.M
)
MATRIX_PROPERTY = re.compile(r"\bjBC:[^\n]*->\s*[\w.$%]+\(\)[ \t]*$", re.M)
CONSTANT = re.compile(
    MEMBER + rf"constant[ \t]+({NAME})[ \t]*\([^()\r\n]+\)[ \t]*=[ \t]*(.*)$", re.M
)
LITERAL = re.compile(r"""[+-]?[0-9]+(?:\.[0-9]+)?|[-_./:]|"[^"]*"|'[^']*'""")
TABLE = re.compile(MEMBER + rf"table[ \t]+({NAME})\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}", re.M)
TABLE_BINDING = re.compile(r"^[ \t]*t24:[ \t]*[\w.$%]+[ \t]*$", re.M)
TABLE_FIELDS = re.compile(r"^[ \t]*fields\s*:\s*\{([^{}]*)\}", re.M)
TABLE_FIELD = re.compile(rf"^[ \t]*({NAME})[ \t]*\([^()\r\n]+\)[ \t]*=[ \t]*([0-9]+)[ \t]*$", re.M)
TABLE_METHODS = {
    "Read": ("function", (False, False)),
    "CacheRead": ("function", (False, False)),
    "ReadNau": ("function", (False, False)),
    "Write": ("subroutine", (False, False)),
    "WriteNau": ("subroutine", (False, False)),
    "WriteHis": ("subroutine", (False, False)),
    "Delete": ("subroutine", (False,)),
}


def declarations(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    for access, name, parameters, result in METHOD.findall(source):
        parts = parameters.split(",") if parameters.strip() else []
        matches = [PARAMETER.fullmatch(part.strip()) for part in parts]
        if all(matches):
            yield name, (access, "function" if result else "subroutine",
                         tuple(bool(match[1]) for match in matches))
    for access, mode, name, binding in PROPERTY.findall(source):
        matrix = bool(MATRIX_PROPERTY.search(binding))
        index = (False,) if matrix else ()
        if mode != "writeonly":
            yield "get" + name, (access, "function", index)
            if matrix:
                yield "getDynArrayFrom" + name, (access, "function", ())
        if mode != "readonly":
            yield "set" + name, (access, "subroutine", index + (False,))
            if matrix:
                yield "setDynArrayTo" + name, (access, "subroutine", (False,))
    for access, name, value in CONSTANT.findall(source):
        value = value.strip()
        if LITERAL.fullmatch(value):
            yield name, (access, "constant", value[1:-1] if value[0] in "\"'" else value)
    for access, table, body in TABLE.findall(source):
        if not TABLE_BINDING.search(body):
            continue
        for method, (kind, signature) in TABLE_METHODS.items():
            yield f"{table}.{method}", (access, kind, signature)
        fields = TABLE_FIELDS.search(body)
        if fields:
            for name, number in TABLE_FIELD.findall(fields[1]):
                # R19 source references field numbers across private table boundaries.
                yield f"{table}.{name}", ("public", "constant", number.lstrip("0") or "0")


def read_component_members(catalogue, root):
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        components = db.execute(
            "SELECT component_name, rel FROM file_path "
            "WHERE extract = ? AND kind = 'component' AND component_name IS NOT NULL ORDER BY rel",
            (root.name,),
        ).fetchall()
    if not components:
        raise ValueError(f"no component definitions for extract '{root.name}' in {catalogue}")
    by_component = {}
    for component, relative in components:
        owner = component.casefold()
        source = (root / relative).read_text(encoding="utf-8", errors="surrogateescape")
        declared = [(name.casefold(), member) for name, member in declarations(source)]
        names = Counter(name for name, _ in declared)
        current = {name: member for name, member in declared if names[name] == 1}
        if owner in by_component:
            # Duplicate definitions can be partial exports of the same component.
            current = {name: member for name, member in by_component[owner].items()
                       if current.get(name) == member}
        by_component[owner] = current
    return {f"{owner}.{name}": (*member, owner)
            for owner, declared in by_component.items() for name, member in declared.items()}
