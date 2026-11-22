# jbcc

jbcc is a jBC-to-C compiler project. Its first target is a native executable
built with the system C compiler. The first translator is written in Python 3 and emits standalone C99.

## Try the compiler

From the checkout, with Python 3.8+ and a C99 compiler on PATH:

```sh
./jbcc tests/snippets/coercion.b -o /tmp/coercion.c
cc -std=c99 /tmp/coercion.c -o /tmp/coercion
/tmp/coercion
```

To build and link in one step, use `./jbcc --exe tests/snippets/coercion.b -o /tmp/coercion`.
Native builds default to `cc -std=c99`. Set `CC` to select the compiler and
`CC_FLAGS` to pass additional compile or link options, for example
`CC=clang CC_FLAGS="-O2 -Wall" ./jbcc --exe tests/snippets/coercion.b -o /tmp/coercion`.
Both variables accept shell-style quoting. The compiler is invoked directly
with the resulting arguments.

The source assigns `"2"` to N. The first CRT adds 3 and prints `5`.
The second concatenates 3 and prints `23`. Each output ends in a newline.

## Just recipes

Run `just` to list the optional shortcuts. Build recipes accept the output
path first, followed by one or more source files.

```sh
just test
just build /tmp/quine tests/programs/quine.b
just emit-c /tmp/banner.c tests/programs/banner.b
just run tests/snippets/coercion.b
just banner
just quine
just routine
just corpus ~/Downloads/t24 > /tmp/jbcc-corpus.json
```

## Implemented subset

Use scalar assignment, PRINT and CRT, decimal numeric
literals, quoted strings (single, double or backslash delimiters),
parentheses, arithmetic, concatenation, and compound assignments (`+=`, `-=`, and `:=`). Addition binds more tightly than
concatenation. Names are case-sensitive. Reads require an assigned value. Routines with GOTO or GOSUB check this at runtime because jumps can bypass assignments. Separate statements with a newline or semicolon. A statement beginning
with `*`, `!` or `REM` comments out the rest of its line. These markers
can follow a named or numeric label directly, as in `setup:* read inputs`
or `100: REM retry`.

`CHANGE old TO new IN target` replaces nonoverlapping substrings from left
to right in an assigned scalar, matrix element or dynamic-array field.
The original grammar also accepts `WITH` in place of `TO`. The function
`CHANGE(text, old, new [, count [, first]])` returns a new value. Counting
starts at one. A count below one replaces all remaining matches, and a
starting occurrence below one starts at the first match. An empty replacement
deletes matches. jbcc leaves the input intact for an empty search string.
[CHANGE](https://jbc-lang.org/pages/change.html), [EREPLACE](https://jbc-lang.org/pages/ereplace.html).

Concatenating assignment appends the right-hand value as a string.
For example, after `S = 'QWERTY'`, `S := 123` gives `QWERTY123`.
It also works on matrix elements, dynamic-array fields and substrings.
[String variables](https://jbc-lang.org/pages/string_variables.html).

The generated file includes the C runtime. Values are immutable strings. Assignment preserves a copied value, and loop
boundaries reclaim temporary values that are no longer in use. Integer addition, subtraction and multiplication check signed 64-bit
overflow. Division and fractional arithmetic use native long double,
rounding results to at most 15 fractional places by default. Division by zero reports the operator location.

NUM tests whether an expression has numeric text and returns 1 or 0.
It follows the guide’s prime-emulation examples. Signed decimals and leading
zeros are accepted, as are the empty string and the single characters
`.`, `+`, and `-`. Spaces, thousands separators, and exponent notation
return 0. [NUM](https://jbc-lang.org/pages/num.html).

MOD returns the decimal remainder of two numeric expressions. For example,
`MOD(12.34, 0.5)` returns `0.34`. A zero divisor returns the original
dividend, as specified in the guide. For signed operands, jbcc uses a
quotient truncated toward zero, so `MOD(-7, 3)` returns `-1`. This sign
rule is provisional pending a reference run. Explicit PRECISION truncates
the nonzero-divisor result after the remainder is computed.
[MOD](https://jbc-lang.org/pages/mod.html).

ABS returns the magnitude of a numeric expression. For example,
`ABS(10 - 15)` returns `5`. jbcc reads decimal strings directly,
preserving their significant digits, and truncates the result when an
explicit PRECISION applies. [ABS](https://jbc-lang.org/pages/abs.html).

DATE() returns the process’s current local calendar date as the number of
days since 31 December 1967. For example, `OCONV(DATE(),'D-')` prints
today’s date as `MM-DD-YYYY`. [DATE](https://jbc-lang.org/pages/date.html).

TIME() returns the local clock time in seconds past midnight. The OCONV
mask `MT` prints hours and minutes on a 24-hour clock, and `MTS` adds
seconds. For example, `OCONV(1,'MTS')` returns `00:00:01`. Both masks
accept an explicit colon separator. The current runtime accepts whole
seconds from 0 through 86399. [TIME](https://jbc-lang.org/pages/time.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

TIMEDATE() formats one reading of the local clock as a printable string,
for example `23:59:59 31 DEC 2023`. jbcc uses the guide’s default layout
with English month abbreviations. [TIMEDATE](https://jbc-lang.org/pages/timedate.html).

ICONV accepts compact Gregorian dates in `YYYYMMDD` form with masks `D`
and `D4`. For example, `ICONV('20121231', 'D')` returns `16437`, the
number of days since 31 December 1967. Other masks and input formats
produce a diagnostic at the call site. An impossible date also produces
a diagnostic, a provisional choice pending a reference run.
[ICONV](https://jbc-lang.org/pages/iconv.html).

For dates, the OCONV mask `D` produces `DD MON YYYY`. A digit from 0 through 4 selects the
year width. With a separator (`-`, `/` or `.`), jbcc follows the guide’s
worked example and observed T24 usage. For example, `OCONV(16454,'D4/')` returns
`01/17/2013`. Append `E` for day-first order. The guide’s syntax table
instead describes day-first order for the plain numeric form. Component
masks include `DD`, `DM`, `DMA`, `DJ`, `DQ`, `DW`, `DWA`, and `DY` with
optional year width. The runtime accepts Gregorian years 1 through 9999
and reports unsupported masks at the call site. [DATE](https://jbc-lang.org/pages/date.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

STR repeats its entire first argument, including any embedded array marks.
For example, `STR('ab', 3)` returns `ababab`. Empty input and zero
repetitions produce an empty string. The guide specifies integer counts.
For fractional or negative counts, jbcc provisionally follows SPACE. It truncates
toward zero and returns an empty string for nonpositive counts.
[STR](https://jbc-lang.org/pages/str.html).

TRIM accepts one to three arguments. In jbcc, `TRIM(text)` removes
leading and trailing spaces and collapses internal runs to one space.
A second argument selects the trim byte. An empty second argument selects
space, as seen in T24. Explicit modes are `L` (leading), `T` (trailing),
`B` (both ends), `A` (all), and `R` (both ends and repeated bytes).
`F`, `E`, and `D` apply leading, trailing, and run trimming respectively
to spaces and tabs. The omitted mode defaults to `R`, and `D` keeps the
first byte of a mixed internal run. Both choices are provisional pending
a reference run. [TRIM](https://jbc-lang.org/pages/trim.html),
[jBASE TRIM manual](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_TRIM.htm).

TRIMF removes leading space bytes and TRIMB removes trailing space bytes.
Both preserve tabs and interior spaces. They use the same runtime as
`TRIM(text, " ", "L")` and `TRIM(text, " ", "T")`, respectively.
[TRIMF](https://jbc-lang.org/pages/trimf.html), [TRIMB](https://jbc-lang.org/pages/trimb.html).

MAXIMUM and MINIMUM compare numeric elements across field, value, and
subvalue marks. An empty element counts as zero. Nonnumeric elements are
skipped, and jbcc provisionally returns zero when all elements are
nonnumeric. Comparisons honor PRECISION and keep the first element on a
tie. The guide shows different output formatting for the two functions.
MAXIMUM returns the selected text, while MINIMUM rounds excess decimal
places to the explicit precision. jbcc follows those examples pending a
reference run. [MAXIMUM](https://jbc-lang.org/pages/maximum.html),
[MINIMUM](https://jbc-lang.org/pages/minimum.html).

SUM adds numeric elements at the deepest mark present in the array
(field, value, or subvalue) and preserves each higher-level mark.
For example, `SUM(1 : @FM : 2 : @VM : 3)` returns `1 : @FM : 5`.
The guide specifies that nonnumeric elements are ignored. For a group
with no numeric elements, jbcc returns zero provisionally. Each addition
uses the runtime's arithmetic and PRECISION rules. [SUM](https://jbc-lang.org/pages/sum.html).

Single-line and multiline IF support THEN, ELSE, and nested branches.
Close a multiline arm with END and start its alternative with END ELSE.
The system constants `@TRUE` and `@FALSE` evaluate to 1 and 0.
Comparisons return the same values. Two decimal strings compare numerically;
other pairs compare in byte order. Numeric zero and the empty string are
false. Decimal comparisons are exact until an explicit PRECISION executes.
See the [Boolean variables](https://jbc-lang.org/pages/boolean_variables.html)
and [IF](https://jbc-lang.org/pages/if_statement.html) chapters.

AND (`&`) and OR (`!`) have equal precedence and group left to right.
Comparisons bind more tightly. For example, `1 OR 0 AND 0` evaluates to
`0`. Both operators return `1` or `0` and skip the right operand when the
left decides the result. At the start of a statement, `!` introduces a
comment. Grouping follows the [jBC grammar](https://github.com/jbc-lang/jbc-language/blob/master/spec/jbc.y).
Short-circuit evaluation follows the original C generator's use of C's
`&&` and `||` in `operator_integer_gen`.

PRECISION accepts an expression whose value is a nonnegative integer. For
example, `PRECISION 6` followed by `CRT 2 / 3` prints `0.666666`. The
runtime truncates fractional results toward zero at the selected number of
decimal places. Numeric comparisons and truth tests use that many places
while stored strings keep their original bytes. Arithmetic accuracy depends
on the host's `long double`. A local GOSUB shares the current setting.
In jbcc, an external subroutine or function inherits the setting on entry
and restores the caller's setting on return.

The arithmetic and truth tests follow the guide's examples. The guide's
second PRECISION example predicts unequal values at 17 places although its
two printed operands agree through those places. Until a reference runtime
is available, jbcc compares the displayed decimal digits through the selected
place. [PRECISION](https://jbc-lang.org/pages/precision.html),
[Boolean variables](https://jbc-lang.org/pages/boolean_variables.html).

MATCH and MATCHES compare the whole input against a pattern. A count followed
by A, N, C or X selects ASCII letters, digits, alphanumeric bytes or any
bytes, respectively. A zero count allows any length, including zero.
For example, `'QA42' MATCHES "2A2N"` is true, as is
`'QA42' MATCHES "'QA'1-3N"`. Quoted literals match exactly, and a value mark
(`@VM`) separates alternative patterns. Unquoted text such as the prefix
in `PL5N` is literal, including periods in the default jBASE mode.
Concatenation binds more tightly than MATCH, so a program can build a
pattern expression directly on its right. [MATCHES](https://jbc-lang.org/pages/matches.html).

The initial `FMT(value, mask)` implementation supports byte-width masks
such as `35L` and `3'0'R`, including a single fill byte in single or
double quotes. Overlong input wraps into padded blocks separated by
CHAR(251). With alignment first, `L` or `R` can be followed by a single
decimal precision digit and a field such as `#10` (spaces), `%10` (zeros)
or `*10` (asterisks). For example, `FMT(1234.56,'R2%10')` returns
`0001234.56`. Precision follows the guide’s worked examples, with no
implicit scaling. Ties round away from zero. Fixed fields retain the
aligned end on overflow. These edge rules are provisional pending a
reference run. Unsupported masks produce a source-located runtime
diagnostic. [FMT](https://jbc-lang.org/pages/fmt.html).

PRINT and CRT write to standard output. Commas separate items with tabs.
A final colon suppresses the newline. A bare PRINT or CRT emits a newline.

FOR supports inclusive bounds, a default step of one, optional STEP,
and an optional variable name after NEXT. The limit and step are evaluated
at the start of each iteration. The captured step increments the counter
after the body. LOOP allows WHILE and UNTIL guards before or after other
statements, including on the same line. FOR also accepts a WHILE or UNTIL
guard in its header. CONTINUE skips the rest of the innermost iteration.
In FOR it advances the counter by the captured step. In LOOP it resumes
at the top, even when a guard appears later in the body. Outside a loop
it issues a compile-time warning and execution proceeds normally.
[CONTINUE](https://jbc-lang.org/pages/continue.html). See the [FOR](https://jbc-lang.org/pages/for.html) and
[LOOP](https://jbc-lang.org/pages/loop.html) chapters.

A bare `EXIT` leaves the innermost FOR or LOOP, including from inside a
CASE arm. A FOR counter keeps its current value. Outside a loop the
compiler warns and ignores bare EXIT, following the reference parser.
`EXIT(expression)` ends the process, including when executed in a
subroutine. jbcc truncates a fractional status toward zero and requires
the result to fit a C int. This conversion policy is provisional pending
a reference run. [EXIT](https://jbc-lang.org/pages/exit.html).

## Dimensioned arrays and shared storage

DIM and DIMENSION accept comma-separated declarations with positive integer
bounds, including expanded EQUATE constants. Indices run from zero through
the declared bound, inclusive, in this subset. Supply one index per dimension.
Local matrices belong to one invocation. Passing an element to CALL passes
that slot by reference. For T24 sources, jbcc also accepts bounds such as
`DIM Grid(Config<1>, N + 1)`. This follows the reference parser’s
`dimvar` rule in dynamic-array mode. The guide describes the constant-bound
form. Each time execution reaches a runtime-sized declaration, jbcc
evaluates its bounds. Within one invocation, re-entering it with the
same shape preserves the elements. A changed shape or use after skipping
the declaration raises a diagnostic. This re-entry policy is provisional
pending a reference run. Unassigned reads and out-of-range subscripts produce
runtime diagnostics.

`MAT A = expression` evaluates the expression once and fills every slot,
including index zero. `MAT A = MAT B` copies the values of a fully
assigned matrix. An unassigned source slot raises a runtime error at the
copy statement. Both forms work with local and COMMON matrices. For now,
jbcc supports copies between matrices with identical declared bounds.
[MAT](https://jbc-lang.org/pages/mat.html).

`MATBUILD record FROM matrix` joins the one-based elements with field
marks. In `MATBUILD record FROM matrix, 3, 7 USING ':'`, positions 3
through 7 are included. The last subscript varies fastest in a matrix
with several dimensions. USING takes the first delimiter byte. Empty
elements retain their positions, and reading an unassigned element in the
selected range raises a diagnostic. Pending a reference run, jbcc joins
without a separator for an empty USING string, returns an empty result for
a reversed range, and diagnoses positions outside the matrix. The reference
generator uses -1 for an omitted endpoint. Its grammar also accepts a
comma before the delimiter when both endpoints are present. [MATBUILD](https://jbc-lang.org/pages/matbuild.html).

`MATPARSE matrix FROM record SETTING used` splits a record on field marks
in the same element order as MATBUILD. An optional range follows the matrix
name. For example, `MATPARSE A, 2, 4 FROM S USING "|"` fills positions 2
through 4. Element zero receives any unsplit remainder, including its
internal delimiters. SETTING is optional and counts input fields placed in
the selected one-based slots, including empty fields between or after
delimiters. jbcc clears unused slots inside the range and treats empty
input as zero fields. An empty delimiter treats nonempty input as one
field. These edge cases are provisional pending a reference run.
[MATPARSE](https://jbc-lang.org/pages/matparse.html).

COM and COMMON accept scalars and dimensioned arrays. Declarations of the
same named or unnamed block share slots by position across routines in one
program. Repeating a scalar in the same block reuses its original slot,
including across separate COMMON statements. This follows the reference
parser’s `common_identifier` rule and its symbol-table allocation. The
compiler checks the member count, rank, and known bounds
across input files. For T24 declarations such as
`COMMON /CACHE/ Rows(Config<1>), Tail`, jbcc evaluates the bound when
execution reaches the declaration. Each matrix has its own storage, so
the scalar after it keeps the same position in every routine. Indices and
MAT operations use the saved bounds, even if Config changes later.
Re-entering the declaration or binding the same member in another routine
checks its dimensions and preserves its values. A different shape produces
a source-located diagnostic. This timing and mismatch policy is provisional
pending a reference run. The current initialization policy leaves slots unassigned until
written. [DIMENSION](https://jbc-lang.org/pages/dimension.html),
[COMMON](https://jbc-lang.org/pages/common.html).

## Compile a T24-style routine

Pass one main program and its subroutine and function source files to the same command.
The translator resolves direct calls by the declared routine name and checks
argument counts before writing a single C translation unit.

```sh
./jbcc tests/routines/caller.b tests/routines/get.status.b -o /tmp/status.c
cc -std=c99 /tmp/status.c -o /tmp/status
/tmp/status
```

This example prints `open` and then `closed`. Both files insert the same
field definition. The caller passes a record and an output variable. The
callee reads the status field, selects a CASE arm, and updates the output.

- Dynamic arrays use one-based field, value and subvalue positions. Use
  `R<2,3,1>` to read or replace a component and `R<-1> = X` to append a
  field. Tight postfix brackets distinguish extraction from relational
  operators. Missing components read as empty strings. Sparse assignments
  fill intervening positions with marks. The runtime uses single-byte
  `@FM` (also `@AM`), `@VM` and `@SM`. [Dynamic arrays](https://jbc-lang.org/pages/dynamic_arrays.html)
- `INS X BEFORE R<field[,value[,subvalue]]>` inserts X at the selected
  level, shifting later siblings and padding missing positions with empty
  components. The first negative index appends at its level and subsequent
  negative indices select position one. jbcc treats an unassigned target
  as empty, truncates fractional indices, and treats trailing zero indices
  as omitted and other zeros as one. These choices are provisional pending
  a reference run. [INS](https://jbc-lang.org/pages/ins.html)
- `INSERT(R, field, value; X)` returns a new array with X inserted at
  that value position. R keeps its original contents. Supply one to three
  indices before the semicolon. With all three indices, the final separator
  can also be a comma, as in `INSERT(R, field, value, 0, X)` in T24.
  Both forms follow the reference parser’s `insert_delims` rule and use
  the same index handling as INS. [INSERT](https://jbc-lang.org/pages/insert.html)
- `REPLACE(R, field, value; X)` returns a copy with X in the selected
  position. The source and neighboring elements keep their values. An empty
  replacement clears the selected component and preserves its position.
  REPLACE shares INSERT’s argument forms and index handling, including the
  five-argument comma form used by T24. [REPLACE](https://jbc-lang.org/pages/replace.html)
- `DEL R<field[,value[,subvalue]]>` removes the selected component and
  closes the gap between its siblings. The target can be an assigned scalar
  or a matrix element. Fractional positions truncate toward zero. A missing
  or nonpositive position leaves the array intact, and a nonnumeric index
  raises a runtime diagnostic. [DEL](https://jbc-lang.org/pages/del.html)
- `DELETE(R, field[, value[, subvalue]])` returns the array with the
  selected component removed. R keeps its original contents. The reference
  compiler emits function calls with two to four arguments. Following T24
  usage, trailing zero indices omit the corresponding levels, so
  `DELETE(R, 2, 0, 0)` removes field 2 and `DELETE(R, 1, 2, 0)` removes
  value 2 of field 1. Other index handling follows DEL.
- Define a local label with a trailing colon, including inside IF, CASE,
  LOOP and FOR bodies. GOTO can jump within or leave a FOR. A jump that
  would enter a FOR without executing its header gets a source diagnostic.
  GOSUB starts a fresh control-flow invocation and shares
  the routine's variables and supports nested returns. Execution falls through
  labels encountered sequentially. STOP terminates the program. [GOSUB](https://jbc-lang.org/pages/gosub.html)
- `PROGRAM name` documents the source. The name generates no C symbol and
  execution continues with the following statement. The native snippet
  exercises the guide's documented behavior with a dotted, hyphenated name
  and a quoted name containing a semicolon. [PROGRAM](https://jbc-lang.org/pages/program.html)
- SUBROUTINE parameters and plain variable arguments to CALL share storage,
  including output arguments. Expressions are passed in temporary slots.
  Each invocation has its own locals. A RETURN outside a local GOSUB ends
  the invocation. Reading an unassigned output reports a runtime diagnostic.
  [SUBROUTINE](https://jbc-lang.org/pages/subroutine.html)
- EQU or EQUATE defines token substitutions, including comma-separated
  definitions. $INSERT and INCLUDE search the including file's directory,
  followed by each `-I DIR` in order. Included tokens retain their source
  locations. [EQUATE](https://jbc-lang.org/pages/equate.html)
- BEGIN CASE evaluates conditions in order, executes the first true arm,
  and resumes after END CASE. Use CASE 1 for a default. [CASE](https://jbc-lang.org/pages/case.html)

## Built-in functions

CHAR returns a single byte for integer codes 1 through 255. CHAR(0)
reports a runtime diagnostic while strings use NUL termination.

`QUOTE(text)` and `DQUOTE(text)` enclose the value in double quotes.
`SQUOTE(text)` uses single quotes. Each function adds one quote at each
end, preserving embedded quotes and array marks. The native snippet checks
the guide’s `QWERTY` examples and the two quote bytes returned for empty
input. [QUOTE / DQUOTE / SQUOTE](https://jbc-lang.org/pages/quote___dquote___squote.html).

`UPCASE(text)` converts ASCII letters to uppercase. `DOWNCASE(text)` and
its alias `LOWCASE(text)` convert them to lowercase. In the current byte
runtime, punctuation, digits, array marks and other non-ASCII bytes pass
through unchanged. The guide describes Unicode case conversion separately
under International Mode. [DOWNCASE](https://jbc-lang.org/pages/downcase.html).

`RAISE(text)` increments delimiter bytes 248 through 254 by one.
`LOWER(text)` decrements bytes 249 through 255 by one. Each function
preserves all other bytes. For example, LOWER turns field marks into value
marks so a record can be nested within a field. These ranges follow the
jBC tables in the guide. [RAISE](https://jbc-lang.org/pages/raise.html),
[LOWER](https://jbc-lang.org/pages/lower.html).

`CONVERT from TO to IN target` maps each input byte once. A source byte
without a corresponding replacement is deleted, so `CONVERT '-' TO '' IN S`
removes every hyphen. The target may be a scalar, a matrix element, or a
selected dynamic-array component. The function form uses the default jBASE
argument order, `CONVERT(text, from, to)`, and returns a new value.
jbcc uses the first mapping for a repeated source byte, a provisional
choice pending a reference run. [CONVERT](https://jbc-lang.org/pages/convert.html).

`INDEX(text, needle, occurrence)` returns the one-based byte position of
the requested match, or zero when it is missing. For example,
`INDEX('ab--ab', 'ab', 2)` returns 5. jbcc currently counts
nonoverlapping matches, truncates fractional occurrence numbers toward
zero, and returns zero for an empty needle or a nonpositive occurrence.
These edge cases are provisional pending a reference run.
[INDEX](https://jbc-lang.org/pages/index.html).

LEFT and RIGHT extract leading and trailing bytes respectively. For example,
`RIGHT("The world is my lobster", 7)` returns `"lobster"`. A length below
one gives an empty string, and a length exceeding the input size gives the
whole string. Both functions use the existing substring rules for numeric
lengths, truncating fractional values toward zero.
[LEFT](https://jbc-lang.org/pages/left.html), [RIGHT](https://jbc-lang.org/pages/right.html).

LEN counts bytes in the current byte-oriented runtime. FIELD accepts a
one-based occurrence and optional field count. The expression
`Text[delimiter, occurrence, count]` calls the same FIELD runtime as
`FIELD(Text, delimiter, occurrence, count)`. For example,
`"a/b/c/d"["/",2,2]` returns `b/c`. FIELD, COUNT and DCOUNT
support multi-byte delimiters. COUNT counts nonoverlapping occurrences as
documented for TAFC R19. DCOUNT returns zero for an empty record. For an
empty delimiter, this implementation returns byte length for COUNT and
DCOUNT, and treats the input as one field for FIELD. These empty-delimiter
choices are provisional. NOT uses the same truth conversion as IF.
[FIELD](https://jbc-lang.org/pages/field.html), [COUNT](https://jbc-lang.org/pages/count.html),
[DCOUNT](https://jbc-lang.org/pages/dcount.html), [LEN](https://jbc-lang.org/pages/len.html).

SPLICE joins corresponding field, value and subvalue positions with a
separator. An unmatched element still gets the separator on its missing
side. An explicitly empty element paired with another element gives an
empty result at that position. An empty separator produces an empty
result, following the guide’s null-separator rule. For T24 calls such as
`SPLICE(ids, '*HIS', '')`, jbcc treats a wholly empty input array as
absent, giving each ID the suffix `*HIS`. This empty-array convention
is provisional pending a reference run. [SPLICE](https://jbc-lang.org/pages/splice.html).

T24 uses `SPLICE(REUSE(prefix), "/", ids)` and `SPLICE(ids, "/", REUSE(suffix))`
to repeat a scalar at each position in an array. jbcc evaluates the
wrapped expression once. This form accepts a direct REUSE call in either
outer operand. A reused value containing a field, value or subvalue mark
produces a diagnostic at the REUSE call.

SUBSTRINGS extracts a byte range from each field, value and subvalue,
preserving every mark, including those around empty elements. A start of
zero selects the first byte, as in the guide’s example and T24.
Negative starts and fractional arguments follow jbcc’s scalar substring
rules. The guide’s table omits the two bytes from `DDDDD` in its
`SUBSTRINGS(t,4,20)` result. Applying the stated rule gives `DD` for
that subvalue. [SUBSTRINGS](https://jbc-lang.org/pages/substrings.html).

FIELDS applies FIELD to each element of a dynamic array. It preserves
field, value and subvalue marks, including those around empty elements.
For example, `FIELDS("a:b":@VM:"c:d", ":", 2)` returns `"b":@VM:"d"`.
The optional fourth argument selects how many delimited fields to keep
per element. In the guide’s example table, jbcc retains the trailing
marks on the third attribute of `r1` and the leading colon before `W` in
`r3`, following the element-wise FIELD rule. jbcc accepts multi-byte
delimiters as in the guide’s `jbase_field` example. [FIELDS](https://jbc-lang.org/pages/fields.html).

## In-memory file tests

The test backend starts with empty files explicitly named at translation
time. Each execution starts fresh. To run the example:

```sh
./jbcc --memory-file CUSTOMERS tests/io/records.b -o /tmp/records.c
cc -std=c99 /tmp/records.c -o /tmp/records
/tmp/records
```

OPEN a name TO a descriptor, READ a variable FROM a descriptor and key,
and WRITE a value ON or TO a descriptor and key. READ and WRITE use
explicit descriptors. OPEN and READ require THEN or ELSE. WRITE can be
unconditional or use a success or failure branch. In this backend a failed
open or read clears its destination. An unhandled failed WRITE terminates
with a source location. Stored records survive reassignment and loop
temporary cleanup.
[OPEN](https://jbc-lang.org/pages/open.html), [READ](https://jbc-lang.org/pages/read.html),
[WRITE](https://jbc-lang.org/pages/write.html).

DELETE removes a record by key. `DELETE F, Key` uses the descriptor F.
`OPEN Name ELSE ...` sets the default descriptor for `DELETE Key`. A
missing record counts as success. In this backend, `SETTING Code` receives
0 on success or 128 for an invalid descriptor. `ON ERROR` runs on failure.
A failed DELETE with neither clause terminates with the source location.
[DELETE](https://jbc-lang.org/pages/delete.html).

CLEARFILE removes every record from the selected in-memory file. Its
descriptors stay open for subsequent reads and writes. Use `CLEARFILE F`
for an explicit descriptor or bare `CLEARFILE` for the default file.
jbcc sets the optional `SETTING` variable to the empty string on success,
consistent with the guide’s example, or to 128 for an invalid descriptor.
`ON ERROR` handles failure in the same way as for DELETE.
[CLEARFILE](https://jbc-lang.org/pages/clearfile.html).

READV reads one field from a record. `READV R FROM F, Key, 2 ELSE STOP`
reads the second field, including any value and subvalue marks inside it.
Omit `F,` to use the default descriptor. An existing record takes THEN,
including when the requested field is absent and R receives an empty string.
For field zero, jbcc uses the `readv0=key` convention. A missing record or
invalid descriptor clears R, sets the optional status to 128, and takes ELSE.
Status is empty on success. READV reserves ON ERROR for incremental file
errors other than 128. [READV](https://jbc-lang.org/pages/readv.html),
[jBASE emulation settings](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/sup12_EMULATION.htm).

MATREAD fills a dimensioned array from a record in the selected in-memory
file. For example, `MATREAD A FROM F, Key SETTING N ELSE STOP` splits the
record on field marks, varying the last matrix subscript fastest. The final
element receives any excess fields with their separators intact. A short
record clears the unused elements. On success N counts all record fields,
including those packed into the final element. jbcc counts an empty record
as zero fields. A missing record preserves the matrix, sets N to 128, and
takes ELSE. Omitting `F,` uses the default descriptor. The in-memory backend
supports ON ERROR with the same status handling as READV. Record locking
remains outside this backend. [MATREAD](https://jbc-lang.org/pages/matread.html).

MATWRITE joins the initialized, one-based elements of a matrix with field
marks and writes the resulting record. `MATWRITE A TO F, Key` writes to
an explicit descriptor. `MATWRITE A ON Key` uses the default descriptor.
The last subscript varies fastest. jbcc interprets a successful `SETTING`
as the field count of the serialized record, including embedded and trailing
field marks. An empty record counts as zero. An invalid descriptor yields
128 and skips the optional `ON ERROR` arm, as specified by the guide.
[MATWRITE](https://jbc-lang.org/pages/matwrite.html).

File SELECT starts an independent cursor over the keys of an open in-memory
file. `SELECT F TO L` creates a named list, and `SELECT` uses the default file
and list. Lists numbered 0 through 10 are supported, including a number held
in a variable. File keys are visited in insertion order. Keys added during
iteration are eligible until READNEXT first reports exhaustion. Deleting
an unread key skips it. Reselecting starts a fresh iteration.

`READNEXT Key FROM L THEN ... ELSE ...` returns one key, and
`LOOP WHILE READNEXT Key FROM L DO` uses the same operation as a Boolean
expression. On exhaustion jbcc clears the destination and returns false.
For ordinary keys the optional multi-value position is zero.

With an explicit string or dynamic array, SELECT makes a list of its fields
in source order. Value and subvalue marks stay inside their fields. Leading,
interior and trailing empty fields are entries. jbcc treats a completely
empty source as an empty list. Reassigning the source leaves the selected
fields available to READNEXT. A standalone `//` line, as used in the
guide’s CLEARSELECT example, is accepted as a separator. [SELECT](https://jbc-lang.org/pages/select.html),
[READNEXT](https://jbc-lang.org/pages/readnext.html).

CLEARSELECT discards one cursor. Bare `CLEARSELECT` clears the default
list (0). A named list, a list number, or a variable holding the number
selects the cursor to clear. Other cursors keep their positions, and the
file retains its records. The guide gives CLEARSELECT a range of 0 through
11 and SELECT a range of 0 through 10. Clearing an inactive list is safe
to repeat. [CLEARSELECT](https://jbc-lang.org/pages/clearselect.html).

## Search a dynamic array

`FIND key IN record, occurrence SETTING field,value,subvalue` searches
for a byte-for-byte match in a dynamic array. Positions start at one.
The occurrence defaults to one, and the value and subvalue outputs are
optional. A match writes the positions and takes the THEN branch. On a
miss, jbcc takes the ELSE branch and leaves the outputs as they were,
following the guide’s examples with preassigned positions. Empty elements
can match an empty key. [FIND](https://jbc-lang.org/pages/find.html).

`FINDSTR` uses the same syntax and returns the same coordinates for a
case-sensitive substring within an element. For example, searching for
`XY` in `'ABC' : @VM : 'XYZ'` returns field 1, value 2, subvalue 1.
In jbcc, each matching element counts once, and an empty key matches
every element. These two edge cases are provisional pending a reference
run. [FINDSTR](https://jbc-lang.org/pages/findstr.html).

`LOCATE key IN record SETTING pos THEN ... ELSE ...` searches fields.
Use `record<field>` to search values in a field and `record<field,value>`
to search subvalues. An optional comma and starting position restrict the
search. Positions are one-based within the selected dimension.

T24 also uses `record<field,value,start>`. jbcc treats its third expression
as the first subvalue to search. For example, with subvalues `A,B,A`,
starting at 2 finds `A` at position 3. The reference parser accepts a third
selector and passes it to the runtime separately from the comma-start
argument. Its runtime behavior is provisional pending a reference run.
Supplying both starts produces a compiler diagnostic.

A match sets `pos` and takes the THEN branch. An unordered miss sets it
one past the end. With `BY`, a miss returns the insertion position for
an already sorted array. jbcc supports AL/DL (byte order), AR/DR
(right-justified), and AN/DN (numeric). Either branch can use `NULL`
as a no-op. This implements the guide's `IN ... SETTING` form with
byte-oriented strings. [LOCATE](https://jbc-lang.org/pages/locate.html).

## Check whether a variable has a value

`ASSIGNED(X)` returns 1 after X receives any value, including zero or an
empty string. `UNASSIGNED(X)` returns the opposite. Both can inspect a
scalar, a COMMON variable, a routine argument, or a dimensioned matrix
element. Testing a variable leaves it untouched. For example,
`IF UNASSIGNED(X) THEN X = ''` supplies a default while preserving any
existing value. [ASSIGNED](https://jbc-lang.org/pages/assigned.html),
[UNASSIGNED](https://jbc-lang.org/pages/unassigned.html).

## Walk a dynamic array

`REMOVE item FROM record SETTING mark` reads the next delimited string.
For `record = 'a' : @FM : 'b'`, successive calls return `a` with mark 2,
then `b` with mark 0. Further calls return mark 0 and leave `item`
unchanged. Bytes 255 through 249 give delimiter codes 1 through 7.

The cursor belongs to the variable. Assigning `record = record` rewinds it,
and copying the value to another variable starts an independent traversal.
COMMON variables, matrix elements and by-reference arguments preserve their
own cursor across calls. [REMOVE in the jBASE manual](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_REMOVE.htm).

## User-defined functions

Declare a function before its first use with `DEFFUN DOUBLE.IT()`. Parameter
names in a declaration are optional. The compiler checks each call against
the supplied `FUNCTION` definition. As with `CALL`, scalar variables and
matrix elements are passed by reference and expressions use temporary slots.
Pass a whole matrix with `CALL UPDATE(MAT Rows)` or `F(MAT Rows)`, and
declare the receiving parameter with `MAT` in SUBROUTINE or FUNCTION.
The callee uses the caller’s storage and bounds, including for COMMON
matrices and calls that forward the parameter. When a DEFFUN lists
parameters, mark its matrix parameters with MAT as well. T24 routines
often repeat DIM for a MAT parameter. Pending a reference run, jbcc
checks that such a declaration matches the caller’s dimensions exactly.

```sh
./jbcc --exe tests/routines/function.caller.b tests/routines/DOUBLE.IT -o /tmp/function-caller
/tmp/function-caller
```

The caller prints `43` from `1 + DOUBLE.IT(21)`. The function returns
`N * 2` through a hidden result argument. A bare `RETURN` gives an empty
string. The example follows the calling convention in the
[DEFFUN](https://jbc-lang.org/pages/deffun.html) and
[FUNCTION](https://jbc-lang.org/pages/function.html) chapters.

## Check a local source corpus

The coverage goal is to translate every program, subroutine and function in
the local T24 sources to valid C99, expanding include fragments wherever
they are used. The latest counts and the next language feature are in
[the compiler plan](PLAN.md).

```sh
python3 tools/check_corpus.py ~/Downloads/t24 -j 8 > /tmp/jbcc-corpus.json
```

The checker visits regular files recursively. It counts `I_` files as include
fragments and expands them when referenced by a compilation unit. It runs
the compiler's preprocessor, parser and C generator on each remaining file.
For external calls it declares the observed signature so that the system C
compiler can check the complete generated unit with C99 warnings as errors.
Additional include directories can be supplied with `-I`.

The JSON report records a status per relative path, diagnostic locations,
and counts by first blocker. A translated unit passed C syntax checking.
Linking its external dependencies and verifying its behavior require separate
tests. UTF-8 decoding failures are counted separately.

## Test corpus

```sh
python3 -B -m unittest discover -s tests -v
```

Each `tests/snippets/*.b` has a sibling `.stdout` file. The tests invoke
the CLI, compile with strict C99 warnings, run the binary and compare output
byte for byte. They also exercise translation errors and runtime errors.
The expected outputs are project expectations. The conversion and printing
rules draw on the guide's [string variables](https://jbc-lang.org/pages/string_variables.html),
[numeric variables](https://jbc-lang.org/pages/numeric_variables.html) and
[CRT](https://jbc-lang.org/pages/crt.html) chapters. Operator ordering follows
the [jBC grammar](https://github.com/jbc-lang/jbc-language/blob/master/spec/jbc.y).
These snippets have yet to be run on a reference jBC implementation.

### Whole-program fixtures

- `quine.b` reproduces its source byte for byte, including the semicolon
  between statements and the final newline. The native test compares stdout
  directly with the source file.
- `banner.b` animates a 24-by-79 character display until a key is available.
  It exercises dimensioned arrays, substring assignment, fractional
  arithmetic, trigonometry, and terminal I/O. Build it with
  `./jbcc --exe tests/programs/banner.b -o /tmp/banner`. Run `/tmp/banner` in an
  ANSI terminal and enter a line to stop. The native test captures the blank
  opening frame and checks every pixel of the next frame before sending input.

SIN and COS take degrees. INT truncates toward zero. Explicit two-argument
substring selection and replacement use one-based byte positions (negative
positions count from the end). Terminal support covers ANSI cursor-home
`@(-2)` and POSIX pending input `SYSTEM(14)`; the latter follows the input
device's line discipline. Native mode links the math library for programs
that use trigonometry. When compiling their generated C manually, use
`cc -std=c99 banner.c -lm -o banner`. [SIN](https://jbc-lang.org/pages/sin.html),
[COS](https://jbc-lang.org/pages/cos.html), [INT](https://jbc-lang.org/pages/int.html).

## Evidence for the implementation

The [grammar investigation](https://github.com/jbc-lang/jbc-language/pull/11)
contains two token grammars, a lexer keyword table and a function catalogue.
The preprocessor handles includes, equates and macros. The main parser handles
statements and expressions. Some scanner decisions depend on declarations or
parser state, so the grammar alone cannot tokenize raw source.

Use the [Programmers Reference Guide](https://jbc-lang.org/) for documented
syntax, output examples and dialect notes. Record the source of each test
expectation. A locally available T24 corpus can tell us which constructs
occur together and how often. Executable snippets with independently checked
output are the evidence for runtime behavior.

## After the first milestone

Use the first-blocker counts to prioritize further compiler work. WebAssembly
remains a possible playground target.
