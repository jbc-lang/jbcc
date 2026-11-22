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

- [ ] Support single-argument substring extraction, `expression[n]`.
  The RIGHT chapter defines it as the last n characters. Check the
  reference grammar, dynamic-array values, and zero and oversized lengths.
  In 532 units the first diagnostic expects a comma at a closing bracket.
