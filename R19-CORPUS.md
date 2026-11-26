# R19 corpus plan

Goal: jbcc translates every production source unit in the local R19
extract (`../t24-extract/201809-R19`) to C that passes strict C99
checking, as it already does for R07, R10 and R13. This continues the
[R19 pilot](PLAN.md#r19-pilot), which covered 146 units, and follows the
[R13 plan](R13-CORPUS.md).

R19 differs from the earlier releases in kind, not only in size. It is
componentised T24: sources declare `$PACKAGE` and `$USING`, call
qualified component methods, read tables through generated accessors and
include inserts generated from `.domain` models. The local reference
compiler (`../jbc-extract`, 201015.001, 2011) predates all of this, so
it cannot serve as an oracle here. Component behaviour has to come from
the catalogued `.component` declarations and from how the sources use
them.

## Trial scan (2026-11-26, jbcc 0.3.0)

```sh
python3 tools/check_corpus.py ../t24-extract/201809-R19 -I .cache/PB201214/include \
  --t24-catalog ../t24-extract/catalog.sqlite --t24-indexed-includes \
  --t24-component-calls --source-encoding bytes --defer-unassigned-reads \
  --quiet-next-warnings --t24-source-fixes -j 8 > /tmp/jbcc-r19.json
```

32,001 of 39,675 catalogued production units (80.7%) translated and
passed strict C99 checking; 7,674 were rejected. Indexed lookup resolved
57,284 include references and missed 3,045. Wall time was 4 min 3 s with
8 workers.

First blockers, grouped by cause:

| Group | Units | Detail |
|---|---:|---|
| Domain-generated includes | 3,044 | 716 distinct `I_<Service>_<Class>` inserts, such as `I_CustomerService_NameAddress` (261 units). None exist in the extract or the original dump; they are generated from `.domain` models |
| Component calls | 4,388 | See below |
| Test framework | 113 | `SE_Test*` units and `TF.*` helpers such as `TF.L3Helper.getInstance` and `TF.List.get` |
| Other language and parse issues | 129 | `MSLEEP`, `CLEARCOMMON`, `@TIMEZONE`, `expected THEN or ELSE` (24), `expected ')'` (36), `unexpected '('` outside component calls (17), text after the final `END` (9) |

Component calls by form:

| Form | Units | Example |
|---|---:|---|
| Table calls used as expressions | 2,205 | `r = AM.Foundation.Parameter.ReadU(id, err, retry)`, `SC.SctSettlement.Settlement.ReadHis(...)` |
| Property `clear` accessors | 1,108 | `EB.SystemTables.clearF`, `clearRNew`, `clearROld` |
| Legacy `table<Name>` read accessors | 582 | `R.ACCOUNT = AC.AccountOpening.tableAccount(ACCT.NO, AC.ERR)` |
| `get`/`set` accessors without a matching declaration | 204 | `EB.API.setException`, `ST.CustomerService.getRecord` |
| Methods without a matching declaration | 132 | `AA.ActivityHook.checkValidateRoutine` |
| Methods called inside expressions | 102 | `EB.Browser.SystemGetvariable(...)`, `AA.Framework.OptionSelected(...)` |
| Arguments that disagree with the declaration | 55 | `ST.CompanyCreation.EbReadParameter` (23) |

About a dozen units call a method declared without a return value inside
an expression, for example `EB.DataAccess.FRead`.

## Steps

- [ ] 1. Record the baseline. Replace the README's "R19 pilot" section
  with the full-corpus command, add an R19 row to the performance table
  and add an "R19 baseline" section to PLAN.md.
- [ ] 2. Component calls. Each item cites the `.component` declaration and
  the sources that use the form. Write independent fixtures under
  `tests/corpus/component-calls`.
  - [ ] Table calls in expression form, including `ReadU` with a retry
    argument and `ReadHis`. Establish the generated signatures from the
    table definitions in the catalog.
  - [ ] Property `clear` accessors, next to the existing `get`/`set`.
  - [ ] Legacy `table<Name>(id, err)` read accessors: find where they
    are declared, or the rule that generates them.
  - [ ] Methods and accessors without a matching declaration (336 units).
    For each name, decide whether the declaration is missing from the
    extract, sits in a component the checker doesn't read, or is
    generated.
  - [ ] Methods used inside expressions, and methods declared without a
    return value but used as one.
  - [ ] Argument count and kind mismatches (55 units).
- [ ] 3. Domain-generated includes. The extract left out the 1,139
  `.domain` model files: `extract_jbc.py` selects only `*.b`, `*.tut`,
  `I_*`, `*.d` and `*.component`. The original dump
  (`~/Downloads/201809`) has all of them. It also keeps 30 generated
  inserts, which give the generator's rule:
  - `I_<Service>_<Class>` describes class `<Class>` of the `.domain` file
    in the component whose `.component` name ends in `<Service>`. For
    example, `I_CustomerService_NameAddress` comes from `NameAddress` in
    `ST/ST_CustomerService/Definition/CustomerDomain.domain`.
  - The body is one `EQU <Class>.<field> TO <n>` line per field, numbered
    from 1 in declaration order. Multi-valued (`*`) fields take one
    position each. Sources read fields as
    `customerNameAddress<NameAddress.shortName>`.
  - The rule reproduces all 20 sample inserts whose `.domain` file is in
    the dump. The other 10 are `I_AccountService_*`, whose domain model
    is missing but whose inserts are already extracted.
  - No sample covers a field whose type is another class.

  Coverage: 708 of the 716 missing inserts (3,035 units) resolve to a
  `.domain` class. The other 8, in 9 units, name a service whose
  `.domain` file lacks the class.

  - [ ] Extend `t24-extract` to copy `.domain` files and catalog their
    classes, then rebuild and verify the R19 extract.
  - [ ] Generate the inserts in the corpus checker from the catalogued
    classes, report each generated insert per unit, and add an
    independent fixture.
  - [ ] Resolve the 8 remaining inserts.
- [ ] 4. Test framework units (113). Decide whether the `SE_Test*`
  routines and `TF.*` helpers are in scope. If they are, find their
  component declarations.
- [ ] 5. Remaining language gaps: `MSLEEP`, `CLEARCOMMON`, `@TIMEZONE`
  and the parse errors. Triage each against the guide, then implement
  it or record a source fix.
- [ ] 6. Close the pilot's open item: find a declaration for
  `EB.Service.setFComo`, or record why it is missing.
- [ ] 7. Re-run R07, R10 and R13 to check for regressions and update
  counts.

Out of scope for this plan: package-aware linkage across units, table
runtime behaviour, and running the `.tut` unit tests with their `.d`
records. Each needs its own plan once translation is complete.
