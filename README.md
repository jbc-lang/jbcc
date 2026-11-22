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

Concatenating assignment appends the right-hand value as a string.
For example, after `S = 'QWERTY'`, `S := 123` gives `QWERTY123`.
It also works on matrix elements, dynamic-array fields and substrings.
[String variables](https://jbc-lang.org/pages/string_variables.html).

The generated file includes the C runtime. Values are immutable strings. Assignment preserves a copied value, and loop
boundaries reclaim temporary values that are no longer in use. Integer addition, subtraction and multiplication check signed 64-bit
overflow. Division and fractional arithmetic use native long double,
rounding results to at most 15 fractional places by default. Division by zero reports the operator location.

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

For dates, the OCONV mask `D` produces `DD MON YYYY`. A digit from 0 through 4 selects the
year width. With a separator (`-`, `/` or `.`), jbcc follows the guide’s
worked example and observed T24 usage. For example, `OCONV(16454,'D4/')` returns
`01/17/2013`. Append `E` for day-first order. The guide’s syntax table
instead describes day-first order for the plain numeric form. Component
masks include `DD`, `DM`, `DMA`, `DJ`, `DQ`, `DW`, `DWA`, and `DY` with
optional year width. The runtime accepts Gregorian years 1 through 9999
and reports unsupported masks at the call site. [DATE](https://jbc-lang.org/pages/date.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

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
that slot by reference. Unassigned reads and out-of-range subscripts produce
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
pending a reference run. Runtime bounds are supported for COMMON matrices. The current initialization policy leaves slots unassigned until
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
- `DEL R<field[,value[,subvalue]]>` removes the selected component and
  closes the gap between its siblings. The target can be an assigned scalar
  or a matrix element. Fractional positions truncate toward zero. A missing
  or nonpositive position leaves the array intact, and a nonnumeric index
  raises a runtime diagnostic. [DEL](https://jbc-lang.org/pages/del.html)
- Define a local label with a trailing colon, including inside IF, CASE,
  LOOP and FOR bodies. GOTO can jump within or leave a FOR. A jump that
  would enter a FOR without executing its header gets a source diagnostic.
  GOSUB starts a fresh control-flow invocation and shares
  the routine's variables and supports nested returns. Execution falls through
  labels encountered sequentially. STOP terminates the program. [GOSUB](https://jbc-lang.org/pages/gosub.html)
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

## In-memory file tests

The test backend starts with empty files explicitly named at translation
time. Each execution starts fresh. To run the example:

```sh
./jbcc --memory-file CUSTOMERS tests/io/records.b -o /tmp/records.c
cc -std=c99 /tmp/records.c -o /tmp/records
/tmp/records
```

OPEN a name TO a descriptor, READ a variable FROM a descriptor and key,
and WRITE a value ON or TO a descriptor and key. The supported forms use
explicit descriptors. OPEN and READ require THEN or ELSE. WRITE can be
unconditional or use a success or failure branch. In this backend a failed
open or read clears its destination. An unhandled failed WRITE terminates
with a source location. Stored records survive reassignment and loop
temporary cleanup. Default descriptors, disk storage, locking, SETTING and
ON ERROR remain outside this test backend.
[OPEN](https://jbc-lang.org/pages/open.html), [READ](https://jbc-lang.org/pages/read.html),
[WRITE](https://jbc-lang.org/pages/write.html).

## Search a dynamic array

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
