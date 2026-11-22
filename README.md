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

The source assigns `"2"` to N. The first CRT adds 3 and prints `5`.
The second concatenates 3 and prints `23`. Each output ends in a newline.

## Implemented subset

Use scalar assignment, PRINT and CRT, decimal numeric
literals, quoted strings (single, double or backslash delimiters),
parentheses, arithmetic, concatenation, and compound assignments (+= and -=). Addition binds more tightly than
concatenation. Names are case-sensitive. Variables must be assigned on every path reaching a use. Separate statements with a newline or semicolon. A statement beginning
with `*`, `!` or `REM` comments out the rest of its line.

The generated file includes the C runtime. Values are immutable strings. Assignment preserves a copied value, and loop
boundaries reclaim temporary values that are no longer in use. Integer addition, subtraction and multiplication check signed 64-bit
overflow. Division and fractional arithmetic use native long double,
rounding results to at most 15 fractional places. This precision is a
provisional project choice. Division by zero reports the operator location.

Single-line and multiline IF support THEN, ELSE, and nested branches.
Close a multiline arm with END and start its alternative with END ELSE.
Comparisons return 1 or 0. Two decimal strings compare numerically;
other pairs compare in byte order. Numeric zero and the empty string are
false. This subset uses exact decimal comparison without PRECISION rounding.
See the [Boolean variables](https://jbc-lang.org/pages/boolean_variables.html)
and [IF](https://jbc-lang.org/pages/if_statement.html) chapters.

PRINT and CRT write to standard output. Commas separate items with tabs.
A final colon suppresses the newline. A bare PRINT or CRT emits a newline.

FOR supports inclusive bounds, a default step of one, optional STEP,
and an optional variable name after NEXT. The limit and step are evaluated
at the start of each iteration. The captured step increments the counter
after the body. LOOP allows WHILE and UNTIL guards before or after other
statements, including on the same line. FOR also accepts a WHILE or UNTIL
guard in its header. See the [FOR](https://jbc-lang.org/pages/for.html) and
[LOOP](https://jbc-lang.org/pages/loop.html) chapters.

## Compile a T24-style routine

Pass one main program and its subroutine source files to the same command.
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
- Define a local label at routine scope with a trailing colon. GOSUB shares
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
LEN counts bytes in the current byte-oriented runtime. FIELD accepts a
one-based occurrence and optional field count. FIELD, COUNT and DCOUNT
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

## Check a local source corpus

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
- `demo.b` animates a 24-by-79 character display until a key is available.
  It exercises dimensioned arrays, substring assignment, fractional
  arithmetic, trigonometry, and terminal I/O. A future automated run
  needs bounded input or a frame limit.

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
