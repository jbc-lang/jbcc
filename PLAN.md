# Compiler plan

The first T24-style milestone is to compile and run a subroutine that reads a
field from a dynamic array, makes a decision, and returns a result through
an argument.

## Standalone programs

- [x] **Comparisons and truth values.** Implement `EQ`, `NE`, `LT`, `LE`,
  `GT`, and `GE`. Add snippets for zero, empty strings, and numeric strings.
- [x] **IF / THEN / ELSE / END.** Support single-line, multiline, and nested
  forms. Test that only the selected branch executes.
- [ ] **PRINT and fuller CRT.** Support comma-separated expressions, blank
  lines, and a trailing colon to suppress the newline. Compare stdout byte
  for byte.
- [ ] **Arithmetic and assignment.** Implement subtraction, unary minus,
  multiplication, `+=`, and `-=`.
- [ ] **Division.** Extend the integer runtime to represent fractional results.
  Use `CRT 7 / 2` with expected output `3.5` as the first snippet.
- [ ] **FOR / TO / STEP / NEXT.** Cover ascending, descending, zero-iteration,
  and nested loops. Verify when the limit and step expressions are evaluated.
- [ ] **LOOP / WHILE / UNTIL / REPEAT.** Test conditions before and after
  statements in the body. Include the form observed in the corpus where
  `UNTIL` shares a line with the preceding statement.

## T24-style routines

- [ ] **Dynamic arrays.** Read and write `REC<field>`, then
  `REC<field,value>` and `REC<field,value,subvalue>`. Build the first test
  record in memory.
- [ ] **Labels and GOSUB / RETURN.** Implement local subroutines and test
  nested returns.
- [ ] **SUBROUTINE and CALL.** Compile a caller and a separately declared
  callee together. Have the callee update an argument and the caller print
  the changed value.
- [ ] **EQUATE and $INSERT.** Resolve local include files. Preserve original
  filenames and line numbers in diagnostics.
- [ ] **BEGIN CASE / CASE / END CASE.** Verify that the first matching case
  wins.

## Libraries and external services

- [ ] **String and multivalue functions.** Start with `LEN`, `FIELD`, `COUNT`,
  and `DCOUNT`. Choose subsequent functions by frequency in the corpus.
- [ ] **File I/O.** Use an in-memory test backend for `OPEN`, `READ`, and
  `WRITE`. Exercise `THEN` and `ELSE` paths with reproducible missing records
  and failed opens.
- [ ] **Whole-routine corpus checks.** Track which routines translate and
  group failures by unsupported construct. Check runtime behavior separately
  with executable snippets whose expected results have a recorded source.
