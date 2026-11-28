# Running T24's `.tut` unit tests

Goal: jbcc builds and runs T24 R19's own unit tests (`*.tut`) and reports
which pass. A passing test is evidence that jbcc translated and ran the
target routine correctly, beyond the corpus scans, which only translate.

The R19 corpus (`../t24-extract/201809-R19`) is proprietary: never copy a
test, a target or a record into this repository. Runs read the corpus in
place, and results are written to reports outside the repository. When a
test shows a construct jbcc gets wrong, write a small independent snippet
for jbcc's own tests and note which corpus file showed it (the corpus's
AGENTS.md).

## What the corpus holds (2026-11-27)

- **26,307 tests**, all in R19. 25,877 are under `<Module>/<Component>/Test/UnitTests/`, and 430 are in flat folders. R07, R10 and R13 have none.
- **The format:** each test is a `TESTCASE name` unit that drives the UTF framework through `UTF.*` calls and ends with `END`. Name and target: `AA.CHECK.RECALCULATE.OPTION_14` tests `AA.CHECK.RECALCULATE.OPTION`.
- **Targets:** every test calls `UTF.setTarget`. 18,300 pass the routine name as a literal; the others assign it to a variable first, usually `RoutineName`. Of the literal targets:

  | Kind | Tests |
  |---|---|
  | SUBROUTINE | 15,296 |
  | Component method (such as `AA.Framework.getX`) | 2,821 |
  | FUNCTION | 138 |
  | PROGRAM | 7 |
  | Not in the corpus | 38 |

- **Runs:** 19,032 tests call `UTF.runTest()` once, 3,770 twice and 3,505 three times or more. The later runs use `UTF.reset` and `UTF.setRepeatable`.
- **Isolation:** 24,042 tests stub routines or seed records. 2,265 do neither, and 1,253 of those have a literal SUBROUTINE or FUNCTION target. Their median length is 77 lines.
- **The `.d` records** (185,691) aren't test fixtures. They are T24 system and model-bank data, one field per line:

  | File | Records |
  |---|---|
  | `F.EB.DICTIONARY` | 69,908 |
  | `F.EB.ERROR` | 27,703 |
  | `F.PGM.FILE` | 8,813 |
  | `F.FILE.CONTROL` | 5,811 |
  | `F.STANDARD.SELECTION` | 5,033 |

  A target can still read them, for example to look up an error message.

### The UTF API, by use

| Call | Uses | Meaning, as the tests and their template comments show it |
|---|---|---|
| `addStubParam(stub, in, out)` | 591,939 | for a stubbed call: the expected argument (a value, `UTF.any()` or `UTF.matches(pattern)`) and the value to return in it (`UTF.same()` leaves it) |
| `any()` | 386,678 | matches any argument |
| `same()` | 331,487 | leaves the argument unchanged |
| `addStub(name)` | 160,138 | stubs a routine the target calls; returns a handle |
| `addParam(var)` | 104,648 | the target's next argument, **by reference**: tests assert on the same variable after `runTest` |
| `assertEquals(actual, expected)` | 74,103 | the main check |
| `setRepeatable` | 66,928 | lets a stub answer more than one call (inferred) |
| `runTest()` | 45,160 | calls the target with the parameters |
| `reset` | 37,942 | clears parameters and stubs between runs (inferred) |
| `setRecord(file, key, record)` | 34,941 | seeds a record the target reads |
| `setTestNumber`, `setDescription` | 57,661 | labels only |
| `setTarget(name)` | 26,313 | the routine under test |
| `getNbInvocation(stub)` | 21,142 | how often a stub was called |
| `setParam` | 15,052 | replaces a parameter (inferred) |
| `ignoreMissingStubs` | 8,635 | lets the target call routines that are not stubbed. So without it, an unstubbed call is a failure (inferred). |
| `getRecord(file, key)` | 4,484 | reads a record back after the run |
| `addStubPropertyChange`, `addStubCommonChange`, `addStubCacheChange` | 6,448 | a stub that also changes a property, a COMMON variable or the cache |
| `assertContains`, `assertTrue`, `assertFalse`, `assertNotEquals`, `matches`, `contains` | about 9,000 | further checks |

Others with fewer than 400 uses include `addStubPropertyCondition`,
`setStubReturnValue`, `addStubWriteDone` and `setEASYQAMode`.

### No reference implementation

UTF isn't in the dump. No jBC routine, component, Java class or jar
defines `UTF.*`, and TAFC PB201214 has no trace of it either. It is a
TAFJ-era (Java) framework. Unlike the TAFC cross-check (TAFC-CROSSCHECK.md),
there's no runtime to probe, so jbcc has to implement UTF from its use. The
tests' own assertions are the only check: a test that passes supports
both the target's translation and the UTF semantics it relies on, and a
failure can come from either.

## Plan

### 1. Translate the tests

- [x] Parse `TESTCASE name` units ending in `END`, as a program whose body
      is the test. `TESTCASE` at the start of a unit names the program, as
      `PROGRAM` does.
- [x] Translate `UTF.*` calls, both as statements and in expressions, to
      runtime calls, with the argument forms the tests use. Each call
      becomes `jbc_utf(method, count, arguments)`. A variable argument
      is passed by reference, an expression as a value, and a matrix
      whole, written `MAT X` or just `X`. Matrix support alone let
      697 more tests translate, mostly ones passing a DIMmed array or
      `R.NEW`. Until step 2, the runtime stops at the first
      UTF call.
- [x] Scan all 26,307 tests with `tools/check_corpus.py`, using the R19
      flags plus a test kind, and record the baseline: how many translate,
      and the first blockers. The option is `--t24-tests`, added to the
      R19 production flags.

#### Step 1 baseline (2026-11-27)

25,875 of the 26,307 tests translate to C that passes strict C99 checking.
23 are excluded, like the production units, for a domain class missing
from the dump, and 409 are rejected. The scan takes 3 min 29 s with 8
workers. On the way, jbcc learned to split string literals longer than
C99's 4,095-byte limit, which 21 tests use.

The rejections are mostly errors in the test sources that TAFC PB201214
rejects too:

| First blocker | Tests | Cause |
|---|---|---|
| `unexpected '@'`, `expected ')'` | 192 | a missing `:` before a system variable, as in `""@VM:""`; TAFC: syntax error |
| `expected '('` | 49 | `<>` on a matrix such as `R.NEW<X> = ...`, or MATBUILD into a matrix |
| `unexpected text after final END` | 24 | a second test body pasted after `END`; TAFC: syntax error |
| `unexpected '.'` | 14 | a stray `.` at the end of a line |
| `expected a dimensioned array ...` | 51 | `MAT X` for an X that is not DIMmed |
| `unsupported statement 'CachePut'`, `'PUTENV'` | 22 | JBC.h cache and PUTENV called as statements without their declarations; worth supporting |
| others | 57 | typos such as `TF.addStubParam`, and one-off forms |

These tests were presumably run only under TAFJ, which may accept some of
these forms, or never run. jbcc keeps TAFC's rules. The JBC.h and PUTENV
statement forms are the only ones to look at later.

### 2. A UTF runtime and a test runner

- [x] **UTF state:** the target, its parameters (as references), the
      runs and checks, and the first failure. In the runtime, under
      `JBC_UTF`, which only programs that call UTF get.
- [x] **`runTest`:** calls the target, a SUBROUTINE or FUNCTION of the
      program, with the parameters, and returns a FUNCTION's result. The
      program ends with a verdict as its last stderr line and exit status:
      passed (0), failed with the first failing check (3), unsupported (4:
      a UTF method of a later step, such as `addStub`) or not run (5).
      Checks: `assertEquals` and `assertNotEquals` (jBC `=`, so `"01"`
      equals `1`), `assertTrue`, `assertFalse`, `assertContains`,
      `assertStartsWith`, `assertEndsWith`, `assertMatches` (jBC
      `MATCHES`) and `assertLessThan`.
- [x] **A runner:** `tools/run_tuts.py`, or `just tut report.json`:
  - finds the target in `UTF.setTarget`, a literal or a variable assigned
    one; a component method (`AA.Account.AccountMaintain`) maps to its
    routine through the catalog's method table, or by the test's own
    name (`AA.ACCOUNT.VALIDATE.BUNDLE.HIERARCHY_1`) when the exported
    definition leaves the method out;
  - builds the test with its target, with the R19 scan's settings;
  - runs it with a time limit (10 s), in a fresh directory;
  - writes a JSON report with one state per test: no target, target
    missing, rejected, unlinked (with the first routine missing),
    not built, passed, failed (with the check), unsupported, not run,
    error (a runtime stop), crashed or timeout.

Inferred behaviour, to revisit as more tests run:

- `runTest` passes missing trailing parameters empty: some tests run a
  target with fewer parameters than it takes.
- `setParam(n, value)` sets parameter n, adding empty ones before it: a
  test calls it after `reset`, with no parameters left.
- `reset` clears the parameters and keeps the target (and, step 5, clears
  the stubs).

#### Step 2 baseline (2026-11-28)

All 26,307 tests in 2 min 53 s with 8 workers:

| State | Tests | Main causes |
|---|---:|---|
| passed | 745 | the target ran and every check held |
| failed | 26 | 11 in `EB.TABLE.DEF.MULTI.SUB.VALIDATE` (a count of 4 against 3), 2 UTF-8 transliterations in `SepaUtf8Process`, single date and code values |
| unsupported | 86 | `setEASYQAMode` (25), `addStub` (22), `ignoreMissingStubs` (19), `setRecord` (10) |
| error | 56 | `expected an integer dynamic-array index` (31), `PWR` out of range, DYNTOXML and calendar backends |
| timeout | 24 | |
| unlinked | 24,885 | 2,487 distinct first missing routines; 17,577 tests stop at an R19 component property accessor such as `EB.SystemTables.setRNew` (1,786) or `setIdNew` (1,431), and 2,087 at `TPSLogging`, a PP logging subroutine that linking on demand will bring in |
| rejected | 457 | the step 1 source errors, as with `--t24-tests` |
| target missing, no target | 28 | |

The accessors are the next blocker (step 4): R19 generates a `get`/`set`
pair for each component property, over a COMMON variable of the
component's insert.

### 3. A first set: no stubs, no records

Overtaken by steps 4 to 6: with stubs and records in place, the whole
corpus runs at once, and the report's states take the place of a fixed
set.

### 4. Linking targets

A target calls other routines: T24 library routines, component methods
and its own helpers.

- [x] Following the calls transitively doesn't work: T24's call graph is
      dense, and 186 of the first 300 tests needed more than 800
      routines. UTF tests are written for isolation instead: they stub
      what the target calls, and `ignoreMissingStubs` exists. So a test
      build links the test, its target and the component property
      accessors they use; every other routine the program calls gets a
      generated body that the UTF runtime answers (`link_units(...,
      stub_missing=True)`).
- [x] Component property accessors (`EB.SystemTables.setRNew(field,
      value)`, `getToday()`, `clearE()`, `getDynArrayFromRNew()`) are
      generated as jBC units from each property's binding in its
      component, as `jBC: I_COMMON ->R.NEW()`: a get, set or clear of the
      COMMON variable or matrix element. They include `I_COMMON` and
      `I_EQUATE` first, as T24 routines do; other inserts size their
      matrices with `I_COMMON`'s `EQU C$SYSDIM TO 500`.
- [ ] Settle how `ignoreMissingStubs` behaves. Now an unstubbed call does
      nothing; the other reading, running the real routine, needs
      transitive linking for those calls only.

### 5. Stubs

- [x] `addStub(name)` returns a handle. Each `addStubParam(stub,
      expected, returned)` describes the next parameter: the value the
      call must pass, or `any()`, `matches(pattern)`, `contains(text)`,
      `greaterThan(n)` or `lessThan(n)`; and the value the stub returns
      there, or `same()` (or `any()`) to leave it.
- [x] A call goes to a stub of its name, in any case, whose expected
      values and conditions match and which isn't used up (a stub answers
      once unless `setRepeatable`). Of those, the most specific answers:
      the one with the most expected values and conditions that aren't
      `any()`; of equally specific ones, the newest. A call no stub
      matches fails the test with the call and its arguments, unless
      `ignoreMissingStubs`. Evidence: `AA.ACCOUNT.SETTLE.SUSP_2` defines
      two equally specific stubs and expects the second to answer;
      `EB.USER.ROLES.VALIDATE_005` defines a stub with two conditions and
      then a general one, and expects the first. Taking the first match
      (step 4 to 6 runs) left 569 invocation counts at 0; taking the
      newest instead passed 1,133 more tests but lost 199, of which
      specificity recovers 170.
- [x] `reset` clears the parameters, the stubs and the call counts, and
      keeps the target and the records: tests define their stubs again
      after each `reset`.
- [x] `setStubReturnValue` (a FUNCTION's result), `getNbInvocation` (a
      handle, or a routine name for every call to it),
      `addStubCommonChange(stub, VAR, value)` and
      `addStubPropertyChange(stub, component, property, value)`.
- [x] A handle that was never created, as `setRepeatable(stub)` after
      `STUB = addStub(...)`, is ignored.
- [x] `addStubPropertyCondition(stub, component, property, value)` and
      `addStubCommonCondition(stub, VAR, value)`: the stub answers only
      while the property or COMMON variable has the value. Tests chain
      stubs this way, each moving `Comi` on for the next.
- [x] `addStubWriteDone(stub, file, key, record)` writes the record when
      the stub answers; `addStubCommonChange` on a COMMON matrix such as
      `R.NEW` fills it from the value's fields, as MATPARSE does.
- [x] `setStopping(stub)`: the call ends the target's run, as a routine
      that stops processing (`StoreEndError`); `runTest` returns.
- [x] `addEasyQAStub(name, n, MAT in, MAT out, error)`, from tests
      converted from EASYQA recordings: a repeatable stub whose expected and
      returned values come from the matrices, where `'*'` is `any()` and
      `same()`. `setEASYQAMode()` marks those tests and has no effect found.
- [x] `setDate(day, month, year)` and `setTime(h, m, s)` fix what `DATE()`
      and `TIME()` return; the `startsWith` matcher; `assertGreaterThan`.
- [x] A stub may name the routine that implements a component method:
      `addStub("OPF")` answers the target's `EB.DataAccess.Opf(...)`, through
      the catalog's method table.
- [ ] `addStubCacheChange` (50 tests), `setFilePointer` (25),
      `lockRecord`, and `addStubCommonChange` given a name in quotes.
- [x] `JBCC_UTF_TRACE=1` prints each stubbed call, its arguments and
      whether a stub answered it, and for the other stubs of the name why
      not: the parameter and value each expects, used up, or a condition.

### 6. Records and T24 data access

- [x] `setRecord(file, key, record)` and `getRecord(file, key)`. A file
      is named without its company prefix: `F.ACCOUNT` and `FBNK.ACCOUNT`
      are `ACCOUNT`.
- [x] A data-access call that no stub answers reads and writes those
      records: `F.READ`, `F.READU`, `CACHE.READ`, `F.WRITE`, `F.DELETE`,
      `OPF`, their `EB.DataAccess` forms, and a component table's
      operations, as `AC.AccountOpening.Account.Read(id, error)`, through
      the table's `t24:` file. A missing record sets the error variable to
      `RECORD NOT FOUND` (inferred).
- [ ] `READ` statements on files the target opens itself, and
      `EB.DataAccess.Das` selections.
- [ ] Load the `.d` system records a target needs, such as `F.EB.ERROR`,
      on demand.

#### Steps 4 to 6 baseline (2026-11-28)

All 26,307 tests in 54 min with 8 workers and a 5 s limit:

| State | Tests | Main causes |
|---|---:|---|
| passed | 14,865 | 56.5% of all tests |
| failed | 4,887 | 2,850 at an assertion; 1,876 at a call no stub matches, as `EB.ErrorProcessing.StoreEndError()` (108) and `EB.DataAccess.Das` (71) |
| timeout | 2,740 | mostly loops whose exit depends on what an unstubbed call returns; one sampled target appends to the list it REMOVEs from, which loops in TAFC too |
| unsupported | 1,745 | `setEASYQAMode` (757), `addStubPropertyCondition` (332), `addStubWriteDone` (235) |
| error | 1,565 | `expected a positive integer dimension` (214, inserts using C$SYSDIM without I_COMMON), FOR with text bounds (102), the `Logger` C function (101), WRITE without a file |
| rejected, target missing, no target, unlinked, crashed | 505 | the step 1 source errors; 10 SIGSEGV |

On the way, the runs found TAFC behaviour that jbcc now follows
(TAFC-CROSSCHECK.md, section 3): indices that are not positive integers
(`tests/tafc/array-index-conversion.b`) and `ABS` of text
(`tests/tafc/abs-non-numeric.b`).

#### Step 5 completion baseline (2026-11-28)

With the stub methods above, MATBUILD's trailing elements and stubs by
routine name, all 26,307 tests in 53 min:

| State | Tests | Main causes |
|---|---:|---|
| passed | 16,510 | 62.8% of all tests |
| failed | 4,844 | 3,107 at an assertion; 1,548 at a call no stub matches, as `ST.CompanyCreation.EbReadParameter` (67) and `EB.DataAccess.Das` (41) |
| timeout | 2,724 | as before |
| error | 1,584 | as before: C$SYSDIM without I_COMMON (214), `Logger` (101), FOR with text bounds (100) |
| unsupported | 137 | `addStubCacheChange` (50), `addStubCommonChange` with a quoted name (46), `setFilePointer` (25) |
| rejected and the rest | 508 | |

#### Stub choice baseline (2026-11-28)

With the most specific stub answering and `reset` clearing the stubs,
all 26,307 tests in 53 min:

| State | Tests | Change from the step 5 baseline |
|---|---:|---|
| passed | 17,696 | 67.3%; 1,197 more pass, 21 fewer |
| failed | 3,633 | 1,845 at `assertEquals` |
| timeout | 2,731 | |
| error | 1,604 | |
| unsupported | 137 | |
| rejected and the rest | 506 | |

### 7. The rest

- [x] The component-method targets, through the catalog's method table
      or the test's name (step 2).
- [x] Tests that run more than once (`reset`, `setRepeatable`).
- [ ] The remaining unsupported UTF methods (step 5).
- [ ] Sort the assertion failures into jbcc bugs, UTF assumptions and
      TAFJ behaviour, with `JBCC_UTF_TRACE` and TAFC probes. Found so far:
  - a jbcc bug: MATBUILD kept trailing empty elements, which TAFC leaves
    out (`tests/tafc/matbuild-trailing.b`); records built from `R.NEW`
    then compared unequal;
  - TAFJ arithmetic: `FRA.VALUATION_0` expects `-5792.70`, where TAFC
    PB201214 and jbcc give `-5792.69` from the same inputs at PRECISION 4.
    Tests written against TAFJ's Java decimals can fail under TAFC's
    rules; jbcc keeps TAFC's.
- [ ] Track the pass rate over all 26,307 tests in this file, in the
      same way R19-CORPUS.md tracks translation.

## Open questions

- The exact meaning of `setRepeatable`, `reset`, `setParam` and
  `ignoreMissingStubs`. These are inferred above; settle each one by which
  reading makes more of its tests pass.
- Stub matching is inferred too (step 5): by position, the most specific
  match wins and then the newest, used up unless repeatable.
- Whether UTF runs each test in a fresh session, with COMMON, the cache and
  files reset, or shares one session across a test's runs.
- The T24 environment a target expects: COMMON variables such as `TODAY`,
  `ID.COMPANY` and `R.USER`, and the company and user records.
  `setEASYQAMode` and the property and COMMON stub changes suggest that
  UTF sets some of these up.
