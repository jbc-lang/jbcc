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

Single-line and multiline IF support THEN, ELSE, and nested branches.
Close a multiline arm with END and start its alternative with END ELSE.
Comparisons return 1 or 0. Two decimal strings compare numerically;
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
Whole-matrix (`MAT`) parameters are outside the current subset.

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
