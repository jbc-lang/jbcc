"""Read the component declarations used by the R19 corpus checker."""

import re
import sqlite3
from collections import Counter
from contextlib import closing

MEMBER = r"^[ \t]*(public|module|private)[ \t]+"
NAME = r"[A-Za-z][A-Za-z0-9_]*"
# R19 writes the result type after the parameters or before them
# (setException : string (...)), may add "implements <interface>", and
# declares service methods as "external" and Java-facing API members as
# "published" (EB.EnquiryHook), both public.
METHOD = re.compile(
    rf"^[ \t]*(?P<access>public|module|private|external|published)[ \t]+method[ \t]+(?P<name>{NAME})"
    r"(?:[ \t]+implements[ \t]+[\w.]+)?"
    r"\s*(?::\s*(?P<before>\w+)\s*)?\((?P<parameters>(?:[^(){}]|\(\))*)\)"
    r"\s*(?::\s*(?P<after>\w+))?(?:\s*\{|[ \t]*$)",
    re.M,
)
# Hook components declare interfaces: no body, and a result type such as
# list<string> or records.PAYMENTORDER:PaymentOrderRecord before the
# parameters. Every R19 call passes the implementing method's name first,
# then the declared parameters (all 32 calls of the 42 declarations).
INTERFACE = re.compile(
    rf"^[ \t]*(?P<access>public|module|private|external|published)[ \t]+interface[ \t]+(?P<name>{NAME})"
    r"\s*(?::\s*(?P<result>[^(){}\n]+?)\s*)?\((?P<parameters>(?:[^(){}]|\(\))*)\)",
    re.M,
)
# A parameter has an optional direction, a name and a type, which may be a
# domain class (CustomerDomain:Parent) with a multiplicity ([0..1]) or a
# list (list<string>, list<ST.StatementHook:ProductDetail>). A
# matrix parameter is marked with () after the name or the type.
PARAMETER = re.compile(
    r"(?:(?:INOUT|IN|OUT)\s+)?[A-Za-z][A-Za-z0-9._$%]*(\(\))?"
    r"\s+(?:list<[\w.:]+>|[A-Za-z][\w.]*(?::[\w.]+)?)(\(\))?\s*(?:\[[^\]]*\])?"
)
PROPERTY = re.compile(
    MEMBER + rf"property[ \t]+(readonly|readwrite|writeonly)[ \t]+({NAME})"
    r"(?:\s*:\s*string\s*\{([^{}]*)\}|[ \t]*$)",
    re.M,
)
# A matrix-backed property binds a COMMON matrix: ->R.NEW() or, with its
# rank, ->MAT.LEG(2). In all 116 numbered R19 bindings the number is the
# rank of the matrix in its insert, and every call passes that many indices.
MATRIX_PROPERTY = re.compile(
    r"\bjBC:[^\n]*->\s*[\w.$%]+\((?P<rank>[0-9]*)\)[ \t]*$", re.M
)
CONSTANT = re.compile(
    MEMBER + rf"constant[ \t]+({NAME})[ \t]*\([^()\r\n]+\)[ \t]*=[ \t]*(.*)$",
    re.M,
)
LITERAL = re.compile(r"""[+-]?[0-9]+(?:\.[0-9]+)?|[-_./:]|"[^"]*"|'[^']*'""")
TABLE = re.compile(
    MEMBER + rf"table[ \t]+({NAME})\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}", re.M
)
TABLE_BINDING = re.compile(r"^[ \t]*t24:[ \t]*[\w.$%]+[ \t]*$", re.M)
TABLE_FIELDS = re.compile(r"^[ \t]*fields\s*:\s*\{([^{}]*)\}", re.M)
TABLE_FIELD = re.compile(
    rf"^[ \t]*({NAME})[ \t]*\([^()\r\n]+\)[ \t]*=[ \t]*([0-9]+)[ \t]*$", re.M
)
# Operations generated for each t24: table, with the arities observed in
# every R19 call: reads take (id, error), locking reads add a retry argument,
# writes take (id, record) and deletes take (id).
TABLE_METHODS = {
    "Read": ("function", (False, False)),
    "CacheRead": ("function", (False, False)),
    "ReadNau": ("function", (False, False)),
    "ReadHis": ("function", (False, False)),
    "ReadU": ("function", (False, False, False)),
    "ReadUNau": ("function", (False, False, False)),
    "ReadUHis": ("function", (False, False, False)),
    "Write": ("subroutine", (False, False)),
    "WriteNau": ("subroutine", (False, False)),
    "WriteHis": ("subroutine", (False, False)),
    "Delete": ("subroutine", (False,)),
    "DeleteNau": ("subroutine", (False,)),
    "DeleteHis": ("subroutine", (False,)),
}


def declarations(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    for method in METHOD.finditer(source):
        # Parameters are separated by commas or, in some definitions, newlines.
        parts = [
            p.strip()
            for p in re.split(r"[,\n]", method["parameters"])
            if p.strip()
        ]
        matches = [PARAMETER.fullmatch(part) for part in parts]
        if all(matches):
            access = method["access"]
            yield (
                method["name"],
                (
                    "public" if access in ("external", "published") else access,
                    "function"
                    if method["before"] or method["after"]
                    else "subroutine",
                    tuple(bool(match[1] or match[2]) for match in matches),
                ),
            )
    for interface in INTERFACE.finditer(source):
        parts = [
            p.strip()
            for p in re.split(r"[,\n]", interface["parameters"])
            if p.strip()
        ]
        matches = [PARAMETER.fullmatch(part) for part in parts]
        if all(matches):
            access = interface["access"]
            yield (
                interface["name"],
                (
                    "public" if access in ("external", "published") else access,
                    "function" if interface["result"] else "subroutine",
                    (False,)
                    + tuple(bool(match[1] or match[2]) for match in matches),
                ),
            )
    for access, mode, name, binding in PROPERTY.findall(source):
        matrix = MATRIX_PROPERTY.search(binding)
        index = (False,) * int(matrix["rank"] or 1) if matrix else ()
        if mode != "writeonly":
            yield "get" + name, (access, "function", index)
            if matrix:
                yield "getDynArrayFrom" + name, (access, "function", ())
        if mode != "readonly":
            yield "set" + name, (access, "subroutine", index + (False,))
            # R19 sources call clear<Name>() with no arguments on scalar and
            # matrix-backed properties alike (5,023 calls).
            yield "clear" + name, (access, "subroutine", ())
            if matrix:
                yield "setDynArrayTo" + name, (access, "subroutine", (False,))
    for access, name, value in CONSTANT.findall(source):
        value = value.strip()
        if LITERAL.fullmatch(value):
            yield (
                name,
                (
                    access,
                    "constant",
                    value[1:-1] if value[0] in "\"'" else value,
                ),
            )
    for access, table, body in TABLE.findall(source):
        if not TABLE_BINDING.search(body):
            continue
        for method, (kind, signature) in TABLE_METHODS.items():
            yield f"{table}.{method}", (access, kind, signature)
        # The component-level read table<Name>(id, error), as in
        # AC.AccountOpening.tableAccount: 1,622 R19 calls, all with two arguments.
        yield f"table{table}", (access, "function", (False, False))
        fields = TABLE_FIELDS.search(body)
        if fields:
            for name, number in TABLE_FIELD.findall(fields[1]):
                # R19 source references field numbers across private table boundaries.
                yield (
                    f"{table}.{name}",
                    ("public", "constant", number.lstrip("0") or "0"),
                )


def read_component_members(catalogue, root):
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        components = db.execute(
            "SELECT component_name, rel FROM file_path "
            "WHERE extract = ? AND kind = 'component' AND component_name IS NOT NULL ORDER BY rel",
            (root.name,),
        ).fetchall()
    if not components:
        raise ValueError(
            f"no component definitions for extract '{root.name}' in {catalogue}"
        )
    by_component = {}
    conflicts = {}
    for component, relative in components:
        owner = component.casefold()
        source = (root / relative).read_text(
            encoding="utf-8", errors="surrogateescape"
        )
        declared = [
            (name.casefold(), member) for name, member in declarations(source)
        ]
        names = Counter(name for name, _ in declared)
        current = {
            name: member for name, member in declared if names[name] == 1
        }
        if owner in by_component:
            # Duplicate definitions are partial exports of one component, as
            # OB_AFW/TF.ErrorHandling.component lacks consumeException. Keep
            # a member declared in any of them; drop one they declare
            # differently.
            previous = by_component[owner]
            clashes = conflicts.setdefault(owner, set())
            clashes.update(
                name
                for name, member in current.items()
                if name in previous and previous[name] != member
            )
            current = {**previous, **current}
            for name in clashes:
                current.pop(name, None)
        by_component[owner] = current
    members = {
        f"{owner}.{name}": (*member, owner)
        for owner, declared in by_component.items()
        for name, member in declared.items()
    }
    # The export leaves out some tables that R19 sources read through a
    # known component, such as PP.SODEODGUI.PptSodeodjoblist.Read. A call
    # <component>.<table>.<operation> to an undeclared table falls back to
    # these entries: the standard operation signatures, with public access.
    # Members the definitions declare differently stay unresolved; mark them
    # so the compiler's fallbacks do not treat them as undeclared.
    for owner, names in conflicts.items():
        for name in names:
            members[f"{owner}.!{name}"] = ("conflict", "conflict", (), owner)
    for owner in by_component:
        for method, (kind, signature) in TABLE_METHODS.items():
            members[f"{owner}.*.{method.casefold()}"] = (
                "public",
                kind,
                signature,
                owner,
            )
    return members


BINDING = re.compile(
    r"jBC\s*:\s*(?P<insert>[\w.$%]+)\s*->\s*(?P<variable>[\w.$%]+)"
    r"(?:\((?P<rank>[0-9]*)\))?"
)


def property_bindings(source):
    """(accessor name, (operation, insert, variable, rank)) for each
    accessor of a property bound to an insert's variable, as
    `jBC: I_COMMON ->R.NEW()`. operation is get, set, clear,
    getDynArrayFrom or setDynArrayTo; rank is 0 for a scalar."""
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    for _access, mode, name, binding in PROPERTY.findall(source):
        bound = BINDING.search(binding or "")
        if not bound:
            continue
        rank = 0 if bound["rank"] is None else int(bound["rank"] or 1)
        operations = []
        if mode != "writeonly":
            operations += ["get"] + (["getDynArrayFrom"] if rank else [])
        if mode != "readonly":
            operations += ["set", "clear"] + (["setDynArrayTo"] if rank else [])
        for operation in operations:
            yield operation + name, (operation, bound["insert"], bound["variable"], rank)


def read_component_properties(catalogue, root):
    """Accessor member (casefolded, as component calls name it) ->
    (operation, insert, variable, rank), for every catalogued component."""
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        components = db.execute(
            "SELECT component_name, rel FROM file_path "
            "WHERE extract = ? AND kind = 'component' AND component_name IS NOT NULL ORDER BY rel",
            (root.name,),
        ).fetchall()
    accessors = {}
    for component, relative in components:
        source = (root / relative).read_text(encoding="utf-8", errors="surrogateescape")
        for name, binding in property_bindings(source):
            accessors.setdefault(f"{component}.{name}".casefold(), binding)
    return accessors


TABLE_FILE = re.compile(r"^[ \t]*t24:[ \t]*([\w.$%]+)[ \t]*$", re.M)


def read_component_tables(catalogue, root):
    """Component table (casefolded, as component calls name it, such as
    ac.accountopening.account) -> the T24 file it binds (ACCOUNT)."""
    uri = catalogue.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        components = db.execute(
            "SELECT component_name, rel FROM file_path "
            "WHERE extract = ? AND kind = 'component' AND component_name IS NOT NULL ORDER BY rel",
            (root.name,),
        ).fetchall()
    tables = {}
    for component, relative in components:
        source = (root / relative).read_text(encoding="utf-8", errors="surrogateescape")
        source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
        for _access, table, body in TABLE.findall(source):
            bound = TABLE_FILE.search(body)
            if bound:
                tables.setdefault(f"{component}.{table}".casefold(), bound[1])
    return tables
