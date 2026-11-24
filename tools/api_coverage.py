"""Aggregate API observations from the corpus checker and render COVERAGE.md."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from textwrap import fill


CATALOGUES = {"expression": "functions.md", "defc": "header-functions.md"}
BACKENDS = {"DYNTOXML", "XMLTOXML", "XMLTODYN", "ITYPE", "INDICES", "JBASECOREDUMP"}

# These are assertions in the native suite. A fixture reference alone does
# not establish that the call executed or that its result was asserted.
RUNTIME_EVIDENCE = {
    ("expression", "BITOR", 2, None): ("Signed 32-bit output checked", "tests/snippets/bitor.b"),
    ("expression", "DATE", 0, None): ("Local date and epoch checked", "tests/test_compiler.py"),
    ("expression", "TIME", 0, None): ("Local clock checked", "tests/test_compiler.py"),
    ("expression", "TIMEDATE", 0, None): ("Local midnight rollover checked", "tests/test_compiler.py"),
    ("expression", "GETENV", 1, None): ("Environment lookup checked", "tests/io/getenv.b"),
    ("expression", "GETENV", 2, None): ("Environment lookup and output parameter checked", "tests/io/getenv.b"),
    ("expression", "PUTENV", 1, None): ("Environment updates checked", "tests/io/putenv.b"),
    ("expression", "FILEINFO", 2, None): ("Handle status and pathname checked", "tests/test_compiler.py"),
    ("expression", "INMAT", 0, None): ("Latest matrix load count checked", "tests/io/inmat.b"),
    ("expression", "INMAT", 1, None): ("Matrix bounds checked", "tests/io/inmat.b"),
    ("expression", "IOCTL", 3, None): ("Filename query and output parameter checked", "tests/test_compiler.py"),
    ("expression", "ENCRYPT", 3, "method 1"): ("ROT13 output checked", "tests/snippets/rot13.b"),
    ("expression", "DECRYPT", 3, "method 1"): ("ROT13 output checked", "tests/snippets/rot13.b"),
    ("expression", "ENCRYPT", 3, "method 4"): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "DECRYPT", 3, "method 4"): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "DYNTOXML", 2, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "DYNTOXML", 3, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "XMLTODYN", 2, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "XMLTODYN", 3, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "XMLTOXML", 3, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "INDICES", 1, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "INDICES", 2, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "ITYPE", 1, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
    ("expression", "JBASECOREDUMP", 2, None): ("Missing-backend diagnostic checked", "tests/test_compiler.py"),
}


def read_catalogues(directory):
    entries = {}
    fingerprints = {}
    for kind, filename in CATALOGUES.items():
        raw = (directory / filename).read_bytes()
        fingerprints[filename] = sha256(raw).hexdigest()
        count = 0
        for line in raw.decode("utf-8").splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(cells) == 3 and cells[0].startswith("`") and kind == "expression":
                name = cells[0].strip("`")
                declaration = cells[1].strip("`")
                guide_call = None
            elif len(cells) == 4 and cells[0].isdigit() and kind == "defc":
                declaration = cells[1].strip("`")
                name = declaration.split("(", 1)[0].split()[-1]
                guide_call = cells[2].strip("`") if cells[2] != "—" else None
            else:
                continue
            guide = re.search(r"\]\((https?://[^)]+)\)", cells[-1])
            entries[(kind, name)] = {
                "kind": kind, "name": name, "declaration": declaration,
                "guide_call": guide_call, "guide": guide[1] if guide else None,
            }
            if kind == "defc":
                entries[(kind, name)]["header_line"] = int(cells[0])
            nominal_arity = re.fullmatch(r"FUNC_PARM([0-3])", declaration)
            if nominal_arity:
                entries[(kind, name)]["nominal_arity"] = int(nominal_arity[1])
            count += 1
        if not count:
            raise ValueError(f"no {kind} entries in {directory / filename}")
    return entries, fingerprints


def record_calls(calls):
    def record(token, arity, kind, form):
        calls.append(((kind, token.word, arity, form), token.path, token.line, token.column))
    return record


def source_location(path, root):
    path = path.resolve()
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


class Coverage:
    def __init__(self, catalogue, root):
        self.entries, self.fingerprints = catalogue
        self.root = root
        self.forms = {}
        self.fixture_scan_failures = []

    def form(self, key):
        if key not in self.forms:
            kind, name, arity, variant = key
            self.entries.setdefault((kind, name), {"kind": kind, "name": name, "declaration": None,
                                                    "guide_call": None, "guide": None})
            support = "backend required" if kind == "defc" or name in BACKENDS else "call translates"
            if name in ("ENCRYPT", "DECRYPT"):
                support = {"method 1": "ROT13 implemented",
                           "computed method": "runtime support depends on method"}.get(variant, "backend required")
            evidence = RUNTIME_EVIDENCE.get(key)
            if arity == 3 and name in ("ENCRYPT", "DECRYPT"):
                variant = {"method 1": "method 1 (ROT13)", "method 4": "method 4 (Base64)"}.get(variant, variant)
            self.forms[key] = {
                "arity": arity, "variant": variant, "jbcc_support": support,
                "occurrences": 0, "units": 0, "c99_checked_units": 0,
                "example": None, "example_c99_checked": None, "snippet_references": [],
                "runtime_evidence": dict(zip(("result", "test"), evidence)) if evidence else None,
            }
        return self.forms[key]

    def add_unit(self, unit, status, calls):
        seen = set()
        for key, path, line, column in calls:
            form = self.form(key)
            form["occurrences"] += 1
            c99_example = status == "translated" and form["example_c99_checked"] is None
            if form["example"] is None or c99_example:
                example = {"unit": unit, "file": source_location(path, self.root), "line": line, "column": column}
                if form["example"] is None:
                    form["example"] = example
                if c99_example:
                    form["example_c99_checked"] = example
            if key not in seen:
                form["units"] += 1
                form["c99_checked_units"] += status == "translated"
                seen.add(key)

    def add_snippet(self, name, calls):
        for key in sorted({key for key, *_ in calls}, key=form_order):
            if key[:2] in self.entries:
                self.form(key)["snippet_references"].append(name)

    def report(self, options):
        for key in RUNTIME_EVIDENCE:
            if key[:2] in self.entries:
                self.form(key)
        rows = {key: dict(entry, forms=[]) for key, entry in self.entries.items()}
        for key in sorted(self.forms, key=form_order):
            rows[key[:2]]["forms"].append(self.forms[key])
        return {"catalogues_sha256": self.fingerprints, "scan": options,
                "fixture_scan_failures": self.fixture_scan_failures,
                "apis": [rows[key] for key in sorted(rows)]}


def form_order(key):
    return (*key[:3], key[3] or "")


def form_label(form):
    arity = form["arity"]
    return form["variant"] or f"{arity} {'argument' if arity == 1 else 'arguments'}"


def render_markdown(report):
    coverage = report["api_coverage"]
    apis = coverage["apis"]
    def observed(api):
        return any(form["occurrences"] for form in api["forms"])

    lines = [
        "# API coverage", "",
        "This snapshot covers expression calls and the direct `DEFC` declarations",
        "in the documentation repo's catalogues. The full JSON includes guide",
        "links, arities, recognized forms, occurrence and translation-unit",
        "counts, and example source locations. See the [scan command](README.md#api-coverage)",
        "to reproduce it.", "",
        f"The corpus scan passed strict C99 checking for {report['counts'].get('translated', 0):,} units.", "",
        "| Catalogue | Entries | Recognized in T24 | No recognized call in T24 |",
        "|---|---:|---:|---:|",
    ]
    for kind, title in (("expression", "Expression calls"), ("defc", "`JBC.h` declarations")):
        entries = [api for api in apis if api["kind"] == kind and api["declaration"] is not None]
        found = sum(map(observed, entries))
        lines.append(f"| {title} | {len(entries)} | {found} | {len(entries) - found} |")
    cited = sum(any(form["runtime_evidence"] for form in api["forms"]) for api in apis)
    fixture_references = sum(any(form["snippet_references"] for form in api["forms"]) for api in apis)
    lines.extend(["", f"Reviewed runtime assertions are linked for {cited} APIs. Repo snippets",
                  f"reference {fixture_references} APIs and are indexed in JSON.", "",
                  "## Runtime evidence by form", "",
                  "| API | Form | Guide | T24 units | jbcc support | Runtime evidence |",
                  "|---|---|---|---:|---|---|"])
    for api in apis:
        for form in api["forms"]:
            evidence = form["runtime_evidence"]
            if not evidence and not (form["occurrences"] and form["jbcc_support"] != "call translates"):
                continue
            label = form_label(form)
            result = f"[{evidence['result']}]({evidence['test']})" if evidence else "Unreviewed"
            guide = f"[Guide]({api['guide']})" if api["guide"] else "—"
            lines.append(f"| `{api['name']}` | {label} | {guide} | {form['units']} | {form['jbcc_support']} | {result} |")

    gaps = [(api["name"], form) for api in apis for form in api["forms"]
            if form["units"] and not form["runtime_evidence"] and not form["snippet_references"]]
    if gaps:
        lines.extend(["", "## Frequent T24 forms without a linked test", "",
                      f"The JSON contains {len(gaps)} observed forms with neither a reviewed runtime",
                      "assertion nor a snippet reference. The table shows up to ten forms,",
                      "ordered by the number of translation units.", "",
                      "| API | Form | T24 units |", "|---|---|---:|"])
        for name, form in sorted(gaps, key=lambda item: -item[1]["units"])[:10]:
            lines.append(f"| `{name}` | {form_label(form)} | {form['units']} |")

    lines.extend(["", "## Catalogue entries by corpus observation"])
    for kind, title in (("expression", "Expression calls"), ("defc", "JBC.h declarations")):
        entries = [api for api in apis if api["kind"] == kind and api["declaration"] is not None]
        for found, label in ((True, "recognized in T24"), (False, "with no recognized call in T24")):
            names = [f"`{api['name']}`" for api in entries if observed(api) == found]
            lines.extend(["", f"### {title} {label}", "", fill(", ".join(names) or "None.", width=88)])
    outside = [f"`{api['name']}` ({api['kind']})" for api in apis
               if api["declaration"] is None and observed(api)]
    if outside:
        lines.extend(["", "### Recognized calls outside the catalogues", "", fill(", ".join(outside), width=88)])
    lines.extend([
        "",
        "Counts reflect calls recognized by jbcc after include and equate expansion.",
        "A call in a shared include can contribute to several units. A zero count",
        "means this scan found no recognized call. Rejected units can contribute",
        "observations up to the first compiler diagnostic. The scan covers",
        "expression calls and declared external C calls. Statically referenced",
        "snippets are recorded in JSON as leads for test review. The runtime table",
        "links to reviewed assertions. Other runtime evidence is unreviewed.",
        "",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="JSON report from check_corpus.py --api-catalogue")
    args = parser.parse_args()
    print(render_markdown(json.loads(args.report.read_text(encoding="utf-8"))), end="")
