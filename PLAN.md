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

- [x] Implement the logical OR operator. Of 3,335 first diagnostics reporting
  an expected THEN or ELSE, 1,911 point at OR. Verify precedence, truth
  conversion and operand evaluation with executable snippets, then rescan.

After logical operator support, 3,596 of 17,336 candidate units passed C99
checking, including all 3,427 previous passes. The scan reported 13,512
compiler diagnostics and 228 encoding errors.

- [x] Implement whole-matrix assignment. MAT is the first blocker in 1,551
  units. Of those, 1,488 use scalar fill and 63 use matrix copy. Verify both
  forms against the guide and test local and COMMON matrices before rescanning.

After MAT fill and copy, 4,309 of 17,336 candidate units passed C99 checking,
including all 3,596 previous passes. The scan reported 12,799 compiler
diagnostics and 228 encoding errors.

- [x] Implement LOCATE, the first unsupported statement in 1,329 units.
  Check the corpus syntax against the guide. Test the returned position and
  THEN/ELSE branches for successful and unsuccessful searches.

After LOCATE and NULL, 4,639 of 17,336 candidate units passed C99 checking,
including all 4,309 previous passes. The scan reported 12,469 compiler
diagnostics and 228 encoding errors. All 1,329 original LOCATE first blockers
used the IN form.

- [x] Implement REMOVE, the first unsupported statement in 966 units. Test
  successive extractions, delimiter codes, end of input and cursor state
  after reassignment against the guide.

After REMOVE, 4,876 of 17,336 candidate units passed C99 checking,
including all 4,639 previous passes. The scan reported 12,232 compiler
diagnostics and 228 encoding errors.

- [x] Implement UNASSIGNED and ASSIGNED. In 892 units the first parser
  diagnostic points to the opening parenthesis of UNASSIGNED. Test an
  untouched variable, an assigned empty string and a matrix element through
  the native compiler.

After ASSIGNED and UNASSIGNED, 4,894 candidate units passed strict C99
checking. All 4,876 previous passes remained. In 854 units the first
diagnostic now points to the same concatenating assignment in I_DAS.

- [x] Implement concatenating assignment (`:=`) for scalars and indexed
  targets and verify against the string examples in the guide.

After concatenating assignment, 5,946 of 17,336 candidate units passed C99
checking, including all 4,894 previous passes. The scan reported 11,162
compiler diagnostics and 228 encoding errors.

- [x] Support labels inside structured statements. The routine-scope label
  restriction is the first blocker in 1,532 units. Test the observed label
  immediately before REPEAT and labels inside IF arms. Check jump targets
  and loop temporary lifetimes before enabling jumps across block boundaries.

After nested label support, 6,146 of 17,336 candidate units passed C99
checking, including all 5,946 previous passes. The scan reported 10,962
compiler diagnostics and 228 encoding errors.

- [x] Implement INDEX. In 1,281 units the first diagnostic points to its
  opening parenthesis. Verify occurrence counting, returned byte positions
  and the missing-substring result in executable tests.

After INDEX, 6,657 of 17,336 candidate units passed C99 checking,
including all 6,146 previous passes. The scan reported 10,451 compiler
diagnostics and 228 encoding errors.

- [x] Support runtime-sized COMMON matrices as used in T24. The first
  diagnostic in 728 units points to the same record-derived dimension in
  I_SEAT.COMMON. Verify when bounds are evaluated, how offsets for later
  members are computed, and how a second routine shares the block.

After runtime-sized COMMON matrices, 6,984 of 17,336 candidate units passed
C99 checking, including all 6,657 previous passes. Of the 728 units previously
stopped at the declaration in I_SEAT.COMMON, 304 passed and 424 reached
another diagnostic. The scan reported 10,124 compiler diagnostics and 228
encoding errors.

- [x] Implement the CONVERT statement, the first blocker in 590 units.
  Check character substitution and deletion against the guide and test
  byte-oriented conversions on dynamic arrays.

After CONVERT statement and function support, 7,214 of 17,336 candidate
units passed strict C99 checking, including all 6,984 previous passes.
Of the 590 previously stopped at the statement, 223 passed and 367 reached
another diagnostic. The scan reported 9,894 compiler diagnostics and 228
encoding errors.

- [x] Investigate the duplicate declaration of `AA$RULE.TYPE`, the first
  diagnostic in 488 units. Trace the include chain and compare the
  declarations before changing COMMON handling.

I_AA.APP.COMMON declares the same scalar twice within /AAAAP/, at lines
4 and 41. The reference parser and symbol table keep the original slot.
With that rule, 7,406 of 17,336 candidates pass strict C99 checking,
including all 7,214 previous passes. Of the 488 units stopped at this
declaration, 125 now pass and 363 reach another diagnostic.

- [x] Implement CONTINUE, the first blocker in 384 units. Verify its
  destination inside nested LOOP and FOR statements, including the FOR
  counter increment and cleanup of iteration temporaries.

After CONTINUE, 7,475 of 17,336 candidates pass strict C99 checking,
including all 7,406 previous passes. Of the 384 units previously stopped
at CONTINUE, 69 pass and 315 reach another diagnostic.

- [ ] Implement RAISE and LOWER for dynamic-array delimiters. The first
  diagnostic points to the opening parenthesis of RAISE in 273 units and
  LOWER in 137. Verify each delimiter level and the boundary cases against
  the guide with native output tests.
