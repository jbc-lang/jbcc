# Compiler plan

The coverage goal is to compile every T24 program, subroutine and function in
the local corpus to C99 that passes the system compiler's syntax checks.
Count include fragments through the compilation units that use them. Track
unreferenced fragments and undecodable files explicitly when assessing full
coverage. Verify runtime behavior separately with executable tests.

The first T24-style milestone is to compile and run a subroutine that reads a
field from a dynamic array, makes a decision, and returns a result through
an argument.

## Standalone programs

- [x] **Comparisons and truth values.** Implement `EQ`, `NE`, `LT`, `LE`,
  `GT`, and `GE`. Add snippets for zero, empty strings, and numeric strings.
- [x] **IF / THEN / ELSE / END.** Support single-line, multiline, and nested
  forms. Test that only the selected branch executes.
- [x] **PRINT and fuller CRT.** Support comma-separated expressions, blank
  lines, and a trailing colon to suppress the newline. Compare stdout byte
  for byte.
- [x] **Arithmetic and assignment.** Implement subtraction, unary minus,
  multiplication, `+=`, and `-=`.
- [x] **Division.** Extend the integer runtime to represent fractional results.
  Use `CRT 7 / 2` with expected output `3.5` as the first snippet.
- [x] **FOR / TO / STEP / NEXT.** Cover ascending, descending, zero-iteration,
  and nested loops. Verify when the limit and step expressions are evaluated.
- [x] **LOOP / WHILE / UNTIL / REPEAT.** Test conditions before and after
  statements in the body. Include the form observed in the corpus where
  `UNTIL` shares a line with the preceding statement.

## T24-style routines

- [x] **Dynamic arrays.** Read and write `REC<field>`, then
  `REC<field,value>` and `REC<field,value,subvalue>`. Build the first test
  record in memory.
- [x] **Labels and GOSUB / RETURN.** Implement local subroutines and test
  nested returns.
- [x] **SUBROUTINE and CALL.** Compile a caller and a separately declared
  callee together. Have the callee update an argument and the caller print
  the changed value.
- [x] **EQUATE and $INSERT.** Resolve local include files. Preserve original
  filenames and line numbers in diagnostics.
- [x] **BEGIN CASE / CASE / END CASE.** Verify that the first matching case
  wins.

## Libraries and external services

- [x] **String and multivalue functions.** Start with `LEN`, `FIELD`, `COUNT`,
  and `DCOUNT`. Choose subsequent functions by frequency in the corpus.
- [x] **File I/O.** Use an in-memory test backend for `OPEN`, `READ`, and
  `WRITE`. Exercise `THEN` and `ELSE` paths with reproducible missing records
  and failed opens.
- [x] **Whole-routine corpus checks.** Track which routines translate and
  group failures by unsupported construct. Check runtime behavior separately
  with executable snippets whose expected results have a recorded source.

## Corpus baseline

The 2026-11-22 scan covered 22,474 local T24 files. Of 17,336 candidate
units, 53 translated and passed C99 syntax checking, 17,055 produced
compiler diagnostics, and 228 encountered UTF-8 decoding errors. The other
5,138 files were classified as include fragments by name.

The first unsupported statement was COM in 16,482 units and COMMON in 18.
Shared COMMON storage and dimensioned declarations are now implemented.

## Whole-program fixture milestones

- [x] Compile and run the quine with byte-oriented CHAR and verify that its
  output reproduces its complete source byte for byte.
- [x] Implement DIM storage and indexed reads/writes alongside COMMON.
  Start with local arrays, including the banner's zero index, then reuse
  the same representation for dimensioned members of shared COMMON blocks.
- [x] Bring up the banner's frame calculation with SPACE, INT, SIN, COS, AND,
  and substring reads and writes on indexed strings. Verify trigonometric
  conventions against the guide.
- [x] Run the unchanged banner with GOTO, cursor control and SYSTEM(14).
  Use deterministic terminal input so the native test can check frame output
  and exit.

## Next coverage milestone

After the COMMON and banner changes, 66 of 17,336 candidate units passed
C99 syntax checking, 17,042 produced compiler diagnostics and 228 encountered
encoding errors. The same 5,138 include fragments were classified separately.

- [x] Compile scalar DEFFUN declarations and FUNCTION calls. The native
  two-source fixture prints 43. Missing definitions and arity mismatches
  report the call site.

After DEFFUN support, 68 of 17,336 candidate units passed C99 checking,
17,040 produced compiler diagnostics, and 228 had encoding errors.
PRECISION is the first blocker in 16,500 units, including uses in I_COMMON.

- [x] Implement PRECISION for arithmetic, comparisons and truth tests.
  Native tests cover conditional and repeated settings, GOSUB, and restoring
  the caller's setting after a subroutine or function returns.

After PRECISION and the recursive-call corpus checker fix, 3,427 of 17,336
candidate units passed strict C99 syntax checking, 13,681 produced compiler
diagnostics, and 228 had encoding errors. The checker classified 5,138 files
as include fragments.

- [ ] Implement the logical OR operator. Of 3,335 first diagnostics reporting
  an expected THEN or ELSE, 1,911 point at OR. Verify precedence, truth
  conversion and operand evaluation with executable snippets, then rescan.
