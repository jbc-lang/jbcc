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

- [x] Implement DIVS for element-wise division. Reuse the array arithmetic
  traversal and check asymmetric padding, empty pairs, PRECISION, scalar
  REUSE and the guide's zero-divisor diagnostic and result. Four T24
  files first stop on a line containing DIVS.

After DIVS, 16,181 of 17,336 candidates pass strict C99 checking.
All 16,179 previous passes still pass. Two of the four files that first
stopped on a line containing DIVS now pass. The other two reach SUBS.
Native tests cover asymmetric padding, empty pairs, scalar REUSE,
decimal precision, and reporting zero divisors while completing the array.

- [x] Implement SUBS for element-wise subtraction. Check the guide's
  use of zero for empty and missing elements, mixed marks, PRECISION,
  scalar REUSE and invalid operands. Three T24 files first stop on a
  line containing SUBS.

After SUBS, 16,184 of 17,336 candidates pass strict C99 checking.
All 16,181 previous passes still pass, and all three targeted files
now pass. Native tests cover zero padding, mixed marks, scalar REUSE,
decimal precision, nonnumeric operands and overflow.

- [x] Implement the `@USERNO` port number and the reference compiler's
  `@USER_NO` and `@UDTNO` aliases. Check their relationship to
  `SYSTEM(18)` and document how a native process gets its port number.
  Unsupported `@USERNO` is the first diagnostic in 35 T24 files.

After the port number support, 16,209 of 17,336 candidates pass strict
C99 checking. All 16,184 previous passes still pass. Of the 35 files
previously blocked on `@USERNO`, 25 now pass and 10 reach other diagnostics.
Native tests verify startup overrides, aliases, `SYSTEM(18)`, the process
ID fallback and diagnostics for malformed settings.

- [x] Implement `@WHO` for the login name. Check its relationship to
  `SYSTEM(19)` and the guide's login-name override before choosing the
  native fallback. Unsupported `@WHO` is the first diagnostic in 18 T24
  files.

After `@WHO`, 16,223 of 17,336 candidates pass strict C99 checking.
All 16,209 previous passes still pass. Of the 18 files blocked on
`@WHO`, 14 now pass and four reach other diagnostics. Native tests
check `SYSTEM(19)`, override precedence, startup capture and the
POSIX user database fallback.

- [x] Implement `@LOGNAME` and `@ACCOUNT`. The reference compiler maps
  both to the same account lookup. Cross-check jBC account naming and
  test the native fallback. These names are the first diagnostic in
  16 T24 files.

After account-name support, 16,234 of 17,336 candidates pass strict C99
checking. All 16,223 previous passes still pass. Of the 16 targeted
files, 11 now pass and five reach later diagnostics. Native tests cover
both aliases, startup override precedence, and the `@WHO` fallback.

- [x] Implement `@SELECTED` for the number of elements in the most
  recent default external select list. Verify which operations update
  it, including selection into named lists, and test its interaction
  with READNEXT and CLEARSELECT. Unsupported `@SELECTED` is the first
  diagnostic in nine T24 files.

After `@SELECTED`, 16,240 of 17,336 candidates pass strict C99 checking.
All 16,234 previous passes still pass. Six of the nine targeted files
now pass and three reach later diagnostics. Native tests use WRITELIST
to populate the default external list and check count persistence
through list traversal, clearing and subroutine calls.

- [x] Implement `@ID` as a record-context variable. The reference
  compiler accepts assignment to it. Check its initial value and
  which statements can write to it, including `READNEXT @ID`.
  Unsupported `@ID` is the first diagnostic in eight T24 files.

After `@ID`, 16,248 of 17,336 candidates pass strict C99 checking.
All 16,240 previous passes still pass, and all eight targeted files
now pass. Native tests cover explicit assignment, READNEXT in statements
and expressions, list exhaustion and sharing across routine calls.

- [x] Implement COMPARE with default, left and right justification.
  Check string ordering, differing lengths, and the guide's TAFC/TAFJ
  discrepancy for right justification. Seven T24 files first stop on
  a line containing COMPARE.

After COMPARE, 16,255 of 17,336 candidates pass strict C99 checking.
All 16,248 previous passes still pass, and all seven targeted files
now pass. Native tests cover byte ordering, alignment, empty strings
and invalid justification. Right justification follows the guide's
TAFJ result using the same left padding as LOCATE.

- [x] Implement DROUND with the guide's four-place default and an
  explicit precision. Check midpoint and negative values, and verify
  the interaction with PRECISION. Six T24 files first stop on a line
  containing DROUND.

After DROUND, 16,261 of 17,336 candidates pass strict C99 checking.
All 16,255 previous passes still pass, and all six targeted files
now pass. Native tests cover default and explicit precision, midpoint
ties, carry, and values with more than 15 fractional digits.

- [x] Implement BYTELEN using the existing byte length operation.
  Check empty strings, multibyte text and dynamic-array marks. Five
  T24 files first stop on a line containing BYTELEN.

After BYTELEN, 16,264 of 17,336 candidates pass strict C99 checking.
All 16,261 previous passes still pass. Three of the five targeted files
now pass, and the other two reach FLUSH and DATA. Native tests cover
empty input, UTF-8, and single-byte array marks.

- [x] Implement FLUSH for sequential files. Verify visibility of writes
  before closing the handle, THEN and ELSE branches, and the behavior
  before a file has been created. Unsupported FLUSH is the first
  diagnostic in seven T24 files.

After FLUSH, 16,271 of 17,336 candidates pass strict C99 checking.
All 16,264 previous passes still pass, and all seven targeted files
now pass. Native tests cover an external reader before CLOSESEQ,
pending and empty handles, and status reporting.

- [x] Implement DATA for queued terminal input. Check FIFO order,
  field-mark separation, fallback to terminal input, and how queued
  input passes through EXECUTE. Unsupported DATA is the first
  diagnostic in seven T24 files.

After DATA, 16,278 of 17,336 candidates pass strict C99 checking.
All 16,271 previous passes still pass, and all seven targeted files
now pass. Native tests cover FIFO order, field marks, limited INPUT,
stdin fallback and command handoff. A child receiving queued input
sees EOF after those lines.

- [x] Implement FILEINFO for the selectors used by T24. Verify file
  handle validity and the documented meaning of key 2 before choosing
  a native representation. Five T24 files first stop on a line
  containing FILEINFO.

After FILEINFO, 16,283 of 17,336 candidates pass strict C99 checking.
All 16,278 previous passes still pass, and all five targeted files
now pass. Native tests cover valid, pending, failed and closed handles,
the pathname selector, and diagnostics for unsupported keys.

- [x] Implement `@DATE` using the guide's startup date semantics.
  Share the internal date conversion with DATE() and verify
  that routines see the startup date. Unsupported `@DATE` is the first
  diagnostic in five T24 files.

After `@DATE`, 16,284 of 17,336 candidates pass strict C99 checking.
All 16,283 previous passes still pass. One of the five targeted files
now passes, and the other four reach `@TIME`. A native test verifies
that a called routine sees the startup date after local midnight.

- [x] Implement `@TIME` using the same startup clock snapshot as
  `@DATE`. Check seconds since midnight and compare with TIME() across
  local midnight. Unsupported `@TIME` is the first diagnostic in six
  T24 files.

After `@TIME`, 16,289 of 17,336 candidates pass strict C99 checking.
All 16,284 previous passes still pass. Five of the six targeted files
now pass. The native midnight test covers the shared startup clock
when either variable is used alone and when both are read together.

- [x] Implement `ASSIGN value TO SYSTEM(key)` syntax. Identify the
  keys used by T24 and verify which native runtime state can be updated.
  Report unavailable services at the call site. Unsupported ASSIGN is
  the first diagnostic in five T24 files.

After ASSIGN, 16,293 of 17,336 candidates pass strict C99 checking.
All 16,289 previous passes still pass. Four of the five targeted files
now pass, and one reaches `@USERSTATS`. Native tests cover the lock
counter reset, retained locks and diagnostics for unavailable keys.

- [x] Implement RECORDLOCKU using the in-memory record lock backend.
  Verify successful acquisition, contention, release and the new
  SYSTEM(1036) counter. Unsupported RECORDLOCKU is the first
  diagnostic in three T24 files.

After RECORDLOCKU, 16,296 of 17,336 candidates pass strict C99 checking.
All 16,293 previous passes still pass, and all three targeted files
now pass. Native tests cover reservation of an unused key, default
files, simulated contention, status, and release.

- [x] Implement the underscore length modifier in `INPUT X,1_` and
  `INPUT X,1_:`. Check when input terminates, how excess bytes are
  handled, and interaction with queued DATA. Nine T24 files first
  stop at this modifier.

After the INPUT underscore modifier, 16,304 of 17,336 candidates pass
strict C99 checking. All 16,296 previous passes still pass. Seven of the
nine files with an unexpected underscore now pass, along with LOAD.FILE,
whose colon-before-underscore form originally reached an expression
diagnostic. The other two reach REWIND. Native tests cover piped input,
queued DATA, terminal bells and waiting for Enter.

- [x] Implement ECHO ON, ECHO OFF and its expression form. Verify
  terminal behavior, interaction with HUSH, and the guide's SYSTEM
  query for echo state. Unsupported ECHO is the first diagnostic
  in two T24 files.

After ECHO, 16,305 of 17,336 candidates pass strict C99 checking.
All 16,304 previous passes still pass. One targeted file now passes
and the other reaches INPUTCLEAR. A pseudo-terminal test covers
character echo, SYSTEM(24), HUSH and terminal mode restoration.

- [x] Implement INPUTCLEAR and its CLEARINPUT alias. Verify that it
  clears terminal type-ahead while preserving queued DATA. Unsupported
  INPUTCLEAR is the first diagnostic in one T24 file.

After INPUTCLEAR, 16,306 of 17,336 candidates pass strict C99 checking.
All 16,305 previous passes still pass, and EDIT.CMD.LINE now passes.
Native tests cover both spellings, complete and partial terminal
type-ahead, queued DATA, and stdin from a pipe.

- [x] Implement FOOTING using the existing report pagination and
  heading options. Check page breaks, printer output and terminal
  pauses. Unsupported FOOTING is the first diagnostic in two T24 files.

After FOOTING, 16,308 of 17,336 candidates pass strict C99 checking.
All 16,306 previous passes still pass. ENQUIRY.HARDCOPY and FILE.UTILITY
now pass as well. Native tests cover footer
line reservation, outgoing page numbers, printer close, normal exit,
and terminal pauses with and without the N option.

- [x] Implement FOLD for width-limited wrapping into attribute-marked
  text. Check word boundaries, long words, whitespace and invalid widths.
  Two T24 files first stop on a line containing FOLD.

After FOLD, 16,310 of 17,336 candidates pass strict C99 checking.
All 16,308 previous passes still pass, and both targeted files now
pass. Native tests cover word boundaries, long words, zero width,
spaces and existing field marks.

- [x] Implement FMTS by applying FMT to each dynamic-array element.
  Check mixed marks, empty elements, expanding output and malformed
  masks. Two T24 files first stop on a line containing FMTS.

After FMTS, 16,312 of 17,336 candidates pass strict C99 checking.
All 16,310 previous passes still pass, and both targeted files now
pass. Native tests cover existing FMT masks, mixed marks, empty
elements and diagnostics. Both newly translated units use a `T` mask.

- [x] Implement width-prefixed `T` masks for FMT and FMTS. Check
  word boundaries, padding and text-mark separation against the
  guide, then run a native example like the T24 narrative calls.

All 16,312 of the previous strict C99 passes still pass after adding
`T` masks. A native fixture follows the T24 narrative call pattern and
checks word breaks, padding, text marks, and value-mark preservation.

- [x] Implement ABSS using the runtime's decimal absolute value and
  dynamic-array traversal. Check empty elements, marks, precision,
  and invalid input. Two T24 files first stop on a line containing ABSS.

After ABSS, 16,314 of 17,336 candidates pass strict C99 checking.
All 16,312 previous passes still pass, and both targeted files now
pass. Native tests cover large magnitudes, empty elements, marks,
PRECISION and invalid elements.

- [x] Implement SMUL for decimal-string multiplication. Check large
  products, signs, fractional precision and the reference grammar's
  optional precision argument. Two T24 files first stop on a line
  containing SMUL.

After SMUL, all 16,314 previous strict C99 passes still pass out of
17,336 candidates. The two targeted files now reach nested SDIV calls.
Native tests reproduce both guide examples and check signs, optional
precision and source-located diagnostics.

- [x] Implement SDIV for decimal-string division. Check the guide's
  14-place examples, its rounding description, the reference grammar's
  optional precision argument, and division by zero. Rerun the two T24
  files that now reach SDIV.

After SDIV, 16,316 of 17,336 candidates pass strict C99 checking.
All 16,314 previous passes still pass, and both targeted files now
pass. Native tests reproduce the guide examples and check explicit
precision, large operands and source-located diagnostics.

- [x] Implement REWIND for tape channels. Check the guide and the
  grammar's optional unit and channel forms, and exercise the documented
  no-media status and ELSE branch. Four T24 files first stop at REWIND.

After REWIND, the same 16,316 of 17,336 candidates pass strict C99
checking. Two targeted files now reach READT and two reach WRITET.
Native tests cover both conditional arms, the unit and channel forms,
and the no-media status. The runtime has no attached tape devices.

- [x] Implement READT for tape records. Check the guide and reference
  grammar for channel selection and failed reads, then reuse the
  no-media status from REWIND. Five T24 files first stop at READT.

After READT, 16,319 of 17,336 candidates pass strict C99 checking.
All 16,316 previous passes still pass. Three targeted files now pass,
and the remaining two reach WRITET. Native tests check scalar and matrix
destinations, channel selection, and no-media status.

- [x] Implement WRITET for tape records. Check the guide's ON and TO forms
  and the reference grammar's UNIT and FROM forms. Verify the no-media
  status and conditional arms. Four T24 files first stop at WRITET.

After WRITET, 16,321 of 17,336 candidates pass strict C99 checking.
All 16,319 previous passes still pass. Two targeted files now pass,
and the other two reach WEOF. Native tests cover the channel forms,
no-media status and source-located errors.

- [x] Implement WEOF for tape end-of-file marks. Check the reference
  grammar's conditional arms and unit and channel forms. Verify the
  no-media path and rerun the three T24 files that first stop at WEOF.

After WEOF, 16,324 of 17,336 candidates pass strict C99 checking.
All 16,321 previous passes still pass, and all three targeted files
now pass. Native tests cover conditional arms, channel selection and
precedence, and the no-media status.

- [x] Implement @TTY for the terminal port name. Verify a native run
  with a pseudoterminal and define the fallback for redirected input
  using the guide and reference runtime evidence. Four T24 files
  first stop at @TTY.

After @TTY, 16,328 of 17,336 candidates pass strict C99 checking.
All 16,324 previous passes still pass, and all four targeted files
now pass. A native test checks a pseudoterminal and redirected input.

- [x] Implement @PID for the current process ID. Check that it matches
  the native process ID when JBCPORTNO overrides @USERNO. Two T24 files
  first stop at @PID.

After @PID, 16,329 of 17,336 candidates pass strict C99 checking.
All 16,328 previous passes still pass. JF.INITIALISE.CONNECTION now
passes, and tSS reaches DEBUG. A native test compares the value with
the launched process ID while JBCPORTNO supplies a separate port.

- [x] Implement DEBUG statement parsing and define the native behavior
  when no jBC debugger is available. Verify conditional execution
  and source-located diagnostics. Six T24 files first stop at DEBUG.

After DEBUG, 16,334 of 17,336 candidates pass strict C99 checking.
All 16,329 previous passes still pass. Five targeted files now pass,
and ENQ.REAL.TIME.PUSH reaches NOBUF. Native verification checks the
diagnostic only when execution reaches the statement.

- [x] Implement NOBUF for open sequential files. Check SETTING and
  conditional arms against the reference grammar, and verify that
  writes become visible before the handle closes. Three T24 files
  first stop at NOBUF.

After NOBUF, the same 16,334 of 17,336 candidates pass strict C99
checking. Two targeted files reach TIMEOUT, and one reaches TTYGET.
A native test checks read-ahead and write visibility while the handle
is still open. Another checks statuses and the error location.

- [x] Investigate TIMEOUT for sequential reads. Check the time unit,
  handle validation and timeout status against the guide. Verify how
  it applies to the regular-file backend. Four T24 files first stop
  at TIMEOUT.

After TIMEOUT, 16,336 of 17,336 candidates pass strict C99 checking.
All 16,334 previous passes still pass. Two targeted files now pass,
and the two ATM files reach ICONVS. Native tests check validation
and immediate regular-file reads and EOF.

- [x] Implement ICONVS using scalar ICONV on dynamic-array elements.
  Check the guide's treatment of empty elements, marks, and conversion
  status. Four T24 first-diagnostic lines contain ICONVS calls.

After ICONVS, 16,339 of 17,336 candidates pass strict C99 checking.
All 16,336 previous passes still pass. Three ATM files now pass and
LI.SECURED.ONLINE reaches OCONVS. Native tests cover the MT and MTS
input conversions, empty elements, chained masks and statuses.

- [x] Implement OCONVS using scalar output conversion on dynamic-array
  elements. Check which result and status the guide specifies for an
  invalid element, and rerun LI.SECURED.ONLINE.

After OCONVS, the same 16,339 of 17,336 candidates pass strict C99
checking. LI.SECURED.ONLINE now reaches REUSE as an infix multiplication
operand. Native tests cover date and time masks, chained conversion,
and preservation of invalid elements and array marks.

- [x] Investigate infix multiplication with REUSE. Check the reference
  grammar and runtime generator, and test scalar reuse across the marks
  of a dynamic array before rerunning LI.SECURED.ONLINE.

After infix multiplication with REUSE, 16,341 of 17,336 candidates
pass strict C99 checking. All 16,339 previous passes still pass.
LI.SECURED.ONLINE and MG.PERFORM.ACCRUALS now pass.
Native tests cover scalar reuse on either side, expression precedence,
mixed array marks and an invalid array inside REUSE.

- [x] Investigate the @USER.NO spelling in T24 and its relationship to
  @USERNO and SYSTEM(18). Three T24 files first stop at @USER.NO.

After @USER.NO, 16,343 of 17,336 candidates pass strict C99 checking.
All 16,341 previous passes still pass. JBASE.COMPILE and
PERFORM.GLOBUS.RELEASE now pass. T24.INITIALISE reaches CALLONEXIT.
Native tests check the configured port and process ID fallback.

- [x] Investigate CALLONEXIT. Check callback lookup, value-mark arguments
  and registration order against the guide, then rerun T24.INITIALISE.

After CALLONEXIT, the same 16,343 of 17,336 candidates pass strict C99
checking. T24.INITIALISE reaches a duplicate declaration of FWC in
I_IO.EQUATE. Native tests cover linked callback lookup, registration
order, value-mark arguments and runtime-controlled termination.

- [x] Trace the duplicate FWC declaration in the T24.INITIALISE
  include chain. Check how the reference compiler handles the two
  declarations before changing COMMON or include behavior.

T24.INITIALISE includes I_IO.EQUATE twice. The reference parser keeps
the COMMON slot when a matrix is declared again in the same block.
Its dynamic-dimension generator handles repeated declarations. jbcc
reuses the slot and validates shape at compile time or runtime.

After this change, 16,352 of 17,336 candidates pass strict C99
checking. All 16,343 previous passes still pass. Nine additional
files pass, including T24.INITIALISE. Native tests verify that
repeated includes still execute each time and preserve linked COMMON
layout and matrix contents.

- [x] Investigate @RECORD. Trace how the reference runtime exposes
  the current record and whether it shares state with @ID. Two T24
  files first stop at @RECORD.

After @RECORD, 16,356 of 17,336 candidates pass strict C99 checking.
All 16,352 previous passes still pass. The two targeted files and
two callers that include @RECORD code now pass. Native tests check
assignment, record reads, and preservation across loop cleanup and
subroutine calls. @ID and @RECORD hold independent values.

- [x] Implement @PATH for the current account path. Check how the
  reference defines it and verify the native result from a different
  working directory. One T24 file first stops at @PATH.

After @PATH, 16,357 of 17,336 candidates pass strict C99 checking.
All 16,356 previous passes still pass. MWT.DUMP.FILE now passes.
The native test checks a working directory longer than the starting
buffer size and supplies unrelated HOME and PWD values.

- [x] Implement @LPTRHIGH using the current output device's line count.
  Check terminal and printer behavior against the guide and the report
  runtime. One T24 file first stops at @LPTRHIGH.

After @LPTRHIGH, 16,358 of 17,336 candidates pass strict C99 checking.
All 16,357 previous passes still pass, and ENQ.PRE.PROCESS now passes.
Native verification checks terminal geometry, the redirected-output
fallback and the selected printer unit.

- [x] Investigate @TERM.TYPE, @TERM_TYPE and @TERMTYPE. Compare the
  guide, reference compiler and T24 spelling, and verify the native
  result with TERM set and unset. One T24 file first stops at @TERM.TYPE.

After the terminal type aliases, 16,359 of 17,336 candidates pass
strict C99 checking. All 16,358 previous passes still pass.
TT.DEAL.SLIP.PRINT now passes. Native tests check populated, empty,
and unset TERM values and a change made by PUTENV.

- [x] Implement @SYS.BELL and check the reference spelling @SYS_BELL.
  Verify the bell byte in native output and rerun ONSITE.LIVE.RELEASE.

After the bell aliases, 16,360 of 17,336 candidates pass strict C99
checking. All 16,359 previous passes still pass, and ONSITE.LIVE.RELEASE
now passes. The native fixture checks the emitted bytes and their
sequence numbers.

- [x] Implement CLEARDATA to discard queued DATA. Check the guide and
  verify that later INPUT can consume new DATA or standard input.
  ENQ.PH.INIT first stops at CLEARDATA.

After CLEARDATA, 16,361 of 17,336 candidates pass strict C99 checking.
All 16,360 previous passes still pass, and ENQ.PH.INIT now passes.
A native test checks clearing a partially consumed entry, the remaining
queue, and later reads from standard input and fresh DATA.

- [x] Count queued DATA in SYSTEM(14). Check the guide's CLEARDATA
  example, partial INPUT reads, and existing counts for piped input.

After the SYSTEM(14) change, the same 16,361 of 17,336 candidates pass
strict C99 checking. Native tests check remaining queued bytes, line
endings, and pending standard input before and after CLEARDATA.

- [x] Implement OSREAD for regular files. Check result and error arms
  against the guide, and rerun UPDATE.UPLOAD.SERVICE.

After OSREAD, 16,362 of 17,336 candidates pass strict C99 checking.
All 16,361 previous passes still pass, and UPDATE.UPLOAD.SERVICE now
passes. Native tests cover path search, reading across a buffer
boundary, NUL replacement, the final LF, and failure arms.

- [x] Investigate OSOPEN for regular files and its relationship to
  OSBREAD, OSBWRITE, and OSCLOSE. Two T24 files first stop at OSOPEN.

After OSOPEN and OSCLOSE, 16,364 of 17,336 candidates pass strict C99
checking. All 16,362 previous passes still pass, and both targeted
files now pass. The reference lexer maps these statements to OPENSEQ
and CLOSESEQ. Native tests check shared handles, access modes, path
search and error arms.

- [x] Implement OSBREAD on an open OS file handle. Check byte offsets,
  short reads, cursor position and NUL conversion against the guide
  and verify the behavior with an OSOPEN fixture.

After OSBREAD, the same 16,364 of 17,336 candidates pass strict C99
checking. Native tests verify explicit offsets, continued reads,
cursor position, short reads, NUL conversion and failure handling.

- [x] Implement OSBWRITE on an open OS file handle. Check offset and
  cursor behavior, byte 128 conversion and error handling, then
  verify a native OSBWRITE and OSBREAD round trip.

After OSBWRITE, the same 16,364 of 17,336 candidates pass strict C99
checking. Native tests compare the exact file bytes after writes,
read them back through OSBREAD, and check cursor movement, sparse
extension, and invalid or read-only handles.

- [x] Implement OSWRITE for whole regular files. Check replacement,
  APPEND, byte conversion, status, and error handling against the guide.

After OSWRITE, the same 16,364 of 17,336 candidates pass strict C99
checking. Native tests cover creation, truncation, append, path
lookup, exact byte conversion and error handling. They verify that
a locked file keeps its original contents.

- [x] Implement OSDELETE for OS files. Check path resolution,
  missing files and the reference error arms using temporary fixtures.

After OSDELETE, the same 16,364 of 17,336 candidates pass strict C99
checking. Native tests cover explicit paths, working directory precedence,
`JEDIFILEPATH` fallback, directories, status and error arms.

- [x] Implement OPENDEV for regular files using the reference lexer's
  OPENSEQ alias. Check native file access and the LOCKED and ELSE arms,
  and identify what the device cases need from the runtime.

After OPENDEV, the same 16,364 of 17,336 candidates pass strict C99
checking. Both units that stopped at OPENDEV now reach TTYGET. Native
tests cover file position, reads and writes, the missing-file branch,
and lock contention with and without a LOCKED clause. The regular-file
backend reports an I/O error for a named pipe.

- [x] Implement TTYGET for POSIX terminal handles. Check the reference
  grammar and field positions used by T24. Verify the supported fields
  with a pseudo-terminal and check the failure path on regular files.

After TTYGET, the same 16,364 of 17,336 candidates pass strict C99
checking. All three units that stopped at TTYGET now reach TTYSET.
Native tests query canonical and noncanonical settings from a
pseudo-terminal and verify the error branches for regular files and
closed handles. The initial field mapping covers mode, echo, baud,
data bits, stop bits, parity and selected signal options.

- [x] Implement TTYSET for POSIX terminal handles. Check which edits
  the three blocked T24 units make, define handling for unsupported
  fields, and verify a TTYSET and TTYGET round trip on a pseudo-terminal.

After TTYSET, 16,366 of 17,336 candidates pass strict C99 checking.
Two new units pass, all previous passes still pass, and the third unit
that stopped at TTYSET now reaches BREAK OFF.
Native tests apply supported settings, read them back and restore them
on a pseudo-terminal. They also verify that invalid requests and
populated unsupported fields leave the terminal settings intact.
The T24 callers also request control characters, carrier and newline
flags, delay fill and signal flushing. Those fields still need a
runtime mapping before those calls can succeed.

- [x] Implement BREAK ON and BREAK OFF for terminal interrupts.
  A pseudo-terminal test sends the actual interrupt character in
  both modes and verifies bare loop BREAK in the same program.

After BREAK ON/OFF, the same 16,366 of 17,336 candidates pass strict
C99 checking. The targeted unit now reaches a substring assignment.

- [x] Implement single-index substring assignment. Check the
  reference grammar and code generator for `value[length] = text`,
  and verify how it replaces bytes at the end of a string. One T24
  unit reaches this form after BREAK OFF.

After single-index substring assignment, 16,377 of 17,336 candidates
pass strict C99 checking. Eleven new units pass and all previous
passes still pass. Native tests cover replacement and concatenation on
scalars, matrix elements and dynamic-array fields, including empty and
oversized selections. The reference generator treats the index as a length.

- [x] Implement BITXOR. Check operand coercion, empty values and the
  integer width against the guide, then verify a native bitwise
  calculation. The targeted unit reaches BITXOR after the assignment.

After BITXOR, 16,378 of 17,336 candidates pass strict C99 checking.
DE.SWIFT.LINE.HANDLER now passes and all previous passes still pass.
Native tests cover the guide example, fractional and empty operands,
signed 32-bit results, wrapping and diagnostics.

- [x] Implement COL1() and COL2() for FIELD positions. Verify the guide
  examples and check how positions reset on a missing field. Two T24
  units use COL2() inside substring assignment.

After COL1 and COL2, 16,381 of 17,336 candidates pass strict C99
checking. Three new units pass, including both targeted units, and
all previous passes still pass. Native tests cover scalar FIELD and
bracket syntax, multiple fields, multi-byte delimiters, empty fields,
and missing occurrences.

- [x] Implement EXEC as an EXECUTE alias. Check the reference
  grammar's Prime and UniVerse forms and verify the existing native
  execution behavior through the alias. Two T24 units stop at EXEC.

After EXEC, 16,382 of 17,336 candidates pass strict C99 checking.
HOST.TO.DOS now passes, and SC.INTEGRITY.RUN reaches a later expression.
All previous passes still pass. Native tests cover command output,
exit status, capture and result clauses, and duplicate-clause diagnostics.

- [x] Implement the RANDOMIZE compatibility statement. Check the
  reference parser's forms and whether the seed affects RND. Verify the
  native behavior and recheck the T24 unit blocked by this statement.

After RANDOMIZE, 16,383 of 17,336 candidates pass strict C99 checking.
CHECK.SPF now passes and all previous passes still pass. The reference
parser discards the optional argument. Native tests cover all three
forms, skipped argument evaluation, RND bounds and the diagnostic for
an extra argument.

- [x] Implement standalone increment and decrement statements. The
  reference grammar allows prefix and postfix forms on scalar and
  matrix element targets. Two T24 units first stop at postfix increment.

After standalone increment and decrement, 16,396 of 17,336 candidates
pass strict C99 checking. Thirteen new units pass and all previous
passes still pass. EB.GET.RECORD.XML now reaches a spaced `: =`
assignment. Native tests cover both spellings in each position, scalar
and matrix targets, and diagnostics for invalid targets and overflow.

- [x] Implement increment and decrement in expressions. Verify the
  guide's old-value and new-value examples, matrix element targets,
  and evaluation order when the variable is used twice.

After increment and decrement expressions, the same 16,396 of 17,336
candidates pass strict C99 checking. Native tests cover prefix and postfix
results, left-to-right operand evaluation, short-circuiting and matrix
elements used as call arguments.

- [x] Accept spaced concatenating assignment (`: =`). The
  reference lexer spells this operator `:=`, while EB.GET.RECORD.XML
  uses the spaced form. Native tests cover spaces and tabs, scalar and
  indexed targets, labels, and ordinary concatenation and comparison.

After spaced concatenating assignment, 16,412 of 17,336 candidates
pass strict C99 checking. Sixteen new units pass, including
EB.GET.RECORD.XML, and all previous passes still pass.

- [x] Implement the LOCKED clause on CLEARFILE. The reference parser
  accepts it after ON ERROR. Native tests verify contention and record
  preservation, the previous error path, and a successful clear.

After CLEARFILE LOCKED, 16,414 of 17,336 candidates pass strict C99
checking. Both units blocked at LOCKED now pass, and all previous
passes still pass.

- [x] Implement DISPLAY as a CRT alias following the reference lexer.
  Verify terminal output and formatting through the alias. One T24
  unit stops at DISPLAY.

After DISPLAY, 16,415 of 17,336 candidates pass strict C99 checking.
ATP.DATA.POPULATE now passes and all previous passes still pass.
Native tests cover formatting, tab separation, newline suppression
and output routing with a printer active.

- [x] Implement GET (ARG.) for program arguments. Check the reference
  forms with and without an index and conditional arms, then verify
  how they map to native argv. One T24 unit stops at GET (ARG.).

After GET (ARG.), 16,416 of 17,336 candidates pass strict C99 checking.
VIB now passes and all previous passes still pass. Native tests cover
arguments containing spaces, empty arguments, indexed and sequential
reads, the shared cursor across routines, and missing arguments.

- [x] Implement a native @USERSTATS snapshot. Use the field numbers
  from JBC.h to expose process identity, invocation and the successful
  record-write count used by BATCH.JOB.CONTROL.

After @USERSTATS, 16,417 of 17,336 candidates pass strict C99 checking.
BATCH.JOB.CONTROL now passes and all previous passes still pass.
Native tests compare process data with the launched executable and
verify the write counter across successful writes and a lock conflict.

- [x] Add the OPEN and READ counters to @USERSTATS. Check which record
  operations contribute, verify the guide's snapshot-and-difference
  pattern on the in-memory backend, and cover lock and missing cases.

The same 16,417 of 17,336 candidates pass strict C99 checking.
Native tests compare snapshots around successful opens and reads.
They cover each supported read variant, empty fields, missing records
and foreign locks.

- [x] Add the DELETE and CLEARFILE counters to @USERSTATS. Check the
  cases of a missing record and an already empty file, and verify
  counter deltas around successful operations and lock conflicts.

The same 16,417 of 17,336 candidates pass strict C99 checking.
Native tests verify that successful statements count even when there
are no records to remove. Invalid descriptors and foreign locks leave
the counters unchanged, and a blocked clear preserves the records.

- [x] Add the EXECUTE and INPUT counters to @USERSTATS. Check which
  execution aliases share a counter and define how child exit status,
  input timeout and end of input affect the totals.

The same 16,417 of 17,336 candidates pass strict C99 checking.
Native tests cover command execution with and without captured streams,
nonzero child exits, queued input, a timeout and end of input.

- [x] Investigate CALLJ syntax from the reference grammar and the seven
  blocked T24 units. Verify a source-located runtime diagnostic for
  calls that require a JVM backend and recheck corpus translation.

The reference grammar and the seven T24 units use three expression
operands, a required SETTING variable and an optional ON ERROR arm.
Native tests verify the diagnostic for a reached call, including one
with an error arm, and verify that a skipped call has no effect.
All seven units now pass strict C99 checking, bringing the total to
16,424 of 17,336 candidates. All 16,417 previous passes still pass.

- [x] Investigate TRANSTART, TRANSEND and TRANSABORT in the guide and
  reference grammar. Add syntax support for the forms in EB.TRANS.JBASE
  and verify the runtime diagnostic when execution requires a transaction
  backend.

The reference grammar requires a conditional arm and accepts an optional
note for each statement. TRANSTART also takes SYNC. Native tests verify
source-located diagnostics for reached calls and cover both inline and
multiline conditional arms.
EB.TRANS.JBASE now passes strict C99 checking, bringing the total to
16,425 of 17,336 candidates. All 16,424 previous passes still pass.

- [x] Trace DIM declarations that reuse an existing COMMON matrix, starting
  with R.NEW in AZ.DEPOSIT.REVERSAL. This is the first diagnostic in
  107 units. Compare the reference compiler's fixed and dynamic dimension
  modes before changing declaration handling.

The fixed-dimension generator rejects a second DIM. The dynamic generator
emits a repeated declaration for the existing COMMON variable. In
AZ.DEPOSIT.REVERSAL, both declarations of R.NEW use C$SYSDIM from I_COMMON.
jbcc accepts the repeated DIM with the same rank and bounds and keeps
the COMMON slot. Native tests check named and unnamed blocks, sharing
across routines, and compile-time and runtime shape mismatches.
The standalone reference compiler crashed in both emulation modes, so
this comparison uses the generator source.

After this change, 16,486 of 17,336 candidates pass strict C99 checking,
including all 16,425 previous passes. Of the 107 units previously blocked
at these declarations, 61 pass, 42 report incompatible COMMON matrix
dimensions, and four reach another diagnostic.

- [x] Trace repeated DIM declarations for local matrices, starting with
  YR.LOCTAB in ARCHIVES.UPDATE.RUN. Check first execution through either
  declaration and verify how the reference generator handles later uses
  of the same local slot.

The reference compiler diagnosed a repeated local DIM in fixed mode.
In Prime mode it emitted two declarations against the same variable,
marking the second as a redeclaration. jbcc keeps one local slot per
invocation and provisionally requires compatible shapes. Native tests
cover first execution through either declaration, preservation of
contents, and compile-time and runtime shape mismatches.

After this change, 16,531 of 17,336 candidates pass strict C99 checking,
including all 16,486 previous passes. Of the 50 units whose result
changed, 45 pass, including ARCHIVES.UPDATE.RUN. Three report
incompatible local matrix dimensions and two reach another diagnostic.

- [x] Trace COMMON matrices whose later DIM supplies different bounds.

All 42 current corpus diagnostics for incompatible COMMON dimensions
involve one-dimensional arrays. The second bound is smaller in 28 units
and larger in 14. REBUILD.AVAIL.FUNDS.LOAD imports R.ACCOUNT(500) through
I_REBUILD.AVAIL.FUNDS.COMMON and dimensions it again at
AC.AUDIT.DATE.TIME, which I_F.ACCOUNT defines as 210. The paired
REBUILD.AVAIL.FUNDS routine uses the same COMMON declaration and passes
R.ACCOUNT as a MAT argument.

The standalone reference compiler crashed because its DIM generator
released the syntax node before the COMMON parser action used it.
Moving that release to the consuming parser actions in a temporary
build let the probe run through code generation. For
`COMMON /EXAMPLE/ A(5)` followed by `DIM A(3)`, fixed mode diagnosed
the second declaration. Prime mode emitted DECLARE_DYN_DIM operations
7 and 8 against the same variable with bounds 5 and 3, respectively.
Growth probes likewise emitted bounds 2 and 5, using operations 7 and
8 for named COMMON and 3 and 4 for unnamed COMMON.
[jBASE emulation documentation](https://docs.rocketsoftware.com/bundle/jbase_lib_59/page/ryu1684869638605.html).

- [ ] Verify shared COMMON resize behavior with the vendor runtime.
  Measure the bound visible to a routine using the original declaration,
  the elements preserved across shrink and grow, and the effect on MAT
  aliases. Keep the shape-mismatch diagnostic until those rules are known.

- [x] Investigate EXECUTE and PERFORM RTNLIST. Check the explicit and
  default output forms and report when the command backend cannot
  return a jBC select list. EBS.CREATE.FILE and WR.MANUAL.REP.INITIALISE
  first stop at RTNLIST.

The guide documents explicit and default destinations. The reference
compiler also accepted numeric and string constants in the operand
position. jbcc accepts these forms in any order with the other supported
clauses. Native tests verify that a reached RTNLIST reports the missing
backend at the statement and the shell command never starts.
Both blocked units now pass strict C99 checking, bringing the total to
16,533 of 17,336 candidates. All 16,531 previous passes still pass.

- [x] Investigate jumps into FOR bodies in the reference generator and
  the T24 corpus. Start with BL.BILL.CROSSVAL and check which counter,
  bounds and step are available when the jump bypasses the header.

The reference compiler emits a direct jump to the body and delegates
incrementing to NEXT_V. BL.BILL.CROSSVAL assigns the counter before
jumping and can set the bound before NEXT. jbcc provisionally allows
entry with the default step and uses the current counter and bound.
When a skipped header contains an explicit STEP, NEXT reports the
missing step at runtime. Native tests cover GOTO, GOSUB, indexed jumps,
RETURN TO and the treatment of a step saved during an earlier iteration.

All 11 affected units now pass strict C99 checking, bringing the total to
16,544 of 17,336 candidates. All 16,533 previous passes still pass.

- [x] Investigate three-operand bracket assignments in the reference
  grammar and T24. The generator emits ASSIGN_FORMAT for this form.
  Verify the delimiter and replacement rules before implementing them.

The reference compiler emits COMPSTORX for replacement and COMPSTORC
for concatenating assignment, with delimiter, first field and field
count operands. EB.IN2.CALL pairs a bracket read with a write to the
same field. jbcc uses the same delimited span for reads and writes.
Native tests cover embedded delimiters, nested targets, concatenation,
and diagnostics. Padding missing fields and the empty-delimiter behavior
are provisional pending a runtime comparison.

All nine affected units now pass strict C99 checking, bringing the total
to 16,553 of 17,336 candidates. All 16,544 previous passes still pass.

- [x] Investigate the element-wise comparison functions related to
  EQS and NES, starting with LES in AZ.GEN.CC.AMT. Check ordering,
  missing elements and REUSE against the guide and reference generator.

LES, LTS, GES and GTS reuse the EQS/NES array traversal and compare
missing elements as empty strings. jbcc provisionally leaves an
explicitly empty element's result empty. The reference compiler
accepts REUSE in either argument. Native tests verify mixed delimiters,
numeric and text ordering, and single evaluation of the reused scalar.

AZ.GEN.CC.AMT now passes strict C99 checking, bringing the total to
16,554 of 17,336 candidates. All 16,553 previous passes still pass.

- [x] Investigate INDICES(file) in BUILD.DICTS.INDICES and the reference
  parser's optional second operand. Establish what index metadata a
  backend would need and how to diagnose a query without that backend.

BUILD.DICTS.INDICES consumes the list of index names. STANDARD.SELECTION
also queries a specific name and tests the result for presence. The
reference compiler passes a null pointer for the omitted name and
accepts a matrix element as the file operand. jbcc translates both
query forms and reports an unavailable secondary-index backend at
the call site. Native tests use an open in-memory file and verify that
a skipped query has no effect.

BUILD.DICTS.INDICES now passes strict C99 checking, bringing the total
to 16,555 of 17,336 candidates. All 16,554 previous passes still pass.

- [x] Trace the 228 UTF-8 decoding failures to their source files or
  includes. Compare Windows-1252 punctuation with single-byte jBC marks
  before adding an explicit legacy source-encoding option. Keep
  strict UTF-8 as the default.

Of the 228 first decoding failures, 206 are in top-level comments or
ignored text, 14 are in includes, and eight are in top-level literals.
I_DX.PRICE.COMMON accounts for 12 include failures. The literal bytes
include 0xFC and 0xFD, which are jBC array marks. The compiler and corpus
checker now accept an explicit bytes mode that preserves source literal
bytes. The UTF-8 diagnostic identifies the actual file, line and column.

Strict UTF-8 preserves all previous statuses and 16,555 strict C99
passes. In bytes mode, 198 of the 228 decoding failures turn into C99
passes and 30 reach compiler diagnostics. The resulting total is
16,753 of 17,336 candidates, with all 16,555 previous passes preserved.

- [x] Investigate forward references to dimensioned arrays. DPC.FILES
  first blocks 14 T24 units, where its DIM appears after its first textual
  use. The reference compiler's check_dimmed records assumed arrays and
  validates their declarations later. Distinguish source order from
  execution order, including for MAT arguments and runtime-sized arrays.

The reference compiler accepted a forward DIM probe in fixed and Prime
modes. The T24 units call an initializer before passing DPC.FILES as a
MAT argument. jbcc indexes declarations before translating their uses.
Native tests cover DIM and COMMON in an insert, MAT arguments, rank
diagnostics at the use, and the requirement to execute runtime-sized
declarations before use.

The byte-mode corpus now has 16,959 of 17,336 candidates passing strict
C99 checking. All 14 DPC.FILES cases and 192 other units now pass.
All 16,753 previous passes still pass, and 13 remaining units reach
different diagnostics.

- [x] Investigate missing concatenation operands in the reference
  lexer and generator. Trace trailing colons and doubled colons in T24,
  starting with AA.CREATE.NEW.DD.ITEM, and distinguish them from the
  trailing colon that suppresses a CRT newline.

The reference parser returns the left value for `resultant ':'` and
clears the output newline flag. Fixed and Prime compiler probes accepted
trailing and doubled colons in expressions and rejected a leading colon.
Native tests exercise nested expressions, CALL arguments, selectors and
statement-wide newline suppression for CRT and PRINT.

The byte-mode scan now has 17,007 of 17,336 candidates passing strict
C99 checking. All 45 targeted units and three additional units now pass.
All 16,959 previous passes still pass.

- [x] Investigate comparison spellings used by T24. The reference
  preprocessor maps `#>` to LE, `#<` to GE and whitespace-prefixed
  `><` to NE. Check their interaction with dynamic-array selectors
  and trace space-separated comparison signs.

The reference compiler accepted `> =` as GE after classifying angle
brackets. It diagnosed separated `< =` and unspaced `A><B`, while
`R<1><2>` remained two selectors. Native tests cover those distinctions,
comparisons between selected fields, and assignment through a selector.

All 16 affected units now pass strict C99 checking in byte mode.
The total is 17,023 of 17,336 candidates, with all 17,007 previous
passes preserved.

- [x] Preserve direct CALL targets when a same-named EQUATE is in scope.
  Trace CONV.SW.SCHEDULE.PROCESSING and AC.PRINT.MASK, where the
  reported numeric token comes from an include. This affects 27 units.
  Check the reference preprocessor's direct and indirect CALL expansion rules.

With no_equate_on_call enabled, the reference preprocessor inhibits
EQUATE lookup for direct CALL names and expands the variable after CALL @.
The reference probe verified a plain name, an exclamation-prefixed name
and an indirect target. The native test uses a shared include and verifies
expansion in the arguments and in ordinary expressions.

All 27 affected units now pass strict C99 checking in byte mode.
The total is 17,050 of 17,336 candidates, including all 17,023
previous passes.

- [x] Investigate quoted and punctuated direct routine names. Check the
  reference name reader for `CALL *name`, quoted targets, and matching
  SUBROUTINE headers. Distinguish a routine-name prefix from a comment.

The reference compiler strips quote delimiters from direct CALL targets
and reads header names as bare tokens. Reference probes confirmed raw
asterisk and hyphen names in both places, and quote characters retained
by the header reader. Native tests link punctuated names, call them
through quoted operands, and verify an indirect call to a punctuated name.

All six affected units now pass strict C99 checking in byte mode.
The total is 17,056 of 17,336 candidates, including all 17,050
previous passes.

- [x] Investigate indirect calls through a matrix element. Start with
  `CALL @ROUTINES(FLDNO) (...)` in TAKEOVER.MAPPING.RUN and trace how
  the reference compiler distinguishes subscripts from call arguments.

The reference name reader checks the declaration of the indirect target.
For a matrix it takes a subscript before the ordinary argument list.
Reference probes confirmed a literal or variable subscript and EQUATE
expansion. jbcc uses its regular matrix subscripts and captures the
selected routine name before argument evaluation. Native tests cover
those rules, omitted arguments and matrix diagnostics.

TAKEOVER.MAPPING.RUN now passes strict C99 checking in byte mode.
The total is 17,057 of 17,336 candidates, including all 17,056
previous passes.

- [x] Investigate the CAT spelling of concatenation in LD.OVER.RIDE.
  Trace the reference lexer's CAT token and check its precedence and
  interaction with omitted operands and output newline suppression.

The reference lexer maps CAT to the colon token. Reference probes
confirm mixed spellings, omitted operands, newline suppression for
output and INPUT, and CAT as a label. jbcc uses the same operator
precedence and omission rules for both spellings. Native tests cover
dynamic-array selectors, arithmetic precedence, and terminal output.

LD.OVER.RIDE now passes strict C99 checking in byte mode. The total
is 17,058 of 17,336 candidates, including all 17,057 previous passes.

- [x] Investigate CLEAR in HELPTEXT.CONVERSION. The guide says it
  initializes local variables to numeric zero. Check which storage
  it affects and how to preserve caller arguments and COMMON values.

The guide demonstrates resetting locals and retaining COMMON. The
reference compiler emits CLEARVAR_V and delegates the storage details
to its runtime. jbcc provisionally resets scalars and allocated
matrices owned by the current invocation. Native tests cover caller
arguments, named and unnamed COMMON, and definite assignment after a
branch containing CLEAR.

HELPTEXT.CONVERSION now passes strict C99 checking in byte mode.
The total is 17,059 of 17,336 candidates, including all 17,058
previous passes.

- [x] Investigate leading, repeated and trailing commas in CRT and PRINT.
  Start with `PRINT ,,,value` in SC.PERF.POLICY.VAR and compare the
  reference parser's tab behavior, line continuation and newline suppression.

The reference grammar treats a comma as an output item that emits a tab.
Reference probes confirmed leading and repeated commas, continuation
across a commented line, and an output comma at the end of the source.
Native tests also cover a comma before ELSE and a colon with an omitted
operand in an output list.

SC.PERF.POLICY.VAR now passes strict C99 checking in byte mode.
The total is 17,060 of 17,336 candidates, including all 17,059
previous passes.

- [x] Investigate NEXT on the same line as an inline IF inside a FOR,
  starting with XT.MAKE.KEYS. Check where the IF arm ends and how the
  parser distinguishes NEXT from a variable or a label.

Reference compiler probes put NEXT after the inline IF, including
when the arm contains another IF or an ELSE. jbcc now uses the enclosing
FOR boundary to end the arm. Native tests also cover jbcc's contextual
assignment and label forms for NEXT.

XT.MAKE.KEYS now passes strict C99 checking in byte mode. The total
is 17,061 of 17,336 candidates, including all 17,060 previous passes.

- [x] Investigate RELEASE with ON ERROR in CONVERT.KEYWORD and
  JBASE.CONVERSION. Check the reference release status and define
  how the in-memory backend handles invalid descriptors and lock ownership.

The reference compiler emits the error arm for a false RELEASE_IBB
result. The in-memory backend provisionally reports 128 through STATUS()
for invalid descriptors and zero on success when an arm is present.
Native tests cover explicit, default and global releases, unlocked keys,
and preservation of simulated foreign locks.

Both affected units now pass strict C99 checking in byte mode. The
total is 17,063 of 17,336 candidates, including all 17,061 previous
passes.

- [x] Investigate @COMMAND in JGLOBUS.DATABASE.COPY.JBASE. Check the
  reference spelling and compare the program name and argument handling
  with @SENTENCE before adding it.

The reference compiler recognizes COMMAND in its system-variable table
and emits ATFUNC_BI(12). T24 extracts arguments from field two onward.
jbcc provisionally uses the native @SENTENCE invocation for @COMMAND.
The native test verifies startup initialization when only a subroutine
reads it, the program name, empty and spaced arguments, and an ordinary
variable named COMMAND used for an indirect call.

JGLOBUS.DATABASE.COPY.JBASE now passes strict C99 checking in byte mode.
The total is 17,064 of 17,336 candidates, including all 17,063 previous
passes.

- [x] Implement SENTENCE() and SENTENCE(position). EB.CREATE.FILE
  and EB.DELETE.FILE use the no-argument form. Verify program-name and
  argument lookup against the guide and jbcc's command-line handling.

The reference grammar and generated C distinguish the zero- and
one-argument forms. jbcc follows the guide for empty, zero and negative
positions and uses native argument boundaries for indexed reads.
Native tests cover reads from a subroutine, empty and spaced arguments,
indices outside the argument list, invalid indices and preservation of
the GET (ARG.) cursor.

EB.CREATE.FILE and EB.DELETE.FILE now pass strict C99 checking in byte
mode. The total is 17,066 of 17,336 candidates, including all 17,064
previous passes.

- [x] Investigate DTX and XTD hexadecimal conversion, starting with
  the DTX call in EB.GC.GET.CONSTRAINT. Check signed values, bit width,
  and invalid input against the guide and reference implementation.

The reference compiler emits DTX_BBI with integer conversion when needed
and XTD_IB with a jBC value. The guide shows uppercase DTX output and
signed 32-bit XTD results, with parsing stopping at the first non-hex
byte. jbcc provisionally truncates DTX fractions toward zero and keeps
the low 32 bits of oversized operands in both directions. Native tests
cover these choices, zero, negative numbers, signed boundaries,
invalid text and source-located errors.

EB.GC.GET.CONSTRAINT now passes strict C99 checking in byte mode.
Of the same 17,336 candidates, 17,067 pass, including all 17,066
previous passes. The raw scan also picked up a new editor swap file
and rejected it. The ICONV call around DTX in EB.GC.GET.CONSTRAINT
still requires runtime support for the MCXB mask.

- [x] Investigate KEYIN() in JGLOBUS.CONVERT and the reference grammar's
  IN() spelling. Check how they interact with native INPUT and queued DATA.

Both forms generate KEYIN_BB in the reference compiler. The guide calls
for a raw character read with system interrupt handling preserved.
jbcc shares the DATA queue and standard input with INPUT. Native tests
exercise both spellings, byte order, EOF, NUL diagnostics, and terminal
mode restoration after a successful read, a NUL byte and a signal.

JGLOBUS.CONVERT now passes strict C99 checking in byte mode. The total
is 17,068 of 17,336 candidates, including all 17,067 previous passes.
The editor swap file from the previous scan was absent. The negative
INPUT length in JGLOBUS.CONVERT remains a runtime blocker.

- [x] Investigate the negative INPUT length in JGLOBUS.CONVERT and other
  T24 callers. Check whether length -1 polls pending input without
  consuming it and how the result relates to KEYIN() and SYSTEM(14).

JGLOBUS.CONVERT and EBS.AUTO.FUNCTION test the result before reading
from the same stream. The reference compiler passes -1 to the ordinary
INPUT macro, including with a FOR clause. The UniVerse BASIC guide
specifies a non-consuming poll with a Boolean result. jbcc provisionally
applies that behavior to length -1. The poll checks queued DATA and
stdin using the same byte-count query as SYSTEM(14). On a canonical
terminal it temporarily disables line editing to detect type-ahead.
With FOR, the current result chooses the arm immediately.
[IBM BASIC Reference Guide, INPUT](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

Native tests cover an empty open pipe, queued DATA and terminal type-ahead
followed by KEYIN. The 21 T24 units with a literal length of -1 already
passed strict C99 checking. The corpus total stays at 17,068 of 17,336,
with identical results for every file.

- [x] Investigate COUNTS in LD.SCHEDULES.CROSSVAL. Compare it with COUNT
  and verify nonoverlapping matches, empty values and array mark handling.

The reference compiler emits COUNTS_BBBB, and the guide describes
nonoverlapping per-element matches and character lengths for an empty
substring. jbcc reuses COUNT's byte-oriented matching and preserves
field, value and subvalue marks. Tests cover zero counts for empty
elements, matching within element boundaries, and a nested SUM call.
The guide's distinct null value is outside the current value model.
[jBASE COUNTS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_COUNTS.htm).

LD.SCHEDULES.CROSSVAL now passes strict C99 checking in byte mode.
The total is 17,069 of 17,336 candidates, including all 17,068
previous passes.

- [x] Investigate ISALPHA and ISDIGIT in UI.CREATE.SCRIPTS.VALIDATE
  and SY.PRODUCT.DEFINITION.VALIDATE. Compare them with ALPHA and NUM
  and check empty values, signs, punctuation and character classes.

The reference compiler emits separate ISALPHA_IB and ISDIGIT_IB
operations. The guide describes ISALPHA as equivalent to ALPHA and
illustrates ISDIGIT rejecting signed and fractional numbers. jbcc
reuses ALPHA and applies its ASCII digit classifier to all bytes in an
ISDIGIT operand. Empty strings provisionally return zero. Native tests
cover numeric strings, signs, punctuation, high bytes and array marks.
[ISALPHA](https://jbc-lang.org/pages/isalpha.html), [jBASE ISDIGIT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_ISDIGIT.htm).

All three affected T24 units now pass strict C99 checking in byte mode.
The total is 17,072 of 17,336 candidates, including all 17,069
previous passes.

- [x] Investigate LENDP in OFS.STORE.RETURN.DATA. Compare display width
  with LEN and BYTELEN for controls, array marks, and multibyte text.

The reference compiler emits LENDP_IB, distinct from LENC_IB for LEN.
The jBASE manual describes Unicode display positions under International
Mode. UniVerse explicitly uses LEN semantics when NLS is disabled.
jbcc uses its existing byte count and tests controls, array marks,
trailing spaces, UTF-8 strings and arity errors.
[jBASE LENDP](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_LENDP.htm), [IBM BASIC Reference Guide](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

OFS.STORE.RETURN.DATA now passes strict C99 checking in byte mode.
The total is 17,073 of 17,336 candidates, including all 17,072
previous passes.

- [x] Investigate READ with SETTING in CONV.LD.TRANCHE.DET,
  CONV.LOAN.SCHEDULES, UI.CREATE.CONTRACT.SCRIPT and UI.CREATE.SCRIPTS.RUN.
  Compare status assignment and error branches with the existing
  READU and MATREAD implementations.

The reference compiler passes the setting variable to NEWREAD_IIBBBB
and generates separate cases for success, absence and I/O errors.
jbcc shares READU's record lookup and optional setting, and uses the
existing file-read branch handling. The memory backend provisionally
assigns an empty setting on success and 128 for an absent record or
invalid descriptor. Native tests cover the default and explicit files,
the record destination, status assignment before branching and
diagnostics for an invalid setting target or a missing conditional arm.
[jBASE READ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_READ.htm).

All four affected units now pass strict C99 checking in byte mode.
The total is 17,077 of 17,336 candidates, including all 17,073
previous passes.

- [x] Investigate IOCTL command 100 in PATCH.RELEASE.RUN. Check the
  reference signature, parameter assignment, and what the in-memory
  backend can report for a record descriptor.

JBC.h names command 100 JBC_COMMAND_GETFILENAME. The reference compiler
passes the third operand to IOCTL_IBBB as a variable, matrix element
or temporary value. jbcc shares open-file lookup with FILEINFO and
returns 1 with a copied pathname on success. Failed lookups return
zero and provisionally preserve the output. Tests cover named and
default files, sequential paths, matrix outputs and unsupported commands.
[jBASE IOCTL](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/sup22_IOCTL.htm).

PATCH.RELEASE.RUN now passes strict C99 checking in byte mode. The
total is 17,078 of 17,336 candidates, including all 17,077 previous
passes.

- [x] Investigate the adjacent operands in the IF condition in
  POPULATE.BAL.MVMT. Check how the reference parser treats identifier
  formatting when the format variable is initialized by a GOSUB.

The reference compiler passes the adjacent operands to FMT on the
right-hand side of the comparison. jbcc now accepts a forward scalar
mask in routines with jumps and uses the existing runtime check for an
unassigned value. Native tests cover comparison precedence, padding,
and runtime failure when the initializing GOSUB is skipped.

POPULATE.BAL.MVMT and AA.PAYMENT.SCHEDULE.REDEEM now pass strict C99
checking in byte mode, bringing the total to 17,080 of 17,336 candidates.
The second unit also appears to omit a statement separator. A reduced
reference probe compiles that shape as a formatted comparison assigned
to the first variable. All 17,078 previous passes retain identical
generated statements. The C99 check establishes translation only.

- [x] Investigate EREPLACE in EB.RUN.RULE and TEC.POPULATE.EVENT.LIST.
  Compare optional limits and the start occurrence with the existing
  CHANGE function and the reference lexer.

The reference lexer maps EREPLACE to CHANGE. The reference compiler
emits SWAPF_BBBBBII for both functions, with a default limit of -1
and start of 1, and accepts the statement spelling. jbcc shares the
existing replacement code. For an empty search in the function, it
follows the documented prefix behavior and the guide's TAFJ R23
example. Tests cover the three arities, deletion, the statement
spelling and source-located diagnostics.
[jBASE EREPLACE](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_EREPLACE.htm).

EB.RUN.RULE and TEC.POPULATE.EVENT.LIST now pass strict C99 checking in
byte mode. The total is 17,082 of 17,336 candidates, including all
17,080 previous passes.

- [x] Investigate SWAP in E.MB.TRADES.TODAY. Compare its function and
  statement forms with CHANGE and confirm whether either mutates the
  source operand.

The reference compiler emits the same SWAPF_BBBBBII operation as
CHANGE for function calls, including when the first argument is a
literal or both optional positions are supplied. It emits the same
CHANGETO_VBIIIBB operation for statements. jbcc shares those two
CHANGE implementations. Native tests show that the function returns
a replacement value, while the statement updates the selected field
and preserves adjacent fields.
[jBASE SWAP](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SWAP.htm).

E.MB.TRADES.TODAY now passes strict C99 checking in byte mode.
The total is 17,083 of 17,336 candidates, including all 17,082
previous passes.

- [x] Investigate TRIMBS and TRIMFS, starting with E.DISP.DE.O.MSG.
  Verify per-element trimming, empty values and preservation of array marks.

The reference compiler emits separate one-argument operations.
The guide describes directional trimming for each element, and the
jBASE function index explicitly includes tabs. jbcc reuses its array
trim with leading or trailing whitespace mode. Tests cover both
directions, mixed spaces and tabs, empty elements, and the existing
default TRIMS behavior.
[jBASE statement and function index](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/JBC1.htm).

E.DISP.DE.O.MSG now passes strict C99 checking in byte mode.
The total is 17,084 of 17,336 candidates, including all 17,083
previous passes.

- [x] Investigate UTF8 in CONVERT.SYSTEM.UTF8.JBASE. Check its
  Latin-1 conversion against the guide and compare the inverse LATIN1
  operation, including malformed input and array marks.

The reference compiler uses separate UTF8_BBB and LATIN1_BBB calls.
The guide describes ISO-8859-1 conversion, and the jBASE CHAR reference
explicitly shows UTF8 converting a field mark into encoded text.
jbcc round-trips every nonzero byte and provisionally diagnoses
malformed UTF-8 and characters outside ISO-8859-1 at the call site.
[jBASE CHAR](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_CHAR.htm).

CONVERT.SYSTEM.UTF8.JBASE now passes strict C99 checking in byte mode.
The total is 17,085 of 17,336 candidates, including all 17,084
previous passes.

- [x] Investigate GROUP in syTransaction.getMarketValue. Compare its
  delimiter, count and out-of-range behavior with FIELD.

The reference compiler emits GROUP_BBBBII and supplies a fourth
argument of one for the three-argument spelling. The guide describes
GROUP as equivalent to FIELD and gives a full-delimiter example.
jbcc reuses FIELD, including its saved positions. Tests cover
multibyte delimiters, absent and empty fields, omitted counts,
and position updates. Position behavior follows the documented
equivalence pending a vendor runtime check.
[jBASE GROUP](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/group_function.html).

syTransaction.getMarketValue now passes strict C99 checking in byte mode.
The total is 17,086 of 17,336 candidates, including all 17,085
previous passes.

- [x] Investigate writable @FILENAME in DW.GET.FIELD.VALUE,
  ENQ.TRANS, IDESC and MI.FIELD.JOIN. Check its relation to @ID
  and @RECORD and whether reads and writes share state across routines.

Reference probes emit ATFUNC_BI(20) for both assignment and reading.
They also pass @FILENAME as an explicit READ, READV or OSREAD destination.
The guide sets the file name alongside @ID and @RECORD before ITYPE.
jbcc provisionally keeps an initially empty slot shared across
routines. Native tests cover both directions of sharing, preservation
through loop cleanup, explicit read destinations and independent
record context.
[ITYPE](https://jbc-lang.org/pages/itype.html).

All four units now parse their @FILENAME assignments and reach ITYPE
as their first blocker. The strict C99 total stays at 17,086 of
17,336 candidates, with all previous passes intact.

- [x] Investigate ITYPE in the four @FILENAME callers and the existing
  dictionary callers. Verify its syntax and compiled descriptor
  requirements, then define the behavior without a dictionary backend.

The reference compiler accepts one expression and emits ITYPE_BBBB.
The guide requires a compiled dictionary descriptor and describes
evaluation with @FILENAME, @ID and @RECORD. jbcc accepts the syntax and
reports a source-located runtime error when evaluation is reached.
Native tests cover skipped calls, reached calls and arity diagnostics.
[ITYPE](https://jbc-lang.org/pages/itype.html).

Six callers now pass strict C99 checking in byte mode. IDESC advances
to the assignment check for I.TYPE. The total is 17,092 of 17,336
candidates, including all 17,086 previous passes.

- [x] Investigate the I.TYPE assignment check in IDESC. Trace how
  DICT.ERR guards access after a successful cache lookup or record
  read, and compare with jbcc's branch assignment analysis.

In IDESC, cache and file-read success supply I.TYPE. The failure arms
set DICT.ERR before the later guard. A reduced reference program with
the same pattern compiles. jbcc retains names assigned on one side of
a conditional join and checks subsequent expression reads at runtime.
Native tests cover the initialized path, the guard that skips a
read, and a faulty guard that reaches an unassigned read. Literal
conditions and the existing CLEAR diagnostics constrain which names
qualify for these runtime checks.

IDESC and 66 other units now pass strict C99 checking in byte mode.
The total is 17,159 of 17,336 candidates, including all 17,092
previous passes. Three other units reach later diagnostics.

- [x] Investigate EQUATE LIT in CONV.DR.DEL. Check how a quoted
  statement expands and how the preprocessor records its source location.

The reference compiler expands quoted statement and expression text with
LIT and LITERALLY. Its diagnostic points to the use of the equate.
jbcc points inside the definition and resolves equates inside the
replacement using its existing recursive substitution rules. The native
tests cover a quoted CALL followed by a second statement, an array
selector, string values, and the location of an error in an include.

CONV.DR.DEL now passes strict C99 checking in byte mode, bringing the
total to 17,160 of 17,336 candidates. All 17,159 previous passes hold.

- [x] Investigate scalar reads after BEGIN CASE, starting with PROP.CHK
  in AA.FIND.DATED.RECORDS. Check how the compiler joins assignments from
  multiple arms and handles the path where no arm runs.

The reference compiler accepts a reduced example with a scalar read
after a nonexhaustive CASE. jbcc now tracks possible assignments from
reachable arms, including nested conditionals, and checks the scalar
when execution reaches the read. Each sibling arm starts with the
assignments available before the CASE. Native tests cover both matching
arms, a guard that skips the read, and a missing assignment on a path
that reaches it. [CASE](https://jbc-lang.org/pages/case.html).

AA.FIND.DATED.RECORDS and 12 other units now pass strict C99 checking
in byte mode. The total is 17,173 of 17,336 candidates, including all
17,160 previous passes.

- [x] Investigate scalar reads after FOR, starting with MATCH.POS in
  LC.MT1798.HDR.FORMAT. Check the paths that skip the body, exit at an
  UNTIL guard, or reach NEXT.

The reference compiler accepts a read after a FOR with a trailing UNTIL
and a scalar assigned inside the body. jbcc retains possible assignments
from the body and checks the value when execution reaches the read.
Native tests cover an assignment before UNTIL or NEXT and a missing value
after the bounds check, a header guard, CONTINUE or EXIT. A later guard
can skip the read entirely. [FOR](https://jbc-lang.org/pages/for.html).

LC.MT1798.HDR.FORMAT and COPY.RE.BAL.DIFFERENCE.IMPORT now pass strict
C99 checking in byte mode. The total is 17,175 of 17,336 candidates,
including all 17,173 previous passes.

- [x] Investigate CONVERT targets assigned on only some paths, starting
  with SCENARIO.LIST in AM.SCE.PREVIEW.FXO and AM.SCE.PREVIEW.SOO.
  Check successful conversion and the diagnostic when LOCATE leaves the
  target unassigned.

The reference compiler emits in-place CONVERT and CHANGE operations
after a LOCATE arm that may initialize their target. jbcc now accepts
the same assignment pattern and checks the target at runtime before
updating it. A successful update establishes the assignment for later
statements. Native tests cover a scalar conversion, an indexed CHANGE
and the diagnostic at the target when LOCATE misses.
[CONVERT](https://jbc-lang.org/pages/convert.html),
[CHANGE](https://jbc-lang.org/pages/change.html).

Both scenario preview routines now pass strict C99 checking in byte
mode. The total is 17,177 of 17,336 candidates, including all 17,175
previous passes.

- [x] Investigate conditionally assigned REMOVE sources in
  ARC.RECORDS.SELECT, COLLATERAL.LIMIT.EOD and MB.TEXT.CASE.CONVERSION.
  Check extraction and cursor advancement when the source is assigned
  and the runtime diagnostic when the assignment path is skipped.

The reference compiler accepts both forms of REMOVE after conditional
initialization of the source. jbcc allows the same pattern and checks
the source before reading the cursor. Native tests alternate both forms
in both orders and check the delimiter codes, exhaustion and the
source-located error when initialization is skipped.

COLLATERAL.LIMIT.EOD and MB.TEXT.CASE.CONVERSION now pass strict C99
checking in byte mode. The total is 17,179 of 17,336 candidates,
including all 17,177 previous passes. ARC.RECORDS.SELECT reaches its
first read of R.ARC.RECORDS.SEL after REPEAT.

- [x] Investigate scalar reads after LOOP, starting with R.ARC.RECORDS.SEL
  in ARC.RECORDS.SELECT. Check what is assigned when a guard exits
  before the body reaches the assignment, and when a later iteration
  exits after the assignment has already run.

The reference compiler accepts a read after a LOOP whose guard can
skip the assignment on the first iteration. It also accepts a read
after an unconditional early EXIT preceding an assignment. jbcc now
keeps possible assignments from the loop body and checks them at the
read. Native tests cover a first-iteration exit, a later exit that sees
the previous value, multiple guards, and the runtime diagnostic for an
early EXIT or BREAK. [LOOP](https://jbc-lang.org/pages/loop.html).

ARC.RECORDS.SELECT and four other units now pass strict C99 checking
in byte mode. The total is 17,184 of 17,336 candidates, including all
17,179 previous passes.

- [x] Investigate compound assignments to conditionally assigned
  scalars, starting with REQ.ID in MB.E.STMT.ENT.DETAIL and YFLD in
  CONV.LOCAL.TABLE.G12.2. Check the read of the previous value when
  the initializing branch runs or is skipped.

A reduced reference program emits an in-place concatenation for both
patterns. jbcc now checks the previous value at runtime when an earlier
branch may have initialized the scalar. The same check applies before
extracting a selected field for a compound update. Native tests cover
concatenation, arithmetic and a selected field, including the diagnostic
when initialization is skipped.

MB.E.STMT.ENT.DETAIL and EXPAND.MULTI.AUTOM now pass strict C99
checking in byte mode. The total is 17,186 of 17,336 candidates,
including all 17,184 previous passes.

- [x] Investigate reads that depend on assignments from earlier FOR
  iterations. Start with YFLD in CONV.LOCAL.TABLE.G12.2, where the first
  iteration initializes the scalar and a later sibling arm appends to it.

The reference compiler emits the same scalar for initialization and
concatenation, so the loop keeps its value between iterations. jbcc
checks tentative reads against plain assignments in the enclosing FOR
and checks the value at runtime. A read followed only by a compound
update or a self-referential assignment still gets a compile diagnostic
when the loop has no initializer. Native tests cover both branch orders
and a first iteration that skips initialization.
[FOR](https://jbc-lang.org/pages/for.html).

CONV.LOCAL.TABLE.G12.2 and DE.ADD.TAG.DETAILS now pass strict C99 checking
in byte mode. The total is 17,188 of 17,336 candidates, including all
17,186 previous passes.

- [x] Investigate preprocessor conditionals and include guards.
  Start with the #ifndef blocks in qbasiccommonpick, qbasiccommonseq
  and EB.DEV.CHECK.LICENSE. Verify how a symbol is defined and how the
  preprocessor skips inactive branches.

The reference compiler treats a zero-valued definition as present and
expands the replacement of #DEFINE when it reads the directive.
A reference probe with a repeated guarded include emitted its body
only once. The reference also processed a definition and an include
lookup inside inactive branches. jbcc skips those side effects and
requires conditionals to close in the file that opens them. Native
tests cover nesting, case-sensitive names, usage of definitions from
an include, and diagnostics in the included file.

All three units now pass strict C99 checking in byte mode, bringing
the total to 17,191 of 17,336 candidates with all previous passes intact.

Adding the local reference source directory to the include path advances
38 corpus units from missing JBC.h to its missing dependency jportB.h.
The bundled reference sources supply JBC.h.

- [x] Investigate CHECKSUM in OS.CHECKSUM.JBASE. Verify the documented
  position-weighted byte sum and how it interacts with jbcc's native
  string representation.

The reference compiler emits CHECKSUM_BBB with one argument. jbcc
implements the guide's one-based weighted sum over unsigned bytes.
Native tests cover the ASCII examples, empty and numeric inputs,
delimiter and UTF-8 bytes, and a sum greater than 32 bits. The runtime
reports overflow beyond UINTMAX_MAX. The guide's CHAR(0) example
needs a string representation that can store embedded NUL bytes.
[CHECKSUM](https://jbc-lang.org/pages/checksum.html).

OS.CHECKSUM.JBASE now passes strict C99 checking in byte mode, bringing
the total to 17,192 of 17,336 candidates with all previous passes intact.

- [x] Investigate @USER.ROOT in VALIDATE.SIGN.ON. Check reads, writes,
  the guide's 63-byte limit and the scope a standalone process can
  provide.

The reference compiler reads and writes system variable 32, and the
guide assigns the published value to USERSTATS attribute 28. Native
jbcc keeps the value within the process and reports an oversized
assignment at its source location. Tests cover reads across linked
routines, clearing, snapshots and the 63-byte boundary with UTF-8.
[jBASE user information](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_%40.htm).

VALIDATE.SIGN.ON now passes strict C99 checking in byte mode. The total
is 17,193 of 17,336 candidates, including all 17,192 previous passes.

- [x] Investigate XMLTOXML and XMLTODYN in the T24 corpus. Start with
  DW.XML.TRANSFORM, EB.TRANSFORM.XML and OS.UPLOAD.EUS.FILE. Verify the
  writable result arguments and the behavior when no XML backend is
  available.

The reference grammar accepts two expressions and an optional writable
result code. A reference compiler probe accepts a matrix element as the
result and rejects a literal or a dynamic-array selector. jbcc lowers
both forms and reports a source-located error when an XML call is
reached. Native tests cover skipped calls, both result target forms
and malformed operands.
[XMLTOXML](https://jbc-lang.org/pages/xmltoxml.html),
[XMLTODYN](https://jbc-lang.org/pages/xmltodyn.html).

All three T24 callers now pass strict C99 checking in byte mode. The
total is 17,196 of 17,336 candidates, including all 17,193 previous passes.

- [x] Investigate CALLC JBASESubroutineExist in CHECK.ROUTINE.EXIST.
  Check the reference signature and status argument, then decide how
  it can query the subroutines linked into a native jbcc executable.

The guide specifies a numeric presence result and reserves SubInfo.
The reference compiler passes a writable variable or a temporary for a
literal. jbcc supports the documented two-argument call as an expression
or statement. It uses a case-sensitive lookup over linked subroutines and
sets SubInfo to an empty string as its native convention. Native tests
cover an uncalled linked routine, missing names, a function name, and
scalar and matrix-element info arguments.
[JBASESubroutineExist](https://jbc-lang.org/pages/jbasesubroutineexist.html).

CHECK.ROUTINE.EXIST now passes strict C99 checking in byte mode.
The total is 17,197 of 17,336 candidates, including all 17,196
previous passes.

- [x] Investigate `array / REUSE(scalar)` in COLLATERAL.ALLOCATION.III.
  Compare the generated reference operation with DIVS and the existing
  infix REUSE multiplication behavior.

The reference compiler emits DIV_BBBB with a REUSE_BB operand on
either side. It emits DIVS_BBBB for the explicit function. jbcc uses
its shared element-wise arithmetic and preserves the scalar division
diagnostic for a zero divisor. Native tests cover both operand orders,
mixed marks, precedence, and invalid reused operands.

COLLATERAL.ALLOCATION.III now passes strict C99 checking in byte mode.
The total is 17,198 of 17,336 candidates, including all 17,197
previous passes.

- [ ] Investigate two subscripts on R.NEW in ACCOUNT.AUTHORISATION.
  Trace the COMMON declaration and check how the reference compiler
  treats a second subscript on a one-dimensional matrix.
