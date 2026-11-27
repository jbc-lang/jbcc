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
  - [x] Table calls in expression form, including `ReadU` with a retry
    argument and `ReadHis`. The dump has no definition of the generated
    operations, so the arities come from all R19 calls: `ReadU` and
    `ReadUNau` take 3 arguments (2,568 calls), `ReadHis` 2 (258),
    `DeleteNau` and `DeleteHis` 1 (420).
  - [x] Property `clear` accessors, next to the existing `get`/`set`.
    All 5,023 calls take no arguments; all but one target a declared
    writable property.
  - [x] Legacy `table<Name>(id, err)` read accessors. Each of the 1,622
    calls names a `t24:` table of the same component, with two arguments.

  After these three, the full scan passes 38,445 of 39,675 units (96.9%),
  with no regressions.
  - [x] Method declaration forms the reader skipped: a result type before
    the parameters, `implements`, `external` service methods, domain-typed
    parameters with a multiplicity, parameters without a direction or
    separated by newlines. 1,210 more members are declared and none
    changes. The full scan passes 38,933 units (98.1%).
  - [x] `ReadUHis` (id, error, retry): all 278 calls. The full scan
    passes 39,210 of 39,675 units (98.8%), with no regressions. Of the
    465 rejections, 190 are undeclared members or other calls, 92
    language or parse issues, 92 argument kinds or index counts, 83 test
    framework units and 8 includes.
  - [ ] Methods and accessors without a matching declaration. Some are
    missing from the export: `PP.StaticDataGUI` declares no `PptLanguage`
    table, `PP.InwardGenericTransactions` no `PpInDirectDebitInit` and
    `USREGS.RegD` no `RegDViolationHist`, yet sources read all three.
  - [ ] Methods used inside expressions, and methods declared without a
    return value but used as one.
  - [ ] Argument kind and index-count mismatches (92 units). **Needs a
    decision.**
    - A scalar passed for a matrix parameter: 38 units call
      `ST.CompanyCreation.EbReadParameter` with a scalar such as
      `DIM.R.INSTALL.CONDS = ""` for `DimParamRec string()`. jbcc rejects
      this, but T24 ships it.
    - Two indices on matrix-backed properties, as in
      `BL.Foundation.getBlRAmdNewBrList(1, BL.Foundation.BlListCtr)` and
      `FX.Contract.getMatLeg(LEG, FLD.NO)`. The `jBC: ->X()` binding
      doesn't give the number of dimensions, so the reader assumes one.
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
  - Associations (`name -> byValue Domain:Class *`) count as fields:
    sources use them as positions, as in
    `ioPaymentObject<PaymentObject.transaction,1,Transaction.fileSendersReference>`.
    No sample shows a class with both associations and attributes, so
    their relative numbering is inferred.

  Coverage: 714 of the 716 missing inserts (3,043 units) resolve to a
  `.domain` class. The other 2, one unit each, are
  `I_InwardCreditTransferInitiationService_BulkDetails` and
  `I_InwardCreditTransferInitiationDASService_PORCreditTransferInitiation`.

  - [x] Extend `t24-extract` to copy `.domain` files and catalog their
    classes, then rebuild and verify the R19 extract. Branch
    `feat/domain-files` adds the 1,139 files and a `domain_field` table
    with 199,751 fields (50,258 of them associations). All 262,693 R19
    files match their catalog hashes.
  - [x] Generate the inserts in the corpus checker from the catalogued
    classes, report each generated insert per unit, and add an
    independent fixture. `--t24-domain-inserts DIR` generates a missing
    insert from the `.domain` file in the same folder as the service's
    `.component`. The full scan now generates 17,222 include lookups and
    passes 34,702 of 39,675 units (87.5%, up from 32,001), with no
    regressions. Eight units still stop at an include: the two
    unresolved inserts (6 units) and the ambiguous
    `I_DAS.POR.CLG.IN.SETTLEMENT.PENDING` (2 units).
  - [ ] Resolve the 2 remaining inserts.
- [ ] 4. Test framework units (113). Decide whether the `SE_Test*`
  routines and `TF.*` helpers are in scope. If they are, find their
  component declarations.
- [ ] 5. Remaining language gaps. Triage each against the guide, then
  implement it or record a source fix.
  - [x] `ISUPPER`, `ISLOWER` and `ISSPACE` (ASCII, like `ISALNUM`).
  - [x] `MSLEEP` (13 uses).
  - [x] `CLEARCOMMON` (11 uses): clears the unnamed COMMON only, as in the
    guide's jBASE example.
  - [x] `MAKETIMESTAMP`, `LOCALDATE`, `LOCALTIME`, `TIMEDIFF` (masks 0
    and 1) and `@TIMEZONE` (`JBASE_TIMEZONE`, then `TZ`; provisional).
  - [x] `UNASSIGNED` of a component call, such as
    `UNASSIGNED(IN.Config.getBicDetails())`: the result counts as
    assigned, as the reference treats any expression (provisional).
  - [x] A stray `END` after the final `END` (10 units): ignored with a
    warning, as the reference does (warning 47).
  - [x] Two `DAS` inserts that end an `EQU` with a comma and repeat `EQU`:
    a source fix, since the reference rejects them too. R19 fixes name
    the path from the extract root.

  After these, the full scan passes 39,299 of 39,675 units (99.05%), with
  no regressions.
  - [ ] Assignment to `@COMPANYNO` (2 units). Neither the guide nor the
    2011 reference knows it ("Unknown @ system constant"). **Needs
    evidence.**
  - [ ] `ICONV`/`OCONV` with the `DG` mask, which R19 uses. It fails only
    when reached, so translation does not depend on it.
- [ ] 5a. Guide examples. Ship a small `JBC.h` with jbcc that defines the
  `EQUATE` constants the jBC guide's examples use (IOCTL commands, cache
  options, `ENCRYPT` methods, user record positions), written from the
  guide rather than copied from the jBASE header. 34 guide code blocks
  include it. Most of them still need files or the jBASE C runtime, so few
  will run in the playground; the gain is that they translate. Also add
  the `MCP` conversion mask, which 30 guide blocks use and which is their
  only failure. After the next jbcc release, rerun `just examples` in
  jbc-language.
- [ ] 6. Close the pilot's open item: find a declaration for
  `EB.Service.setFComo`, or record why it is missing.
- [ ] 7. Re-run R07, R10 and R13 to check for regressions and update
  counts.

Out of scope for this plan: package-aware linkage across units, table
runtime behaviour, and running the `.tut` unit tests with their `.d`
records. Each needs its own plan once translation is complete.
