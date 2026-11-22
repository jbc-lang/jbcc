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

Use scalar assignment, CRT with one expression, unsigned decimal integer
literals, quoted strings (single, double or backslash delimiters),
parentheses, addition and concatenation. Addition binds more tightly than
concatenation. Names are case-sensitive. Variables must be assigned on every path reaching a use. Separate statements with a newline or semicolon. A statement beginning
with `*`, `!` or `REM` comments out the rest of its line.

The generated file includes the C runtime. It keeps immutable string values
alive until program exit, so assignment preserves a copied value. Addition
converts its operands to signed 64-bit decimal integers and reports invalid
input or overflow at the operator. These limits are provisional. Decimal
fractions in arithmetic and API calls are outside the current subset.

Single-line and multiline IF support THEN, ELSE, and nested branches.
Close a multiline arm with END and start its alternative with END ELSE.
Comparisons return 1 or 0. Two decimal strings compare numerically;
other pairs compare in byte order. Numeric zero and the empty string are
false. This subset uses exact decimal comparison without PRECISION rounding.
See the [Boolean variables](https://jbc-lang.org/pages/boolean_variables.html)
and [IF](https://jbc-lang.org/pages/if_statement.html) chapters.

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

`tests/programs/` contains two user-supplied programs for manual compiler
checks. Try either with `./jbcc tests/programs/quine.b -o /tmp/quine.c`,
substituting `demo.b` for the animation.

- `quine.b` exercises same-line statements, `CHAR`, and concatenation.
  Its source separates the assignment and CRT with a semicolon, while
  `CHAR(58)` prints a colon at that position. A byte-for-byte comparison
  with its source would therefore be an incorrect output test.
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

Continue the standalone-program milestones in [PLAN.md](PLAN.md). Once native
execution is repeatable, evaluate compiling the same generated C and runtime
to WebAssembly for a browser playground.
