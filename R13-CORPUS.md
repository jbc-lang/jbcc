# R13 corpus plan

Goal: jbcc translates every source unit in every local T24 corpus
(`../t24-extract`: R07, R10, R13 and R19) to C that passes strict C99
checking, with documented commands and recorded baselines. Reference
compiler evidence comes from `../jbc-extract`.

## Trial scan (2026-11-26, before any change)

`201307-R13` has two flat folders, `T24.BP/` and `SENSITIVE.BP/`, and no
C headers; 45 units include `JBC.h`. The PB201214 headers in
`../jbc-extract/TAFC_PB201214_LINUX_ELF_AS6_106034.tar.gz`
(`PB201214/include`) match the former `~/Downloads/PB201214-linux/include`
byte for byte. `../jbc-extract/JBC.h` is an older revision.

19,524 of 19,537 source units translated and passed C syntax checking;
5,837 files are include fragments. Wall time 2 min 33 s with 8 workers.

| Kind | Units | Cause |
|---|---|---|
| Missing statement | `CLEAR.TOKENS`, `DW.EXPORT.CONF.EXPORT`, `DW.EXPORT.CONFIGURE` | `DELETESEQ` |
| Missing function | `IN2SEC` | `ISALNUM(...)` |
| Missing function form | `SEAT.SCRIPT.ACTIVITY.TRANSFER` | `IF CHDIR(path) THEN` |
| Parser gap | `RAISE.PENDING.ENTRIES` | `UNASSIGNED(X<I,J>)` |
| Needs reference check | `AM.RECOMMEND.ALERT(.LOAD)`, `DE.O.CC.TEMPLATE(.LOAD)` | name declared in `COMMON`, then `DIM` in the routine |
| Source problem | `DM.GENERATE.ERWIN` | `VALIDATE_PRODUCT_LICENSE` with its `jThreadB.h` include commented out |
| Known fix not applied | `STEST.AZ.PD.DATES.CHK` | `<.AZ.SLS.TYPE.I` fix limited to R10 root and R07 `GLOBUS.BP/` |
| Out of scope | `V.PL.B2LIM.NET` | Raiffeisen Bank Polska local routine; its include is absent |

## Steps

- [x] 1. Take reference headers from `../jbc-extract` instead of
  `~/Downloads`: unpack `PB201214/include` from the tarball to a cache
  and update README.md and SOURCES.md (`~/Downloads/jbc/` becomes
  `../jbc-extract/jbccom`).
- [x] 2. Apply the T24 source fixes per release directory, including R13
  `T24.BP/`, starting with `STEST.AZ.PD.DATES.CHK`. Add a
  `tests/corpus/r13/` fixture and test like the R07 one.
- [x] 3. Record the baseline: an "R13 corpus" README section with the
  command, an R13 row in the performance table, an "R13 baseline"
  section in PLAN.md and the R13 API coverage report.
- [ ] 4. Close the language gaps with small independent snippets that
  name the corpus file that showed each construct:
  - [x] `DELETESEQ` statement with ELSE (`DW.EXPORT.CONF.EXPORT` then
    stops at `READXML`)
  - [x] `READXML` statement (parsed; reports a missing XML backend when
    reached)
  - [x] `ISALNUM`
  - [ ] The other reference-lexer class tests: `ISCNTRL`, `ISGRAPH`,
    `ISLOWER`, `ISPRINT`, `ISPUNCT`, `ISSPACE`, `ISUPPER`, `ISXDIGIT`.
    Not used by the corpora. Decide byte classes first: the guide's
    ISCNTRL example returns 1 for `@FM:CHAR(13):CHAR(10)`.
  - [ ] `CHDIR` as a condition
  - [ ] `UNASSIGNED` with a dynamic-array argument
- [ ] 5. Settle `COMMON X` followed by `DIM X(n)` and `DM.GENERATE.ERWIN`
  with the reference compiler (`../jbc-extract/tools/build-jbccom.sh`,
  or `bin/JBCCOM` from the tarball in the Linux container). Implement,
  fix in memory or record as expected failures.
- [x] 6. Exclude `V.PL.B2LIM.NET` as non-Temenos code and report it as
  excluded rather than rejected (`--t24-exclude-local-routines`).
- [ ] 7. Re-run R10 and R07 to check for regressions and update counts.
- [ ] 8. Extend from the R19 pilot to the full R19 corpus.
