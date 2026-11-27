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

- [ ] **UTF state:** the target, its parameters (as references), the stubs
      with their expected and returned arguments, the seeded records, and
      the assertion results.
- [ ] **`runTest`:** call the target, a SUBROUTINE or FUNCTION built from
      the corpus, with the parameters. Then mark the test passed if every
      assertion holds, and failed with the first failing assertion
      otherwise.
- [ ] **A runner** (`tools/run_tuts.py` and a `just tut` recipe):
  - build each test with its target;
  - run it with a time limit;
  - write a JSON report with these states per test: translated, built,
    ran, passed, failed (with the assertion), crashed.

### 3. A first set: no stubs, no records

- [ ] Choose a fixed set from the 1,253 tests with no stubs, no records, a
      literal SUBROUTINE or FUNCTION target and a single `runTest`.
      Prefer short tests whose targets read no clock, files or COMMON.
      Record the list as corpus paths in the report, not as copies.
- [ ] Make them pass. Each failure is a jbcc bug, a UTF assumption or a
      missing service; fix it or record it in a "known" list with the
      reason.
- [ ] Record the baseline in this file: passed, failed and why.

### 4. Linking targets

A target calls other routines: T24 library routines, component methods
and its own helpers. The R19 scan checks each unit on its own, with
prototypes for what it calls (R19-CORPUS.md); running needs real code.

- [ ] Resolve each CALL in a test build to one of:
  - a stub;
  - the real routine, built from the corpus on demand, with its own
    callees in turn;
  - a missing-routine failure, unless `ignoreMissingStubs` is set.
- [ ] Settle how `ignoreMissingStubs` behaves: does it run the real
      routine, or skip the call? Compare which hypothesis lets more of the
      tests that use it pass.

### 5. Stubs

- [ ] `addStub` and `addStubParam` with `any`, `same` and `matches`,
      `setRepeatable` and `getNbInvocation`. A call whose arguments match
      no stub fails the test (inferred). Measure how many stubbed tests
      pass.
- [ ] The property, COMMON and cache side effects, and
      `setStubReturnValue`, for FUNCTION stubs.

### 6. Records and T24 data access

- [ ] `setRecord` and `getRecord` over jbcc's in-memory files, created on
      demand for each file the test names.
- [ ] The T24 data-access routines a target reads records with (`F.READ`,
      `CACHE.READ`, their R19 component forms and so on), over the same
      files: stubbed, or built from the corpus where that works.
- [ ] Load the `.d` system records a target needs, such as `F.EB.ERROR`,
      into in-memory files at startup, on demand.

### 7. Component-method targets and the rest

- [ ] The 2,821 component-method targets, with the R19 component call
      mapping (`--t24-component-calls`).
- [ ] Tests that run more than once (`reset`, `setRepeatable`).
- [ ] Track the pass rate over all 26,307 tests in this file, in the
      same way R19-CORPUS.md tracks translation.

## Open questions

- The exact meaning of `setRepeatable`, `reset`, `setParam` and
  `ignoreMissingStubs`. These are inferred above; settle each one by which
  reading makes more of its tests pass.
- How a stub's arguments are matched: by position, how many arguments, and
  in which order, when the same routine is stubbed more than once.
- Whether UTF runs each test in a fresh session, with COMMON, the cache and
  files reset, or shares one session across a test's runs.
- The T24 environment a target expects: COMMON variables such as `TODAY`,
  `ID.COMPANY` and `R.USER`, and the company and user records.
  `setEASYQAMode` and the property and COMMON stub changes suggest that
  UTF sets some of these up.
