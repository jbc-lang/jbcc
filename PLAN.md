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

- [x] Implement RAISE and LOWER for dynamic-array delimiters. The first
  diagnostic points to the opening parenthesis of RAISE in 273 units and
  LOWER in 137. Verify each delimiter level and the boundary cases against
  the guide with native output tests.

After RAISE and LOWER, 7,666 of 17,336 candidates pass strict C99 checking,
including all 7,475 previous passes. Of the 410 units whose first diagnostic
pointed to the opening parenthesis of either function, 155 now pass and 255
reach another diagnostic.

- [x] Recognize a comment immediately after a label. In 723 units the
  first diagnostic points to an asterisk following a colon, commonly in
  `DEFINE.PARAMETERS:* ...`. Test named and numeric labels and preserve
  multiplication and concatenation in expressions.

After label comments, 8,334 of 17,336 candidates pass strict C99 checking,
including all 7,666 previous passes. Of the 723 units stopped at the
asterisk after a label, 668 now pass and 55 reach another diagnostic.

- [x] Implement three-argument bracket extraction, as in
  `Text["-",1,1]`. In 467 units the first diagnostic expects a closing
  bracket at a comma. Check the reference parser's
  `spec_substring_extract_gen` and verify field selection in native tests.

The reference generator emits FIELD for three-argument bracket reads.
After bracket extraction, 8,499 of 17,336 candidates pass strict C99
checking, including all 8,334 previous passes. Of the 467 units stopped
at the extra comma, 165 now pass and 302 reach another diagnostic.

- [x] Implement the MATCH and MATCHES comparison operators. Start with
  the pattern forms observed in the corpus and check their meanings against
  the guide. In 550 units the first diagnostic points to one of these
  operators where the parser expects a conditional arm or a closing
  parenthesis, or reports an unexpected token.

After MATCH and MATCHES, 8,873 of 17,336 candidates pass strict C99
checking, including all 8,499 previous passes. Of the 550 units tracked
above, 213 now pass and 337 reach another diagnostic.

- [x] Implement the system constants `@TRUE` and `@FALSE`. The first
  diagnostic points to `@FALSE` in 250 units and `@TRUE` in 122. Check
  their values against the reference and test them in assignments,
  arithmetic and IF conditions.

After the Boolean constants, 9,020 of 17,336 candidates pass strict C99
checking, including all 8,873 previous passes. Of the 372 units stopped
at either constant, 147 now pass and 225 reach another diagnostic.

- [x] Implement DEL for dynamic-array fields, values and subvalues. It is
  the first blocker in 269 units. Check deletion at the start, middle and
  end of a component list, missing positions and matrix-element targets
  against the DEL chapter.

After DEL, 9,151 of 17,336 candidates pass strict C99 checking, including
all 9,020 previous passes. Of the 269 units stopped at DEL, 131 now pass
and 138 reach another diagnostic.

- [x] Implement `INS expression BEFORE target<...>`, the first blocker
  in 230 units. Test insertion before existing fields, values and subvalues,
  padding beyond the last element and the guide's negative-index append rule.

After INS, 9,276 of 17,336 candidates pass strict C99 checking, including
all 9,151 previous passes. Of the 230 units stopped at INS, 125 now pass
and 105 reach another diagnostic.

- [x] Implement MATBUILD, the first blocker in 210 units. Check how the
  guide maps matrix elements to a dynamic array, including the default
  delimiter, explicit delimiters and optional element ranges.

After MATBUILD, 9,348 of 17,336 candidates pass strict C99 checking,
including all 9,276 previous passes. Of the 210 units stopped at MATBUILD,
72 now pass and 138 reach another diagnostic.

- [x] Implement MATPARSE, the first blocker in 174 units. Use the guide’s
  examples to check element order, ranges, delimiters, SETTING and overflow
  into element zero. Verify a MATPARSE/MATBUILD round trip in native tests.

After MATPARSE, 9,410 of 17,336 candidates pass strict C99 checking,
including all 9,348 previous passes. Of the 174 units stopped at MATPARSE,
62 now pass and 112 reach another diagnostic.

- [x] Support MAT routine parameters, the first blocker in 247 units.
  Trace the reference grammar for formal and actual arguments. Verify
  that a callee sees the caller's bounds and can update its matrix, and
  diagnose mismatched scalar and matrix arguments.

After whole-matrix arguments, 9,571 of 17,336 candidates pass strict C99
checking, including all 9,410 previous passes. Of the 247 units stopped
at a MAT formal parameter, 60 now pass and 187 reach another diagnostic.
Accepting MAT at call sites also lets 101 other units pass.

- [x] Investigate the three-position LOCATE selector, the first blocker
  in 227 units. Check how the reference handles the starting subvalue in
  `LOCATE X IN R<F,V,S>` and verify the SETTING position for matches and
  misses, including starting positions greater than one.

After three-position LOCATE, 9,693 of 17,336 candidates pass strict C99
checking, including all 9,571 previous passes. Of the 227 units previously
stopped at the selector, 122 pass and 105 reach another diagnostic.

- [x] Implement EXIT, the first blocker in 189 units. Distinguish a bare
  EXIT inside a loop from EXIT(expression), which returns a process status.
  Test nested loops, CASE inside a loop, and the native executable's status.

After EXIT, 9,804 of 17,336 candidates pass strict C99 checking, including
all 9,693 previous passes. Of the 189 units stopped at a bare EXIT, 111
pass and 78 reach another diagnostic.

- [x] Start FMT with the mask forms observed in T24. In 277 units the
  first diagnostic points to the opening parenthesis of FMT. Cross-check
  width, justification, padding and decimal precision against the guide,
  and report unsupported masks at the call site.

After adding the common FMT masks, 9,926 of 17,336 candidates pass strict
C99 checking, including all 9,804 previous passes. Of the 277 units
previously stopped at FMT, 105 now pass and 172 reach another diagnostic.
Other mask forms still need runtime support.

- [x] Implement ABS, the first blocker in 172 units. Cover negative decimal
  values, zero, and numeric strings in native execution tests.

After ABS, 10,062 of 17,336 candidates pass strict C99 checking, including
all 9,926 previous passes. Of the 172 units previously stopped at the
opening parenthesis of ABS, 104 now pass and 68 reach another diagnostic.

- [x] Implement SUM, the first blocker in 168 units. Test the guide’s
  dynamic-array examples for fields, values and subvalues, including
  how SUM preserves higher-level marks and ignores nonnumeric elements.

After SUM, 10,194 of 17,336 candidates pass strict C99 checking, including
all 10,062 previous passes. Of the 168 units previously stopped at the
opening parenthesis of SUM, 95 now pass and 73 reach another diagnostic.

- [x] Implement TRIM, the first blocker in 114 units. Check the default
  behavior and the guide’s eight trim modes with spaces, tabs and a
  caller-supplied trim character.

After TRIM, 10,256 of 17,336 candidates pass strict C99 checking, including
all 10,194 previous passes. Of the 114 units previously stopped at the
opening parenthesis of TRIM, 43 now pass and 71 reach another diagnostic.

- [x] Start OCONV, the first blocker in 258 units. Begin with date masks
  observed in T24, including `D-`. Verify the internal date epoch, leap
  years and output layout against the guide, and diagnose unsupported
  conversions at the call site.

After adding OCONV date masks, 10,267 of 17,336 candidates pass strict
C99 checking, including all 10,256 previous passes. Of the 258 units
previously stopped at the opening parenthesis of OCONV, 5 now pass and
253 reach another diagnostic. The scan checks generated C syntax only.
Mask support is checked separately in native tests.

- [x] Implement DATE() so T24 expressions such as `OCONV(DATE(),'D-')`
  can run. Check the local calendar date against the same 1967 epoch,
  including dates across a timezone boundary.

After DATE(), 10,325 of 17,336 candidates pass strict C99 checking,
including all 10,267 previous passes. Of the 50 units previously reporting
an unknown DATE or stopping at its opening parenthesis, 19 now pass and
31 reach another diagnostic.

- [x] Implement TIME() and the common OCONV time masks `MT` and `MTS`.
  Check seconds since local midnight and the guide’s formatted examples,
  including midnight and the last second of the day.

After TIME(), 10,384 of 17,336 candidates pass strict C99 checking,
including all 10,325 previous passes. Of the 44 units previously reporting
an unknown TIME or stopping at its opening parenthesis, 20 now pass and
24 reach another diagnostic.

- [x] Implement TIMEDATE(), the first blocker in 120 units. Format a
  single local clock reading as `hh:mm:ss dd mmm yyyy` and verify that
  the date and time agree at midnight.

After TIMEDATE(), 10,451 of 17,336 candidates pass strict C99 checking,
including all 10,384 previous passes. Of the 120 units previously stopped
at TIMEDATE, 66 now pass and 54 reach another diagnostic.

- [x] Implement CHANGE as a statement and a function. Together the two
  forms are the first blocker in 161 units. Check replacement order,
  unequal string lengths and empty replacements in native tests.

After CHANGE, 10,553 of 17,336 candidates pass strict C99 checking,
including all 10,451 previous passes. Of the 161 units previously stopped
at CHANGE, 101 now pass and 60 reach another diagnostic.

- [x] Implement FIND, the first blocker in 128 units. Test exact matches,
  occurrence selection, field/value/subvalue positions, and THEN/ELSE
  behavior against the guide’s dynamic-array examples.

After FIND, 10,639 of 17,336 candidates pass strict C99 checking,
including all 10,553 previous passes. Of the 128 units previously stopped
at FIND, 86 now pass and 42 reach another diagnostic.

- [x] Implement FINDSTR, the first blocker in 133 units. Verify substring
  matches within an element, occurrence selection and SETTING positions
  against the guide.

After FINDSTR, 10,745 of 17,336 candidates pass strict C99 checking,
including all 10,639 previous passes. Of the 133 units previously stopped
at FINDSTR, 106 now pass and 27 reach another diagnostic.

- [x] Implement record DELETE for the in-memory file runtime, the first
  blocker in 137 units. Verify deletion through READ, repeated deletion
  of a missing key, and the SETTING and ON ERROR clauses.

After DELETE, 10,844 of 17,336 candidates pass strict C99 checking,
including all 10,745 previous passes. Of the 137 units previously stopped
at DELETE, 99 now pass and 38 reach another diagnostic.

- [x] Implement CLEARFILE in the in-memory backend, the first blocker in
  116 units. Test explicit and default descriptors, SETTING and ON ERROR,
  and verify that clearing one file preserves records in a second file.

After CLEARFILE, 10,901 of 17,336 candidates pass strict C99 checking,
including all 10,844 previous passes. Of the 116 units previously stopped
at CLEARFILE, 57 now pass and 59 reach another diagnostic.

- [x] Implement READV for the in-memory backend, the first blocker in
  108 units. Check field extraction, default and explicit descriptors,
  and the behavior of missing records and out-of-range fields.

After READV, 10,980 of 17,336 candidates pass strict C99 checking,
including all 10,901 previous passes. Of the 108 units previously stopped
at READV, 79 now pass and 29 reach another diagnostic.

- [x] Implement MATREAD in the in-memory backend, the first blocker in
  71 units. Verify field mapping into a dimensioned array and preservation
  of the destination on a missing record.

After MATREAD, 11,002 of 17,336 candidates pass strict C99 checking,
including all 10,980 previous passes. Of the 71 units previously stopped
at MATREAD, 22 now pass and 49 reach another diagnostic.

- [x] Implement MATWRITE for the in-memory backend, the first blocker
  in 46 units. Verify matrix element order, SETTING, and a round trip
  through MATWRITE and MATREAD using explicit and default descriptors.

After MATWRITE, 11,015 of 17,336 candidates pass strict C99 checking,
including all 11,002 previous passes. Of the 46 units previously stopped
at MATWRITE, 13 now pass and 33 reach another diagnostic.

- [x] Implement file SELECT and READNEXT for the in-memory backend,
  currently the first blockers in 124 and 10 units respectively.
  Verify iteration over record keys, empty files and list exhaustion.

After file SELECT and READNEXT, 11,072 of 17,336 candidates pass strict
C99 checking, including all 11,015 previous passes. Of the 124 units first
blocked at SELECT, 47 now pass. Of the 10 first blocked at a READNEXT
statement, two now pass. Supporting READNEXT expressions also helped
units whose first diagnostic was elsewhere.

- [x] Implement CLEARSELECT, the first blocker in 28 units. Verify that
  clearing the default, a named or a numbered list leaves other cursors
  and the underlying records intact.

After CLEARSELECT, 11,084 of 17,336 candidates pass strict C99 checking,
including all 11,072 previous passes. Of the 28 units first blocked at
CLEARSELECT, 12 now pass and 16 reach another diagnostic.

- [x] Extend SELECT to dynamic arrays. Run the CLEARSELECT guide example
  with two field-mark-separated inputs and verify that READNEXT preserves
  field order and that the lists can be cleared independently.

The guide’s two-list example now runs as written. All 11,084 previous
strict C99 passes remain among the 17,336 T24 candidates. Array selection
adds runtime behavior to SELECT syntax the compiler already accepted.

- [x] Implement PROGRAM, the first blocker in 64 units. Check the guide’s
  documentation-only header, the names used in T24, and native execution
  of the statements following the header.

After PROGRAM, 11,087 of 17,336 candidates pass strict C99 checking,
including all 11,084 previous passes. Three of the 64 PROGRAM units now
pass and the other 61 reach another diagnostic.

- [x] Support runtime bounds in local DIM declarations. Cover one- and
  two-dimensional arrays, evaluate expressions when the declaration runs,
  and use the saved bounds for element access and MAT arguments.

After local DIM, 11,111 of 17,336 candidates pass strict C99 checking,
including all 11,087 previous passes. Of the 135 units previously blocked
by the constant-bound requirement, 24 now pass and 111 reach another
diagnostic.

- [x] Implement NUM(expression). In 368 units the first diagnostic points
  at the opening parenthesis of a NUM call. Test the guide’s prime-emulation
  examples, including empty strings, lone signs, a lone decimal point,
  and rejected exponent notation.

After NUM, 11,325 of 17,336 candidates pass strict C99 checking,
including all 11,111 previous passes. Of the 368 units whose first
diagnostic pointed to a NUM call’s opening parenthesis, 176 now pass
and 192 reach another diagnostic. Another 38 units with different first
diagnostics also pass.

- [x] Start ICONV with the guide’s compact calendar dates and the D and D4
  masks. Check the internal day count and leap-year example with native
  tests. In 191 units the first diagnostic points at an ICONV call’s opening
  parenthesis. These calls use several conversion masks.

After ICONV date support, 11,425 of 17,336 candidates pass strict C99
checking, including all 11,325 previous passes. Of the 191 units whose
first diagnostic pointed at an ICONV call’s opening parenthesis, 85 now
pass and 106 reach another diagnostic. Mask selection happens at runtime,
so the corpus count includes calls using masks beyond D and D4.

- [x] Implement FIELDS, whose opening parenthesis is the first diagnostic
  in 68 units. Use the guide’s example to check extraction across field,
  value and subvalue marks, with and without an explicit extraction count.

After FIELDS, 11,472 of 17,336 candidates pass strict C99 checking,
including all 11,425 previous passes. Of the 68 units whose first
diagnostic pointed at a FIELDS call’s opening parenthesis, 43 now pass
and 25 reach another diagnostic.

- [x] Implement STR(text, repetitions), whose opening parenthesis is the
  first diagnostic in 67 units. Verify whole-string repetition with the
  guide’s 999-copy example, empty input, and zero repetitions.

After STR, 11,497 of 17,336 candidates pass strict C99 checking,
including all 11,472 previous passes. Of the 67 units whose first
diagnostic pointed at a STR call’s opening parenthesis, 18 now pass
and 49 reach another diagnostic.

- [x] Implement the INSERT function, whose opening parenthesis is the
  first diagnostic in 94 units. Cover the guide’s semicolon before the
  inserted value and the five-argument comma form used in T24. Check the
  returned array and verify that evaluating INSERT preserves its input.

After INSERT, 11,556 of 17,336 candidates pass strict C99 checking,
including all 11,497 previous passes. Of the 94 units whose first
diagnostic pointed at an INSERT call’s opening parenthesis, 54 now
pass and 40 reach another diagnostic.

- [x] Implement REPLACE, the first diagnostic at a function call’s opening
  parenthesis in 20 units. Use the guide’s value replacement example to
  verify the returned array, preservation of the source, and preservation
  of neighboring elements. Check argument forms against the reference parser.

After REPLACE, 11,572 of 17,336 candidates pass strict C99 checking,
including all 11,556 previous passes. Of the 20 units previously blocked
at a REPLACE call, 16 now pass and four reach another diagnostic.

- [x] Implement UPCASE, DOWNCASE and the LOWCASE alias in the current
  byte-oriented runtime. Test ASCII letters, punctuation and array marks.
  Calls to these functions are the first diagnostic in 60, seven and two
  units respectively.

After case conversion, 11,615 of 17,336 candidates pass strict C99 checking,
including all 11,572 previous passes. Of the 69 units previously blocked
at these functions, 40 now pass and 29 reach another diagnostic.

- [x] Implement QUOTE and DQUOTE for double quotes and SQUOTE for single
  quotes. Verify empty strings, embedded quotes and array marks. Calls to
  these functions are the first diagnostic in 27, 48 and 14 units respectively.

After the quote functions, 11,682 of 17,336 candidates pass strict C99
checking, including all 11,615 previous passes. Of the 89 units previously
blocked at these calls, 63 now pass and 26 reach another diagnostic.

- [x] Implement MOD(dividend, divisor), the first blocker in 84 units.
  Check the guide’s loop example and its rule that a zero divisor returns
  the dividend. Cover signed and fractional operands and nonnumeric input.

After MOD, 11,740 of 17,336 candidates pass strict C99 checking,
including all 11,682 previous passes. Of the 84 units previously blocked
at MOD, 47 now pass and 37 reach another diagnostic.

- [x] Implement LEFT and RIGHT. Their calls are the first diagnostic in
  51 and 35 units respectively. Verify the guide’s leading and trailing
  substring examples, oversized lengths, and lengths below one.

After LEFT and RIGHT, 11,802 of 17,336 candidates pass strict C99
checking, including all 11,740 previous passes. Of the 86 units
previously blocked at these calls, 57 now pass and 29 reach another
diagnostic.

- [x] Implement the dynamic-array DELETE function, the first diagnostic
  at a call in 65 units. Check supported argument counts in the reference
  parser and verify field, value and subvalue removal on a copy of the
  source array.

After the DELETE function, 11,846 of 17,336 candidates pass strict C99
checking, including all 11,802 previous passes. Of the 65 units previously
blocked at these calls, 38 now pass and 27 reach another diagnostic.

- [x] Implement MAXIMUM and MINIMUM, the first blockers in 35 and 13 units
  respectively. Check the guide’s PRECISION examples, empty components
  treated as zero, and nonnumeric components ignored across array levels.

After MAXIMUM and MINIMUM, 11,884 of 17,336 candidates pass strict C99
checking, including all 11,846 previous passes. Of the 48 units previously
blocked at these functions, 34 now pass and 14 reach another diagnostic.

- [x] Implement SUBSTRINGS, the first blocker in 32 units. Verify byte
  extraction within each element, oversized lengths, and preservation of
  field, value and subvalue marks around empty elements.

After SUBSTRINGS, 11,903 of 17,336 candidates pass strict C99 checking,
including all 11,884 previous passes. Of the 32 units previously blocked
at SUBSTRINGS, 17 now pass and 15 reach another diagnostic.

- [x] Implement SPLICE, the first blocker in 31 units. Verify the guide’s
  mixed value/subvalue example and how unmatched elements are combined
  with the separator when the two arrays have different shapes.

After SPLICE, 11,916 of 17,336 candidates pass strict C99 checking,
including all 11,903 previous passes. Of the 31 units previously blocked
at SPLICE, 11 now pass and 20 reach another diagnostic.

- [x] Support scalar REUSE operands in SPLICE. The first diagnostic points
  at a REUSE call in 17 units. T24 uses this form to repeat a prefix or
  suffix. Test both operand positions across differently shaped arrays.

After scalar REUSE in SPLICE, 11,932 of 17,336 candidates pass strict C99
checking, including all 11,916 previous passes. Of the 17 units previously
blocked at REUSE calls, 15 now pass and two reach another diagnostic.

- [x] Implement TRIMF and TRIMB, the first blockers in 20 and seven units
  respectively. Verify the guide’s equivalences to TRIM with a space
  and mode L or T, including tabs and interior spaces.

After TRIMF and TRIMB, 11,957 of 17,336 candidates pass strict C99
checking, including all 11,932 previous passes. Of the 27 units whose
first diagnostic pointed to a TRIMF or TRIMB call’s opening parenthesis,
nine now pass and 18 reach another diagnostic.

- [x] Implement ALPHA for the byte-oriented runtime. The first diagnostic
  points at an ALPHA call in 25 units. Check the guide’s letters-only and
  trailing-digit examples, along with punctuation, empty input and array marks.

After ALPHA, 11,975 of 17,336 candidates pass strict C99 checking,
including all 11,957 previous passes. Of the 25 units previously blocked
at ALPHA, 13 now pass and 12 reach another diagnostic.

- [x] Implement scalar NEG, the first blocker in 20 units. Check the NEGS
  chapter’s scalar examples, including signed numbers, a comparison result
  and the documented zero substitution for nonnumeric input.

After NEG, 11,982 of 17,336 candidates pass strict C99 checking,
including all 11,975 previous passes. Of the 20 units previously blocked
at NEG, seven now pass and 13 reach another diagnostic.

- [x] Implement RETURN TO label. In 142 units the first diagnostic points
  at TO in this statement. Check the reference compiler’s handling of the
  GOSUB return stack, exercise nested calls and validate the target label.

After RETURN TO, 12,100 of 17,336 candidates pass strict C99 checking,
including all 11,982 previous passes. Of the 142 units previously blocked
at RETURN TO, 118 now pass and 24 reach another diagnostic.

- [x] Support the spaced augmented assignment seen in T24 sources, such
  as `RESULT<1> + = 1`. Check how the reference grammar handles whitespace
  and exercise both scalar and dynamic-array targets.

After arithmetic compound assignments, 12,235 of 17,336 candidates pass
strict C99 checking, including all 12,100 previous passes. All 38 units
previously rejected with `unsupported statement 'RESULT'` now pass.

- [x] Implement `@TM`, the text mark (byte 251) documented with `@AM`,
  `@VM` and `@SM`. Verify its byte value and exercise it in a string.
  It is the first diagnostic in 13 T24 units.

With `@TM`, `@SVM`, `@IM` and `@RM`, 12,255 of 17,336 candidates pass
strict C99 checking, including all 12,235 previous passes. Ten of the 13
units blocked at `@TM` now pass, along with five each for `@SVM` and `@IM`.

- [x] Accept empty `BEGIN CASE` / `END CASE` blocks. All 284 units whose
  first diagnostic is `expected CASE clause` have only comments or blank
  lines before `END CASE`. Test that execution continues after the block
  and that malformed nonempty blocks still get a diagnostic.

After empty CASE blocks, 12,493 of 17,336 candidates pass strict C99
checking, including all 12,255 previous passes. Of the 284 units blocked
at an empty block, 238 now pass and 46 reach another diagnostic.

- [x] Support CALL argument lists that continue on the next line after a
  comma. In 498 units the first diagnostic expects an expression at the end
  of such a CALL line. Check the reference continuation rules and verify
  argument order and by-reference updates across a line break.

After comma continuation, 12,957 of 17,336 candidates pass strict C99
checking, including all 12,493 previous passes. Of the 498 units previously
blocked at a CALL line ending in a comma, 399 pass and 99 reach another
diagnostic.

- [x] Accept an optional colon after GOSUB and GOTO targets, as the
  reference grammar does with `Label_opt_colon`. The first diagnostic
  points at this colon in 151 GOSUB units and 44 GOTO units. Exercise named
  and numeric targets and preserve the existing checks for invalid jumps.

After optional jump-target colons, 13,025 of 17,336 candidates pass strict
C99 checking, including all 12,957 previous passes. Of the 195 units
blocked at a target colon, 68 now pass and 127 reach another diagnostic.

- [x] Support the two-expression OPEN form. In 158 units the first
  diagnostic points at the comma after the first OPEN operand. Check
  `OPEN '', name` and `OPEN 'DICT', name` against the guide and exercise
  data and dictionary handles separately with the in-memory file backend.

After two-expression OPEN, 13,057 of 17,336 candidates pass strict C99
checking, including all 13,025 previous passes. Of the 158 units blocked
at the first OPEN comma, 32 now pass and 126 reach another diagnostic.

- [x] Handle ELSE on a following line. The reference preprocessor joins
  the newline before this keyword, including across blank and comment
  lines. Exercise inline arms, END followed by ELSE, and nested IFs.
  An unexpected standalone ELSE is the first blocker in 251 units.

After branch-keyword continuation, 13,340 of 17,336 candidates pass strict
C99 checking, including all 13,057 previous passes. Of the 251 units
previously blocked at a standalone ELSE, 199 now pass and 52 reach
another diagnostic.

- [x] Support static routine names beginning with `!`, such as
  `CALL !HUSHIT(1)`. The first diagnostic points at this prefix in 104
  CALL statements and three SUBROUTINE headers. Check a caller and
  definition together and preserve `!` in comments and expressions.

After bang-prefixed subroutine names, 13,359 of 17,336 candidates pass
strict C99 checking, including all 13,340 previous passes. Of the 107
units previously blocked at the prefix, 19 now pass and 88 reach another
diagnostic.

- [x] Support single-argument substring extraction, `expression[n]`.
  The RIGHT chapter defines it as the last n characters. Check the
  reference grammar, dynamic-array values, and zero and oversized lengths.
  In 532 units the first diagnostic expects a comma at a closing bracket.

After suffix extraction, 13,746 of 17,336 candidates pass strict C99
checking, including all 13,359 previous passes. Of the 532 units with a
closing-bracket diagnostic, 387 now pass, 142 reach a new diagnostic and
three still require single-argument substring assignment.

- [x] Implement two-coordinate terminal positioning, `@(col,row)`. In at
  least 544 units the first diagnostic points at the coordinate comma.
  Check the guide’s zero-based origin, verify the emitted terminal bytes
  for constant and computed coordinates, and retain the existing @(-2) test.

After two-coordinate cursor positioning, 14,026 of 17,336 candidates pass
strict C99 checking, including all 13,746 previous passes. Of the 544
units identified at the coordinate comma, 275 pass and 269 reach another
diagnostic.

- [x] Implement the common terminal clearing codes `@(-1)`, `@(-3)` and
  `@(-4)` using the guide’s SCREENCODE table. Among the 280 new strict C99
  passes, 166 source files contain at least one of these literal forms.
  Verify clear-and-home, erase to end of screen, and erase to end of line
  by comparing the native output bytes.

All 14,026 of the 17,336 candidates that passed strict C99 checking before
the screen-code runtime change still pass. Native tests check the bytes
for a stored clear-and-home sequence and both partial clears.

- [x] Implement indirect `CALL @Name(args)`. In 376 units the first
  diagnostic points at the `@` after CALL. Resolve the variable's value
  against the subroutines supplied to the compiler and test by-reference
  updates, missing targets, and incompatible argument lists.

After indirect CALL, 14,324 of 17,336 candidates pass strict C99
checking, including all 14,026 previous passes. Of the 376 units blocked
at the target variable, 298 now pass and 78 reach another diagnostic.

- [x] Implement READU for the in-memory file backend. It is the first
  blocker in 187 units. Check the guide’s lock lifetime for existing and
  missing keys, and exercise the success, missing-record and lock-conflict
  branches with explicit and default file descriptors.

After READU, RELEASE and RECORDLOCKED, 14,527 of 17,336 candidates
pass strict C99 checking, including all 14,324 previous passes.
Of the 187 files blocked at READU, 146 now pass and 41 reach another
diagnostic. The in-memory backend uses a permanent foreign-lock fixture
to test contention. Timed WAIT remains unsupported.

- [x] Implement MATREADU using the same update locks as READU. It is
  the first blocker in 35 units. Check matrix contents and SETTING on
  success, missing keys and lock conflicts, and test release by MATWRITE.

After MATREADU, 14,546 of 17,336 candidates pass strict C99 checking,
including all 14,527 previous passes. Of the 35 files blocked at MATREADU,
19 now pass and 16 reach another diagnostic.

- [x] Implement line-oriented `INPUT Var`, including the trailing colon
  seen in T24. Check prompt and newline handling against the INPUT chapter
  and exercise consecutive reads, an empty line and end-of-file through
  the native executable. INPUT is the first blocker in 84 files.

After line-oriented INPUT and PROMPT, 14,574 of 17,336 candidates pass
strict C99 checking, including all 14,546 previous passes. Of the 84
files blocked at INPUT, 25 now pass and 59 reach another diagnostic.
Three more pass after PROMPT support.

- [x] Implement length-limited `INPUT Var, n` and its trailing-colon
  form. In 32 units the first diagnostic points at the comma after
  the input variable. Exercise early Enter, automatic completion at the
  limit and the bytes available to a subsequent INPUT.

After length-limited INPUT, 14,592 of 17,336 candidates pass strict
C99 checking. All 14,574 previous passes still pass. Of the 32 units
blocked at the comma, 18 now pass and 14 reach another diagnostic.

- [x] Implement timed `INPUT Var FOR n` with THEN and ELSE. The INPUT
  chapter specifies a timeout in tenths of a second between keystrokes.
  Test successful completion and timeout with a partially filled variable.

After timed INPUT, 14,592 of 17,336 candidates still pass strict C99
checking. The only changed diagnostic is in WHERE.MONITOR, which now
reaches a read of `@SENTENCE` after its timed INPUT.

- [x] Support reading `@SENTENCE`, the next blocker in 23 units.
  Check how the invocation is represented, then exercise a native program
  with and without command-line arguments and read the value in a subroutine.

After adding `@SENTENCE`, 14,593 of 17,336 candidates pass strict C99
checking. All previous passes still pass. Of the 23 units previously
blocked there, CREATE.SC.VAL.COST passes and 22 reach later diagnostics.

- [x] Recognize EQU and EQUATE after a statement separator. All 37 units
  currently blocked at EQU use it after a semicolon. Test multiple
  definitions on a line and expansion in subsequent statements.

After inline EQU and EQUATE, 14,622 of 17,336 candidates pass strict
C99 checking, including all 14,593 previous passes. Of the 37 units
blocked at EQU, 27 now pass and 10 reach another diagnostic. Two more
units with different first diagnostics also pass.

- [x] Implement indexed `ON expression GOSUB` and `ON expression GOTO`.
  These are the first blockers in 28 and 4 units respectively. Test
  one-based label selection, return to the next statement after GOSUB,
  and the guide's emulation-dependent behavior for out-of-range indices.

After indexed GOTO and GOSUB, 14,633 of 17,336 candidates pass strict
C99 checking. All 14,622 previous passes still pass. Of the 32 units
blocked at ON, 11 now pass and 21 reach another diagnostic.

- [x] Implement SLEEP with a numeric duration in seconds, including
  fractions and the default one-second pause. SLEEP is the first blocker
  in 29 units. Test elapsed time and resumption at the following statement.

After numeric SLEEP, 14,645 of 17,336 candidates pass strict C99 checking.
All 14,633 previous passes still pass. Of the 29 units blocked at SLEEP,
12 now pass and 17 reach another diagnostic.

- [x] Implement bare BREAK using the existing loop EXIT behavior. BREAK
  is the first blocker in 34 units. Test leaving the innermost FOR and
  LOOP, and the guide's warning when BREAK appears outside a loop.

After bare BREAK, 14,673 of 17,336 candidates pass strict C99 checking.
All 14,645 previous passes still pass. Of the 34 units blocked at BREAK,
28 now pass and six reach another diagnostic.

- [x] Support a trailing UNTIL condition in a FOR body before NEXT. Of
  the 41 units first blocked at an UNTIL statement, 26 have NEXT on the
  following non-comment line. Test early exit before the increment and
  normal iteration when the condition stays false.

After FOR body guards, 14,707 of 17,336 candidates pass strict C99
checking, including all 14,673 previous passes. Of the units previously
blocked at UNTIL or WHILE, 26 and 8 respectively now pass.

- [x] Match the reference parser when NEXT names a different counter. It
  warns and closes the innermost FOR using the counter from its header.
  Test nested loops, the warning location and the counter values after
  each loop. A mismatched NEXT is the first diagnostic in 69 units.

After accepting mismatched NEXT counters with a warning, 14,762 of
17,336 candidates pass strict C99 checking. All 14,707 previous passes
still pass. Of the 69 units previously blocked here, 55 now pass and
14 reach a later diagnostic.

- [x] Implement plain EXECUTE and its PERFORM synonym for native programs.
  EXECUTE is the first blocker in 346 units. Test a local command's
  output and that the caller resumes after the child exits. Follow with
  CAPTURING and its newline-to-field-mark conversion.

After plain EXECUTE and PERFORM, 14,918 of 17,336 candidates pass
strict C99 checking. All 14,762 previous passes still pass. Of the 346
units first blocked at EXECUTE, 156 now pass and 190 reach another
diagnostic.

- [x] Implement CAPTURING for EXECUTE and PERFORM. It is the first
  diagnostic in 32 units. Test empty output, multiple lines, a final
  line without a newline, and stderr remaining visible to the caller.

After CAPTURING, 14,935 of 17,336 candidates pass strict C99 checking.
All 14,918 previous passes still pass. Of the 32 units first blocked at
CAPTURING, 17 now pass and 15 reach another diagnostic.

- [x] Implement RETURNING and its synonym SETTING for EXECUTE and
  PERFORM. Put the child exit status in the first field and check how
  error text is represented. Test both orders with CAPTURING and a child
  that writes to both stdout and stderr before exiting nonzero.

After RETURNING and SETTING, 14,936 of 17,336 candidates pass strict
C99 checking. All 14,935 previous passes still pass. Of the four units
previously blocked at SETTING after a command, one now passes and three
reach later diagnostics.

- [x] Investigate and implement `@SYSTEM.RETURN.CODE`, the first blocker
  in 67 units. Check which command forms update it and what a caller
  reads after consecutive successful and unsuccessful commands.

After native command return-code support, 14,975 of 17,336 candidates
pass strict C99 checking, including all 14,936 previous passes. Of the
67 units first blocked at @SYSTEM.RETURN.CODE, 39 now pass and 28 reach
another diagnostic.

- [x] Recognize GO and GO TO as GOTO spellings, as in the reference
  lexer. GO is the first blocker in 13 units. Exercise label resolution,
  assignment checks after jumps, and jumps across FOR headers.

After GO and GO TO, 14,985 of 17,336 candidates pass strict C99 checking.
All 14,975 previous passes still pass. Of the 13 units blocked at GO,
10 now pass and three reach another diagnostic.

- [x] Implement MATCHFIELD(string, pattern, field) using the existing
  MATCHES pattern rules. Test extraction from a full match, variable-width
  components and a pattern that leaves unmatched input. The guide gives
  executable examples for each of these cases.

After MATCHFIELD, 15,021 of 17,336 candidates pass strict C99 checking.
All 14,985 previous passes still pass. Another 36 units now pass and
nine reach a different diagnostic.

- [x] Implement SORT(expression). The guide specifies ascending
  left-justified order across mixed dynamic-array delimiters and
  attribute marks between sorted elements. Test mixed delimiters,
  duplicates, empty elements and preservation of the input.

After SORT, 15,038 of 17,336 candidates pass strict C99 checking.
All 15,021 previous passes still pass. Another 17 units now pass and
five reach a different diagnostic.

- [x] Implement EQS(array1, array2). Use the guide's mixed value and
  subvalue example to test how corresponding elements align. Cover
  unequal lengths and distinguish a missing element from an empty one.

After EQS, 15,057 of 17,336 candidates pass strict C99 checking.
All 15,038 previous passes still pass. Another 19 units now pass and
one reaches a different diagnostic.

- [x] Implement NES(array1, array2) with the same element alignment as
  EQS. The guide specifies 1 for missing elements and null for a pair
  containing a null element. Exercise both cases with nested marks.

After NES, 15,065 of 17,336 candidates pass strict C99 checking.
All 15,057 previous passes still pass. Eight more units now pass and
one reaches a different diagnostic.

- [x] Implement CATS(array1, array2) to concatenate corresponding elements.
  Exercise the guide's mixed value and subvalue example, a wholly empty
  operand, and the scalar REUSE prefix used in T24.

After CATS, 15,071 of 17,336 candidates pass strict C99 checking.
All 15,065 previous passes still pass. Six more units now pass and
one reaches a different diagnostic.

- [x] Implement RND(bound). Test the guide's integer range for positive
  and negative bounds, the single possible result for a bound of one,
  and diagnostics for invalid inputs. Check zero-bound behavior separately
  since the guide's stated range is empty for zero.

After RND, 15,088 of 17,336 candidates pass strict C99 checking.
All 15,071 previous passes still pass. Seventeen more units now pass
and one reaches a different diagnostic.

- [x] Implement REM(dividend, divisor) in expressions. The reference
  compiler emits the same runtime call for REM and MOD. Cover signed
  and decimal operands, zero divisors, and REM comments at statement start.

After REM, 15,102 of 17,336 candidates pass strict C99 checking.
All 15,088 previous passes still pass. Fourteen more units now pass
and two reach a different diagnostic.

- [x] Implement TRIMS(array). The reference lexer accepts one argument.
  Verify trimming of leading, trailing and repeated interior spaces at
  each dynamic-array position. Cover mixed marks and empty elements.

After TRIMS, 15,109 of 17,336 candidates pass strict C99 checking.
All 15,102 previous passes still pass. Seven more units now pass and
four reach a different diagnostic.

- [x] Implement SUMMATION(array). The reference lexer accepts one argument.
  Check how it totals mixed field, value and subvalue levels, including
  empty and nonnumeric elements, before sharing arithmetic with SUM.

After SUMMATION, 15,117 of 17,336 candidates pass strict C99 checking.
All 15,109 previous passes still pass. Eight more units now pass and
one reaches a different diagnostic.

- [x] Implement PWR(base, exponent) and the guide's infix power operator.
  Check precedence and associativity against the reference grammar.
  Cover integer and fractional powers, PRECISION and invalid domains.

After power operators and unary signs, 15,190 of 17,336 candidates pass
strict C99 checking. All 15,117 previous passes still pass. Of the 73 new
passes, 44 previously stopped at a star and 11 at a plus. Seven more
units reach a different diagnostic.

- [x] Implement SQRT(expression) using the guide's PRECISION examples.
  Exercise positive, zero, negative and nonnumeric inputs through the
  native compiler.

After SQRT, 15,190 of 17,336 candidates still pass strict C99 checking.
DX.PR.BLACK76 and DX.PR.NORMSDIST.DASH both advance to EXP.

- [x] Implement EXP(expression), the natural exponential. Check EXP(0),
  positive and negative arguments, PRECISION, invalid input and overflow.
  Recheck the two pricing routines that reached EXP after SQRT.

After EXP, 15,191 of 17,336 candidates pass strict C99 checking.
DX.PR.NORMSDIST.DASH now passes and all 15,190 prior passes still pass.
DX.PR.BLACK76 reaches a call to LN.

- [x] Implement LN(expression), the natural logarithm. Test LN(1),
  fractions, PRECISION and diagnostics for inputs outside the positive
  real domain. Recheck DX.PR.BLACK76.

After LN, 15,193 of 17,336 candidates pass strict C99 checking.
DX.PR.BLACK76 and EB.CALC.TERM now pass,
and all 15,191 previous passes still pass.

- [x] Investigate MAT copies between differently dimensioned arrays, the
  first diagnostic in 110 units. Check unequal extents and rank changes
  against the reference before changing copy lengths or runtime checks.

All 110 first failures at MAT copy involved vectors. In 61 the
destination was shorter and in 49 it was longer. After supporting
unequal shapes, 91 of those units pass strict C99 checking and 19
reach another diagnostic. All previous passes still pass, for a total
of 15,284 of 17,336 candidates.

- [x] Investigate HEADING, the first diagnostic in 103 units. Check
  plain headings and HEADING ON print-unit forms against the reference.
  Exercise header placement and page breaks through native output tests.

After HEADING and PAGE, 15,388 of 17,336 candidates pass strict C99
checking. All 15,284 previous passes still pass. Of the 130 files
previously blocked first by HEADING, HEADINGN or PAGE, 104 pass and
26 reach another diagnostic. Native fixtures cover header replacement,
page numbering, automatic breaks, and terminal pause and resume.
Explicit print units currently produce a source-located runtime error.

- [x] Investigate PRINT ON and PRINTER against the reference grammar.
  BUILD.DICTS.INDICES now reaches PRINT ON 1. Establish how unit
  selection interacts with CRT, headings and page state, and exercise
  separate units with a native test backend.

With PRINT ON and PRINTER, 15,416 of 17,336 candidates pass strict C99
checking, including all 15,388 previous passes. PRINTER.ON, PRINTER.OFF,
PRINTER.CLOSE and ENQUIRY.REPORT.RUN now pass. BUILD.DICTS.INDICES
advances to INDICES(file). Native tests compare terminal output and each
job’s bytes across routing changes, page breaks, resets and closes.

- [x] Implement sequential file I/O, starting with OPENSEQ, the first
  diagnostic in 44 units. Check its path and file/record forms against
  the grammar. Exercise success and failure arms, READSEQ end of file,
  WRITESEQ and CLOSESEQ with temporary files.

After regular-file sequential I/O, 15,437 of 17,336 candidates pass
strict C99 checking. All 15,416 previous passes still pass. Fourteen
additional passes came from the 44 OPENSEQ cases, three from WRITESEQ,
two from READSEQ and two from CLOSESEQ.

- [x] Implement CREATE on the descriptor returned for a missing sequential
  file, and WEOFSEQ to truncate at the current file position. These are
  now the first blockers for seven and five of the original 44 OPENSEQ
  cases respectively. Check creation races and preservation of the prefix
  before the current position against native fixtures.

After CREATE and WEOFSEQ, 15,441 of 17,336 candidates pass strict C99
checking. All 15,437 previous passes still pass. ATM.SPOOL.LOG,
CRP.GENERATE.DATABASE, CRP.GENERATE.TXN.DATABASE and OFS.INITIALISE.SOURCE
now pass. Native tests cover competing pending handles, truncation after
a buffered read, subsequent writes and read-only failures.

- [x] Implement SEEK for regular sequential files. ATM.CONTROL and
  ATM.CONTROL.USW now reach SEEK with an offset of zero relative to EOF.
  Check offsets relative to the start, current position and end, including
  failed seeks, with native read/write fixtures.

After SEEK, all 15,441 previous strict C99 passes still pass. The two
ATM.CONTROL variants advance to TIMEOUT on an input pipe. Native fixtures
verify byte positioning after buffered reads, failed seeks, rewind after
EOF, and a write beyond EOF that leaves a zero-filled gap.

- [x] Implement OPENPATH, the first diagnostic in 23 candidates. Check
  named and default descriptors, relative and absolute paths, and missing
  files with SETTING. Verify record reads and writes through the opened
  descriptor using an explicit test backend.

After OPENPATH, 15,451 of 17,336 candidates pass strict C99 checking.
All 15,441 previous passes still pass. Ten of the 23 OPENPATH cases now
pass, six reach the STATUS statement, and three reach CLOSE. Native tests
exercise explicit and default descriptors against path-named memory files.

- [x] Implement the STATUS statement (`STATUS result FROM descriptor`),
  the first diagnostic in 23 candidates. Check the fields read by T24
  against the guide and reference grammar, and exercise valid and missing
  descriptors through the record backend.

After STATUS, 15,465 of 17,336 candidates pass strict C99 checking.
Fourteen of the 23 previously blocked units now pass and every previous
pass still passes. Two of those units now reach CLOSE. Native fixtures
check the record backend’s size, name and type, and compare sequential
metadata with the host file before and after reading to EOF.

- [x] Implement CLOSE for record files, the first diagnostic in 12
  candidates. Verify default and explicit descriptors, lock release,
  and reopening a file with its records intact.

After CLOSE, 15,474 of 17,336 candidates pass strict C99 checking.
Nine of the 12 formerly blocked units now pass, including SYSTEM.RESTORE
and both AM.REP routines. All 15,465 previous passes still pass. The
reference grammar requires a named descriptor. Native tests verify
that closing it leaves the default descriptor usable and that later
routine cleanup preserves locks acquired after an explicit close.

- [x] Implement GETENV(name, variable). EBS.CREATE.FILE now reaches it
  after CLOSE. Verify the Boolean result and the output variable for
  present, empty and missing environment variables in a native subprocess.

After both GETENV forms, 15,480 of 17,336 candidates pass strict C99
checking. All 15,474 previous passes still pass. Six additional units
pass, including GET.ENV.JBASE and T24.BUILD.LIBRARIES. EBS.CREATE.FILE
advances to a duplicate declaration of R.FILE.CONTROL.

- [x] Implement PUTENV(expression). EB.CATALOG.PATCH.JBASE and
  SET.LIBRARIES.JBASE now reach it. Verify replacement, empty values,
  failure handling and visibility to GETENV and child processes.

After PUTENV, 15,482 of 17,336 candidates pass strict C99 checking.
EB.CATALOG.PATCH.JBASE and SET.LIBRARIES.JBASE now pass, along with
all 15,480 previous passes. Native tests cover child-process inheritance,
empty values, malformed assignments and short-circuit evaluation.

- [x] Recognize dynamic-array assignment with whitespace before the
  selector. All 28 first diagnostics naming T.SEQU are appends such as
  `T.SEQU <-1> = A+1` or `T.SEQU < - 1 > = A + 1`. Check the grammar
  and test both spellings alongside less-than and greater-than comparisons.

After spaced dynamic-array assignments, 15,574 of 17,336 candidates
pass strict C99 checking. All 15,482 previous passes still pass.
Of the 92 new passes, 25 previously stopped at T.SEQU and 67 at other
assignment targets. The remaining three T.SEQU cases now reach later
diagnostics. Native fixtures exercise both append spellings, compound and
substring assignments, nested indices, matrix elements and comparisons.

- [x] Support the alternate comparison spellings `=<` and `=>`. The
  reference preprocessor maps them to LE and GE. Check both against
  ordinary comparisons and dynamic-array selectors in native fixtures.

After alternate comparisons, 15,596 of 17,336 candidates pass strict C99
checking. All 15,574 previous passes still pass. The 22 additional passes
include AC.CP.CHECK.SWEEP.REQD, EB.CALC.EIR and SWAP.PARAMETER.

- [x] Recognize spaced dynamic-array extraction in expressions. For
  example, AC.EXP.RECS.EOD reads `R.AC.EXPECTED.RECS <AC.EXP.ACCOUNT.ID>`
  on the right of an assignment. Check the reference’s disambiguation
  rules and exercise spaced selectors alongside chained comparisons.

The native fixture exercises one to three indices, nested selectors, a
substring, arithmetic, comparison chains and LOCATE. The expected output
uses the existing tight-selector semantics. Choosing a comparison when
a plain operand follows a spaced bracket pair is a project rule pending
a reference execution.

After spaced array reads, 15,727 of 17,336 candidates pass strict C99
checking. All 15,596 previous passes still pass. The 131 additional
passes include AC.EXP.RECS.EOD, AA.SIMULATION.PROJECTION and
CREATE.INAU.RECORDS.

- [x] Implement HUSH. The guide documents ON, OFF, an expression and a
  bare toggle. Exercise terminal output suppression and restoration in
  a native fixture. HUSH is the first blocker in 20 T24 files.

After HUSH, 15,741 of 17,336 candidates pass strict C99 checking. All
15,727 previous passes still pass. Of the 20 files that stopped at HUSH,
14 now pass and six reach later diagnostics.

- [x] Support saved lists with WRITELIST and READLIST. Verify that one
  executable can save a named list and another can retrieve it, check
  its element count and iterate it with READNEXT. Cover a missing list
  and a failed write. READLIST is the first blocker in 20 files and
  WRITELIST in 16.

After saved lists, 15,765 of 17,336 candidates pass strict C99 checking.
All 15,741 previous passes still pass. Of the 24 new passes, 11 previously
stopped at READLIST and 13 at WRITELIST. Two native executables share a
list directory to check replacement, retrieval, element counts and iteration.

- [x] Implement GETLIST and DELETELIST against the saved-list store.
  Exercise the guide’s write, retrieve and delete sequence across processes.
  GETLIST is the first blocker in five files and DELETELIST in two.

After GETLIST and DELETELIST, 15,769 of 17,336 candidates pass strict C99
checking. All 15,765 previous passes still pass. Four of the seven files
blocked by these statements now pass, and three reach later diagnostics.
All five GETLIST cases used the reference grammar’s omitted TO clause.

- [x] Implement FORMLIST to build a default, named or numbered select
  list from a dynamic array. Check the reference grammar’s optional
  SETTING clause and verify element order with READNEXT. FORMLIST is
  the first blocker in three files.

After FORMLIST, 15,772 of 17,336 candidates pass strict C99 checking.
All 15,769 previous passes still pass. E.CRYS.PORT.VAL, E.GET.SC.PERF.VB
and E.GET.SC.VAL.VB now pass with the default-list form.

- [x] Implement SSELECT for open files. Verify that READNEXT visits
  record IDs in ascending order when insertion order differs, and cover
  the default file, explicit destinations and ON ERROR. File SSELECT
  is the first blocker in 11 T24 units.

After file SSELECT, 15,780 of 17,336 candidates pass strict C99 checking.
All 15,772 previous passes still pass. Eight of the eleven SSELECT
blockers now pass. Two of the three remaining files reach a loop guard
after an inline READNEXT arm.

- [x] Allow an inline READNEXT arm to end at a LOOP guard, as in
  `LOOP READNEXT ID ELSE ID = "" WHILE ID <> ""`. Verify that the guard
  tests the value after the conditional arm and that an inner ELSE
  still binds to its own statement. Eleven T24 files first stop at
  WHILE in this pattern.

After inline loop guards, 15,795 of 17,336 candidates pass strict C99
checking. All 15,780 previous passes still pass. Of the 15 additional
passes, eight previously stopped at WHILE, including
EOD.GROUP.ACCRUAL.POST and RE.UPDT.STAT.LINE.CONT.

- [x] Implement READVU by combining field extraction with a record lock.
  Verify explicit and default files, field zero, successful and missing
  reads, LOCKED and ON ERROR. READVU is the first blocker in nine files.

After READVU, 15,800 of 17,336 candidates pass strict C99 checking.
All 15,795 previous passes still pass. Five of the nine READVU blockers
now pass. Three reach a diagnostic in I_GOSUB.MSK and one reaches WRITEU.

- [x] Implement WRITEU to update a record while preserving its lock.
  Verify that updating a locked record retains the lock, that WRITE
  or RELEASE can release it, and that SETTING and ON ERROR handle
  failures. WRITEU is the first blocker in four files.

After WRITEU, 15,804 of 17,336 candidates pass strict C99 checking.
All 15,800 previous passes still pass. All four WRITEU blockers now
pass, including TK.DATA.CAPTURE.1, which previously stopped at READVU.

- [x] Implement WRITEV and WRITEVU for field updates. Verify that
  they preserve other fields, fill gaps with empty fields, and handle
  owned and foreign locks. WRITEV is the first blocker in six files.

After WRITEV and WRITEVU, 15,810 of 17,336 candidates pass strict C99
checking. All 15,804 previous passes still pass. All six WRITEV blockers
now pass.

- [x] Implement `IF condition THEN value ELSE value` in expressions.
  Check the reference grammar's resultant production and verify that
  only the selected arm runs, including when the values are nested
  in function arguments, array indices, or concatenations. The shared
  I_GOSUB.MSK include uses this form in a concatenation.

After conditional expressions, 15,877 of 17,336 candidates pass strict
C99 checking. All 15,810 previous passes still pass. The 67 additional
passes include COLLATERAL.ALLOCATION, which uses a conditional array
index, and COLLATERAL.PARAMETER, which uses a conditional in concatenation.
The three ARCHIVES files blocked in I_GOSUB.MSK now reach its format mask
expression on line 307.

- [x] Support the reference grammar's implicit format expression, as in
  `Value "10R"` and `Value Mask<2>`. Reuse FMT and test precedence,
  keyword boundaries, and literal and variable masks.

After implicit formatting, 16,010 of 17,336 candidates pass strict C99
checking. All 15,877 previous passes still pass. The 133 additional
passes include ARCHIVES.FIELD.RUN and ARCHIVES.LIVE.TO.HIST.RUN.
ARCHIVES.UPDATE.RUN advances to a duplicate declaration.

- [x] Support message operands on STOP and implement ABORT. Check the
  reference grammar and guide, define how standalone executables render
  message arguments, and verify termination and exit status from main
  programs and called routines. STOP operands are the first blocker in
  47 files and ABORT in ten.

After STOP and ABORT, 16,043 of 17,336 candidates pass strict C99
checking. All 16,010 previous passes still pass. Of the 33 additional
passes, 26 previously stopped at a STOP operand and seven at ABORT.

- [x] Add SETTING and ON ERROR to ordinary WRITE. Verify that failures
  report the file status and enter the error arm, and that existing
  WRITE forms and lock release still work. WRITE with ON ERROR is
  the first blocker in 38 files.

After WRITE status and error arms, 16,077 of 17,336 candidates pass
strict C99 checking. All 16,043 previous passes still pass. Of the 38
files previously blocked by WRITE with ON ERROR, 34 now pass and four
reach later diagnostics.

- [x] Implement sequential block I/O with READBLK and WRITEBLK. Check
  byte counts, file position, end of file, and writes without automatic
  newlines. Verify the reference grammar's SETTING and conditional arms.

After READBLK and WRITEBLK, 16,085 of 17,336 candidates pass strict C99
checking. All 16,077 previous passes still pass. Eight of the nine
block I/O blockers now pass. TK.TELEKURS.1 advances to STATUS() in
its READBLK error arm.

- [x] Implement STATUS() for the result of the latest supported file I/O.
  Distinguish the function from the STATUS statement and verify its value
  inside success and failure arms, including when SETTING is omitted.

After STATUS(), 16,125 of 17,336 candidates pass strict C99 checking.
All 16,085 previous passes still pass. The 40 additional passes formerly
stopped on a line containing STATUS(). Native tests exercise file I/O
results. STATUS() for conversions still needs coverage.

- [x] Implement SEQ for first-byte values and investigate the SEQX
  spelling used by T24. Verify ASCII, high bytes, and extraction from a
  READBLK buffer. TK.TELEKURS.1 calls SEQX while decoding a length.

After SEQ, 16,129 of 17,336 candidates pass strict C99 checking. All
16,125 previous passes still pass. The four new passes include the
T24 SEQX function, which uses INDEX with a character table or calls
SEQ in UTF-8 mode. TK.TELEKURS.1 already parsed the SEQX calls and first
stops at ASCII on line 64.

- [x] Implement ASCII and EBCDIC byte conversions. Identify the
  reference character mapping, verify the guide's byte example and a
  round trip, and check TK.TELEKURS.1 again.

After ASCII and EBCDIC, 16,131 of 17,336 candidates pass strict C99
checking. All 16,129 previous passes still pass. TK.TELEKURS.1 and
AUTOCASH.INTERFACE now pass. The guide's example works with IBM CP037.
The exact reference table is unspecified, so jbcc provisionally uses
CP037 and ISO-8859-1. Native tests verify both directions and round trips
for every nonzero byte.

- [x] Implement SPACES for scalar counts and dynamic arrays. Check
  delimiter preservation, zero counts, and the guide's empty-element
  diagnostic. CONVERT.ASCII.EBCDIC first stops at SPACES(255) when
  initializing the table used by SEQX.

After SPACES, 16,133 of 17,336 candidates pass strict C99 checking.
All 16,131 previous passes still pass. ATM.BALANCE.UPLOAD.USW and
CONVERT.ASCII.EBCDIC now pass. A local native probe linked the T24 SEQX
and CONVERT.ASCII.EBCDIC routines, initialized their shared startup flags,
and verified the 255-byte table and lookup results for ASCII A and @FM.

- [x] Implement NEGS for element-wise negation using NEG's numeric
  conversion. Check marks, empty elements, and nonnumeric input
  against the guide, whose prose and empty-element example differ.
  Five T24 files first stop on a line containing NEGS.

After NEGS, 16,138 of 17,336 candidates pass strict C99 checking.
All 16,133 previous passes still pass. All five files blocked on NEGS
now pass. Native fixtures preserve empty elements per the jBASE reference
and test precision, delimiters and warnings for nonnumeric elements.

- [x] Implement the REMOVE function in expressions. The reference
  grammar accepts `REMOVE(array, delimiterCode)`, and T24 uses it in
  assignments and loop headers. Check whether the expression and
  statement forms share a cursor, and verify exhaustion and resetting
  the cursor by reassigning the source. Thirteen files first stop on
  a line containing a REMOVE call.

After the REMOVE function, 16,148 of 17,336 candidates pass strict C99
checking. All 16,138 previous passes still pass. Ten of the thirteen
files that first stopped on a REMOVE call now pass. Native tests check
shared cursors, copy and reassignment behavior, delimiter codes, and
exhaustion.

- [x] Implement INMAT with and without a matrix argument. Verify the
  element capacity for dimensioned arrays and the result of the most
  recent MATREAD or MATPARSE, including overflow. Nine files first
  stop on a line containing INMAT.

After INMAT, 16,155 of 17,336 candidates pass strict C99 checking.
All 16,148 previous passes still pass. Seven of the nine files blocked
on INMAT now pass. Native tests cover the dimension vector, counts
after MATREAD, MATREADU and MATPARSE, and overflow.

- [x] Implement DIV for scalar division. Reuse the existing arithmetic
  runtime and test fractional quotients, PRECISION, empty operands,
  and zero divisors. Nine files first stop on a line containing DIV.

After DIV, 16,164 of 17,336 candidates pass strict C99 checking.
All 16,155 previous passes still pass, and all nine files first blocked
on a line containing DIV now pass. Native tests cover quotients, explicit
PRECISION, empty operands, and source-located errors.

- [x] Implement EXTRACT with two to four arguments using the same
  dynamic-array access as angle brackets. Six T24 files first stop on
  a line containing EXTRACT. Test field, value and subvalue selection,
  missing components and source-located diagnostics for invalid indices.

After EXTRACT, 16,170 of 17,336 candidates pass strict C99 checking.
All 16,164 previous passes still pass, and all six files first blocked
on a line containing EXTRACT now pass. Native tests cover component
selection, trailing zero indices, missing components and diagnostics.

- [x] Implement ADDS for element-wise addition. Reuse the runtime's
  array cursor and arithmetic. Check mark alignment, missing versus
  empty elements, PRECISION and scalar REUSE. Six T24 files first stop
  on a line containing ADDS.

After ADDS, 16,174 of 17,336 candidates pass strict C99 checking.
All 16,170 previous passes still pass. Four of the six files with ADDS
on their original failing line now pass. The other two stop at MULS.
Native tests cover mixed marks, empty and unmatched positions, decimal
precision, scalar REUSE and call-site diagnostics.

- [x] Implement MULS for element-wise multiplication. Reuse the ADDS
  traversal, return zero for an unmatched element and propagate paired
  empty elements as in the guide. Check PRECISION and scalar REUSE.
  Eight T24 files first stop on a line containing MULS.

After MULS, 16,179 of 17,336 candidates pass strict C99 checking.
All 16,174 previous passes still pass. Five of the eight files that
first stopped on a line containing MULS now pass. The other three reach
DIVS. Native tests cover mixed marks, unmatched positions, empty pairs,
scalar REUSE, decimal precision and overflow.

- [ ] Implement DIVS for element-wise division. Reuse the array arithmetic
  traversal and check asymmetric padding, empty pairs, PRECISION, scalar
  REUSE and the guide's zero-divisor diagnostic and result. Four T24
  files first stop on a line containing DIVS.
