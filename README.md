# jbcc

jbcc is an experimental jBC-to-C compiler prototype. Its grammar has been
tested against the T24 R07, R10 and R13 source corpora. Some system calls are
stubbed, and development and testing take place mainly on macOS. The
translator is written in Python 3 and emits standalone C99 that the system C
compiler can build into a native executable.

jbcc is an independent, from-scratch reimplementation of the jBASE compiler.
Its parser supports the jBC grammar exercised by the T24 source corpus.
Parts of the jBASE runtime are still to be implemented.

The [jBC API coverage report](COVERAGE.md) shows which API forms were
exercised by compiling the T24 R13 corpus and links to available runtime
tests. Some APIs may already be implemented while their runtime behavior
still awaits verification.

The [jBC language reference repository](https://github.com/jbc-lang/jbc-language)
maintains the programmer’s guide, grammar, and function catalogue.

## Playground

Open the [online jBC playground](https://online.jbc-lang.org/) to edit a
multi-file project. The browser compiles and runs your code and saves
projects locally.

The [jbc-playground repository](https://github.com/jbc-lang/jbc-playground)
maintains the site, browser tests, and local development commands.

## Compiler performance

On a 10-core Apple M5 Mac with eight workers, the
[corpus checker](#check-a-local-source-corpus) scanned each extract,
translated its source units to C, and syntax-checked the output with
Apple Clang. These runs used the documented corpus compatibility options,
including in-memory source fixes, the R07 include stub, the R13
local-routine exclusion and, for R19, the
[T24 corpus flags](#t24-corpus-flags).

| T24 release | Files scanned | Source units translated and checked | Wall time |
| --- | ---: | ---: | ---: |
| R10 | 22,474 | 17,336 | 2 min 18 s |
| R07 | 18,362 | 15,030 | 2 min 2 s |
| R13 | 25,374 | 19,536 | 2 min 53 s |
| R19 | 39,675 | 39,669 | 4 min 59 s |

The R07, R10 and R13 file totals also count headers and include
fragments. The R19 total counts the catalogued production units only;
its includes are resolved through the catalog, and 6 units are excluded
because their generated inserts have no `.domain` class.

## What is jBC?

jBC is a dialect of BASIC developed for the jBASE MultiValue database
system. It follows the Pick BASIC tradition and has built-in operations
for working with MultiValue records.
[jBASE BASIC documentation](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/jbase_basic_jbc_.html).

Temenos used jBC in its T24 core banking software.
[jBC Programmer’s Reference Guide](https://jbc-lang.org/).

## A quick taste of jBC

[rule110.b](tests/programs/rule110.b) prints 32 generations of the Rule 110
cellular automaton. It starts with a single live cell and prints each
generation as a row of `#` and `.` characters. `DIM` declares the arrays,
`MAT` fills or copies them, and `CRT` prints each row.

```basic
EQUATE width TO 63
EQUATE generations TO 32

* The extra cell at each end stays dead.
DIM cells(width + 1), next_cells(width + 1)
MAT cells = 0
MAT next_cells = 0
cells((width + 1) / 2) = 1

* Rule 110 in binary, ordered from neighborhood 111 down to 000.
rule = '01101110'

FOR generation = 1 TO generations
  row = ''
  FOR x = 1 TO width
    IF cells(x) THEN
      row := '#'
    END ELSE
      row := '.'
    END

    neighborhood = 4 * cells(x - 1) + 2 * cells(x) + cells(x + 1)
    next_cells(x) = rule[8 - neighborhood, 1]
  NEXT x
  CRT row
  MAT cells = MAT next_cells
NEXT generation
```

More examples in jBC

- [hello.b](tests/programs/hello.b) prints “Hello, jBC!”
- [life.b](tests/programs/life.b) animates Conway’s Game of Life.
- [snake.b](tests/programs/snake.b) lets you play Snake with the WASD keys.
- [banner.b](tests/programs/banner.b) animates a waving jBC banner.

## Browser translation API

Import `translate`, `Diagnostic`, `SourceLimitError`, and `read_runtime`
from `jbcc.browser`. Call `translate(paths, include_resolver=resolver)`
with a sequence of `pathlib.Path` values. Put the main program first,
followed by any linked subroutines and functions. The compiler reads UTF-8
source and returns a standalone C translation with the packaged runtime
included. `read_runtime()` returns that runtime as C source when needed on
its own. A separate C compiler builds the generated source for WASI.

The resolver receives `(including_path, include_name, line, column)` and
returns a `Path` or `None` if the include is missing. Lines and columns are
one-based. The caller controls filesystem access and include lookup.
`include_depth` optionally limits nesting. `source_filter(path, text)`
can inspect or replace the decoded source of each unit and each expanded
include. It can raise `SourceLimitError` to abort when a workspace budget
is exceeded.

`emulation` selects the jBASE emulation, `'prime'` (default) or
`'jbase'`, as the `--emulation` option does.

Translation errors raise `Diagnostic` with source locations where
available. `SourceLimitError` is a subclass of `Diagnostic`. Compiler
warnings go to standard error. The caller handles browser-specific
concerns such as project JSON, staging files, and UI diagnostics.

## Try the compiler

You need Python 3.8 or newer to run jbcc. Using `uv` is recommended for
managing Python and running the developer tools. Native builds also need
a C99 compiler on `PATH`, such as Clang or GCC. jbcc uses `cc` by default.

Run [jbcc from PyPI](https://pypi.org/project/jbcc/) with `uvx` from any
working directory. uv downloads the compiler on demand.

```sh
printf '%s\n' 'CRT "Hello, jBC!"' > hello.b
uvx jbcc --run hello.b
```

From a source checkout, `uvx` can also run the local compiler.

```sh
uvx --from . jbcc --run tests/programs/hello.b
```

From the checkout, build and start the banner animation. Press Enter to stop it.

```sh
./jbcc --exe -o banner tests/programs/banner.b && ./banner
```

Use `--run` to build and launch in one command. By default, jbcc removes the
temporary executable after the program exits. Use `-o` to keep it.

```sh
./jbcc --run tests/programs/banner.b
./jbcc --run -o banner tests/programs/banner.b
```

To inspect the generated C, try the coercion example.

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
with the resulting arguments. Add `-v` (or `--verbose`) to print each external
command to stderr before it runs. With `--run`, jbcc returns the program's
exit status.

Source files and their includes are read as strict UTF-8 by default.
Use `./jbcc --source-encoding bytes legacy.b -o /tmp/legacy.c` for
legacy input. This mode preserves the original bytes in string literals,
including single-byte jBC delimiters, and accepts legacy punctuation in
comments. It applies to every source and include in the invocation.
A UTF-8 decoding diagnostic identifies the failing file and position.
The lexer skips NUL bytes in comments and inactive source lines. NUL
bytes in active code, literals or include paths report a source location;
TAFC PB201214 rejects a NUL byte in a literal as a syntax error too. Use
`CHAR(0)` for byte 0.

Use `--defer-unassigned-reads` for legacy code that reads a scalar before
jbcc can establish an assignment. This opt-in turns that compile-time
diagnostic into a warning. If execution reaches the read of an unassigned
variable, the runtime warns, assigns and uses an empty string, and goes on,
as TAFC PB201214 does (`Invalid or uninitialised variable -- NULL USED`).
Unknown function calls remain compile errors. Without the option, jbcc
still rejects a read it can prove unassigned, where TAFC compiles it with
a warning.
Compound assignments such as `+=` and `:=` also check the target's old
value at runtime under this option.

The source assigns `"2"` to N. The first CRT adds 3 and prints `5`.
The second concatenates 3 and prints `23`. Each output ends in a newline.

## Just recipes

[LANGUAGE-GAPS.md](LANGUAGE-GAPS.md) lists what jbcc does not do yet, or does
only provisionally.

[MISSING-BACKENDS.md](MISSING-BACKENDS.md) lists the features that parse and
translate but need a service jbcc does not have, such as persistent files,
XML, ciphers or a JVM, with how often T24 uses each.

[RELEASING.md](RELEASING.md) lists the steps of a release, from the
version bump to the playground, the guide and the organisation page.

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
just corpus ../t24-extract/201001-R10 > /tmp/jbcc-corpus.json
```

## Emulation

jBASE, and TAFC with it, runs jBC under an emulation of an older
MultiValue system, chosen by the `JBCEMULATE` environment variable and
defined in TAFC's `config/Config_EMULATE`. T24 runs under `prime`, and its
code depends on it: all 214 function-form CONVERT calls in the R13 and
R19 corpora use the prime argument order. TAFC applies some emulation
switches when it compiles a program and others when the program runs.
jbcc fixes the emulation when it translates. The generated program does
not read `JBCEMULATE`.

`--emulation prime` (the default) and `--emulation jbase` select it. The
emulation decides:

- the argument order of the CONVERT function;
- what `LOCATE x IN array<...>` searches, and the order of `BY 'AR'`;
- the MATCH and MATCHES pattern codes.
- whether a division by zero warns and continues (prime) or stops the
  program, as TAFC's debugger does without a terminal (jbase).

These rules come from TAFC PB201214 runs under both emulations; the
probes are in `tests/tafc/` ([TAFC-CROSSCHECK.md](TAFC-CROSSCHECK.md),
section 1). Other rules in this README follow the guide's prime-emulation
examples unless they say otherwise.

## Implemented subset

Use scalar assignment, PRINT and CRT, decimal numeric
literals, quoted strings (single, double or backslash delimiters),
parentheses, arithmetic, concatenation, and compound assignments. A trailing
backslash or ellipsis joins the next source line, including when a semicolon
comment follows the continuation marker.

The reference lexer accepts spaces and tabs before the equals sign in `+=`,
`-=`, `*=` and `/=`. For example, `R<1> + = 1` increments the first field, a
form used in T24.

An assignment target may have whitespace before the opening angle bracket.
Both `T.SEQU <-1> = A+1` and `T.SEQU < - 1 > = A + 1` append a field. The
reference grammar allows one to three indices followed by an optional
substring selector. Reads also allow whitespace, as in `X = R <FIELD>` and
`LOCATE X IN R <FIELD> SETTING POS`.

The reference preprocessor pairs angle brackets within an expression and
checks for intervening logical operators. jbcc keeps a spaced comparison
chain such as `A < B > C` when an operand follows the closing bracket.
Before a binary operator, `R <1> + 3` reads field one and adds three. Use
`LT` and `GT` to make ambiguous comparisons explicit.

The reference preprocessor spells LE as `#>`, GE as `#<`, and NE as `><`
with a space or tab before it. For example, `R<1> >< R<2>` compares two
fields and `R<1><2>` chains selectors. A greater-than sign and equals sign
can be separated by spaces or tabs when the greater-than sign is a
comparison. After a field selector, `R<1> = X` still uses the single equals
operator.

The reference lexer spells concatenating assignment `:=`. jbcc also accepts
spaces or tabs before the equals sign in this operator, following usage in
T24. A compound assignment to a conditionally assigned scalar checks the
previous value at runtime. This includes updates to a dynamic-array field in
that scalar. Addition binds more tightly than concatenation.

Names are case-sensitive and can contain `%` after the first letter. Reads
require an assigned value. An expression can read a scalar assigned on some
paths through a prior conditional or loop. jbcc checks the value at runtime,
so a later guard can protect that read. A FOR body can be skipped by its
bounds or its guard. Routines with GOTO, GOSUB or RETURN TO also check reads
at runtime because jumps can bypass assignments.

Separate statements with a newline or semicolon. A statement beginning with
`*`, `!` or `REM` comments out the rest of its line. These markers can
follow a named or numeric label directly, as in `setup:* read inputs` or
`100: REM retry`.

`END:` can label a statement, including inside a block. A bare `END` closes
a block or terminates the source unit. A stray `END` after the final one
is ignored with a warning, as the local reference compiler does (warning
47, "END is misplaced"), while other text there is an error. A single `.` at the start of a
physical line can stand alone or label a statement on that line, with an
optional colon. A digit-only label at the start of a source line can also
omit the colon, including before a comment or statement. Separate the digits
from a following statement with whitespace or a semicolon. A standalone
EQUATE reference that expands to digits works the same way. Leading zeros
are part of the label.

`CAT` is another spelling of the concatenation operator `:` and has
the same precedence. An omitted right operand keeps the left value.
For example, `X = 'a':` stores `a` and `X = 'a'::'b'` stores
`ab`. Within CRT, DISPLAY or PRINT, an omitted operand also suppresses
the statement's final newline, including when the operator occurs inside
a nested expression or between output arguments. In an INPUT length,
the same rule suppresses the input newline. This follows the reference
parser's `resultant ':'` production.
[jBASE CRT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_crt.htm).

Each comma in CRT, DISPLAY or PRINT emits a tab. Leading and repeated
commas can stand on their own. A comma at the end of a physical line
also continues the statement onto the next source line. At the end of
the source, a final output comma emits its tab before the newline.

`CLEAR` assigns numeric zero to local scalars, including locals first
mentioned later in the source. It preserves caller arguments and
COMMON storage. jbcc provisionally also zeroes allocated local matrix
elements, including index zero, and leaves their dimensions intact.
A runtime-sized matrix still needs its declaration to execute before use.
[CLEAR](https://jbc-lang.org/pages/clear.html).

`CHANGE old TO new IN target` replaces nonoverlapping substrings from left
to right in an assigned scalar, matrix element or dynamic-array field.
The original grammar also accepts `WITH` in place of `TO`. The function
`CHANGE(text, old, new [, count [, first]])` returns a new value. Counting
starts at one. A count below one replaces all remaining matches, and a
starting occurrence below one starts at the first match. An empty replacement
deletes matches. jbcc leaves the input intact for an empty search string.
[CHANGE](https://jbc-lang.org/pages/change.html).

`EREPLACE(text, old, new [, count [, first]])` uses the same occurrence
rules. An empty search string leaves the text unchanged, as TAFC PB201214
does and as the guide records for TAFC R23; jBASE documents, and TAFJ
R23 shows, a prefixed replacement instead. The reference lexer also accepts
`EREPLACE old TO new IN target` as a spelling of the CHANGE statement.
[jBASE EREPLACE](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_EREPLACE.htm).

`SWAP(text, old, new [, count [, first]])` returns a new value using
the same rules as the CHANGE function. The reference compiler accepts
expressions in the first argument and supports both optional arguments.
`SWAP old TO new IN target` updates the target in place, with `WITH`
also accepted in place of `TO`.
[jBASE SWAP](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SWAP.htm).

Concatenating assignment appends the right-hand value as a string.
For example, after `S = 'QWERTY'`, `S := 123` gives `QWERTY123`.
It also works on matrix elements, dynamic-array fields and substrings.
[String variables](https://jbc-lang.org/pages/string_variables.html).

Standalone `V++`, `V--`, `++V`, and `--V` change an assigned
variable or matrix element by one. They use the same numeric coercion
as compound assignment. The reference grammar
uses scalar and matrix targets for these statements.
In expressions, a prefix operator returns the updated value and a
postfix operator returns the previous value. jbcc evaluates operands
from left to right, including when they refer to the same variable.
[Numeric variables](https://jbc-lang.org/pages/numeric_variables.html).

The generated file includes the C runtime. Values are immutable strings. Assignment preserves a copied value, and loop
boundaries reclaim temporary values that are no longer in use.

Arithmetic is exact decimal arithmetic at the PRECISION in force, 4
places unless a PRECISION statement says otherwise, as in TAFC PB201214
([TAFC-CROSSCHECK.md](TAFC-CROSSCHECK.md), "TAFC's number model"):

- each operand is rounded half away from zero to PRECISION places, so
  `0.00004 + 0.00004` is 0 and `0.06245 * 1` is 0.0625;
- `+` and `-` are then exact, and `*` and `/` truncate the exact result
  toward zero, so `2/3` is 0.6666, `1/7*7` is 0.9996 and
  `0.5555 * 0.5555` is 0.3085;
- integers have no size limit, so `99999999999999999999 + 1` is exact;
- under prime emulation, spaces and tabs around a number are ignored.

Results print without trailing fractional zeros and never as `-0`.
Comparisons and truth tests round numeric operands the same way, so
`'0.33333' = '0.3333'` is true at PRECISION 4.

As in TAFC, arithmetic does not stop on bad operands. An empty string, a
lone sign or a lone point is 0. Any other operand that is not a decimal
number, such as `'abc'`, `'1E3'` or a dynamic array under prime, warns
`Non-numeric value -- ZERO USED` at the operator and counts as 0. Division
by zero, including `DIV` and `/=`, warns at the operator and gives 0.
jbcc writes these warnings to stderr; TAFC writes them to stdout. TAFC keeps a numeric literal at the unit's first
PRECISION when a later PRECISION statement lowers it; jbcc rounds it at
the PRECISION in force (`tests/snippets/precision.b`).

`DIV(dividend, divisor)` returns the fractional quotient with the same
PRECISION rules as `/`. The guide specifies an empty result if either
operand is empty. jbcc applies that rule before numeric validation and
reports a zero divisor at the DIV call for nonempty operands.
[DIV](https://jbc-lang.org/pages/div.html).

`DROUND(value[, places])` rounds decimal values and removes trailing
fractional zeros. It defaults to four places whatever the PRECISION, as
TAFC PB201214 does (`DROUND(1.235)` is 1.235 at PRECISION 2). An
explicit nonnegative integer overrides that default. Rounding is exact
decimal rounding with midpoint ties away from zero.
[jBASE DROUND](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_DROUND.htm).

`SMUL(left, right[, places])` multiplies decimal strings exactly before
limiting the output scale, so products can exceed the native integer range.
It ignores the active PRECISION, truncates toward zero to 14 fractional
places and removes trailing fractional zeros, as TAFC PB201214 does
(`tests/tafc/string-math*.b`); the guide prints 16 places for its
fractional example. The reference
grammar accepts a third argument. jbcc treats it as a nonnegative
fractional limit and accepts `-1` for the default.
[jBASE SMUL](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SMUL.htm).

`SDIV(dividend, divisor[, places])` divides decimal strings without
native floating-point conversion. It ignores the active PRECISION.
The guide describes rounding to 14 fractional places. Its `SDIV(2, 3)`
example gives `0.66666666666666`. jbcc follows that example and
provisionally truncates toward zero at the selected limit.
The optional nonnegative integer sets that limit, and omitting it or
passing `-1` selects 14. Trailing fractional zeros are removed. A zero
divisor reports an error at the call.
[SDIV](https://jbc-lang.org/pages/sdiv.html).

`ALPHA` and `ISALPHA` return 1 when every byte in a nonempty value is an
ASCII letter. `ISDIGIT` returns 1 for nonempty values made entirely of
ASCII digits, and `ISALNUM` for values made entirely of ASCII letters and
digits. `ISUPPER` and `ISLOWER` test for ASCII upper- and lower-case
letters, and `ISSPACE` for space, tab, line feed, vertical tab, form feed
and carriage return. Signs, decimal points, spaces and array marks return 0
from `ISDIGIT`. jbcc provisionally returns 0 for an empty string with
these character tests. The guide describes Unicode classification
separately under International Mode.
[ALPHA](https://jbc-lang.org/pages/alpha.html), [ISALPHA](https://jbc-lang.org/pages/isalpha.html), [ISALNUM](https://jbc-lang.org/pages/isalnum.html), [ISUPPER](https://jbc-lang.org/pages/isupper.html), [ISSPACE](https://jbc-lang.org/pages/isspace.html), [jBASE ISDIGIT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_ISDIGIT.htm).

NUM tests whether an expression has numeric text and returns 1 or 0, as
TAFC PB201214 does (`tests/tafc/emulation-rules-*.b`). Signed decimals,
leading zeros and the empty string are numeric; thousands separators,
exponent notation and inner spaces are not. Under prime, spaces and tabs
around a number are skipped (`NUM(' 12')` is 1) and a lone `.`, `+` or `-`
is not a number. Under `--emulation jbase` a lone `.`, `+` or `-` is
numeric and any space is not. [NUM](https://jbc-lang.org/pages/num.html).

`NUMS(array)` applies that test to each element, preserving field, value
and subvalue marks. Empty strings are numeric under the same rules.
[NUMS](https://jbc-lang.org/pages/nums.html).

`NOTS(array)` returns the logical complement of each element and
`LENS(array)` the byte length of each element, preserving the marks.
An empty element is false and has length 0.
[NOTS](https://jbc-lang.org/pages/nots.html), [LENS](https://jbc-lang.org/pages/lens.html).

MOD and REM return the decimal remainder of two numeric expressions.
The reference compiler emits the same runtime call for both. A
statement-leading REM still introduces a comment.
For example, `MOD(12.34, 0.5)` returns `0.34`. A zero divisor returns the original
dividend, as specified in the guide. For signed operands, jbcc uses a
quotient truncated toward zero, so `MOD(-7, 3)` returns `-1`. This sign
rule is provisional pending a reference run. Explicit PRECISION truncates
the nonzero-divisor result after the remainder is computed.
[MOD](https://jbc-lang.org/pages/mod.html).

`PWR(base, exponent)`, `^` and `**` use the same host math operation.
The reference grammar groups powers left to right, so `2 ^ 3 ^ 2` gives
64. Power binds more tightly than multiplication and unary signs.
`-2 ^ 2` gives -4 and `(-2) ^ 2` gives 4. Multiplication also binds inside a unary sign, so
`2 ^ -1 * 2` gives 0.25. The runtime applies explicit
PRECISION to the result. For a negative base with a fractional exponent,
jbcc follows the guide's prose and reports the domain error, returns zero
and continues. The guide also shows `0.0nan` as output, so the exact
diagnostic and rendering remain provisional. Zero raised to a negative
power and overflow produce runtime errors. [PWR](https://jbc-lang.org/pages/pwr.html).

`LN(value)` computes the natural logarithm of a positive number. At
`PRECISION 2`, `LN(3)` prints `1.1`. jbcc rounds to the requested
precision, as it does for EXP. The guide leaves rounding unspecified.
Zero, negative values, nonnumeric text and positive values outside the
host's floating-point range raise a runtime error at the call site.

`FADD`, `FSUB`, `FMUL` and `FDIV` compute in floating point and print
ten significant digits, not PRECISION places: TAFC PB201214 stores their
result as a raw double. So `FSUB(2.54, 5.703358)` prints `-3.163358`, as in
the guide, and at `PRECISION 4` `FSUB(10, 0.00004)` prints `9.99996`. The
reference compiles `FSUB` to its floating-point routine and `-` to its
ordinary subtraction. [FSUB](https://jbc-lang.org/pages/fsub.html).
[LN](https://jbc-lang.org/pages/ln.html).

`EXP(value)` computes the natural exponential with the host's `expl`.
jbcc rounds the result to the requested PRECISION. For example,
`EXP(1)` prints `2.72` at `PRECISION 2`. The guide specifies the number
of decimal places and leaves the rounding rule open. Nonnumeric input
and overflow report errors at the call site. A result that underflows to
zero on the host returns zero. [EXP](https://jbc-lang.org/pages/exp.html).

`SQRT(value)` returns the square root of a nonnegative number. jbcc uses
the host's `sqrtl` and rounds to the requested PRECISION, following the
guide's TAFC output. With `PRECISION 6`, `SQRT(2)` prints `1.414214`.
The guide's prose describes truncation. Negative and nonnumeric operands
raise a runtime error at the call site. [SQRT](https://jbc-lang.org/pages/sqrt.html).

On Unix, `RND(bound)` returns a random integer from zero through
`ABS(bound) - 1`. The bound must be an integer with magnitude at most
2,147,483,647. The native runtime samples from `/dev/urandom` and uses
rejection sampling for bounds that do not evenly divide the sample range.
The guide leaves the zero case unspecified. jbcc provisionally reports a
runtime error at the call to `RND(0)`. [RND](https://jbc-lang.org/pages/rnd.html).

`RANDOMIZE`, `RANDOMIZE()` and `RANDOMIZE(expression)` are compatibility
forms. The reference parser accepts all three and discards the optional
expression without generating a seed operation. jbcc checks the
expression at compile time and skips it at runtime. `RND` continues to
draw from `/dev/urandom`.

`BITAND(left, right)`, `BITOR(left, right)`, `BITXOR(left, right)` and
`BITNOT(value)` take the low 32 bits of each operand's integer part and
return an unsigned 32-bit result, so `BITOR(-1, 0)` is 4294967295 and
`BITNOT(6)` is 4294967289. An empty or nonnumeric operand counts as 0, as
does a value outside the signed 64-bit range. These rules follow a TAFC
PB201214 run (`tests/tafc/bit-unsigned.b`).
[BITAND](https://jbc-lang.org/pages/bitand.html), [BITOR](https://jbc-lang.org/pages/bitor.html), [BITXOR](https://jbc-lang.org/pages/bitxor.html), [BITNOT](https://jbc-lang.org/pages/bitnot.html).

`ENCRYPT(text, key, method)` and `DECRYPT(text, key, method)` implement
three methods of PB201214's JBC.h, as TAFC PB201214 runs them
(`tests/tafc/crypt-base64.b`):

- `JBASE_CRYPT_ROT13` (1) rotates ASCII letters and ignores the key;
- `JBASE_CRYPT_XOR11` (2) XORs byte i, counting from 0, with the key's
  first byte modulo 11 plus i, modulo 32 (an empty key counts as 0);
  ENCRYPT and DECRYPT are the same;
- `JBASE_CRYPT_BASE64` (4) is standard Base64 with `=` padding and no line
  breaks. Decoding skips every character outside the alphabet, padding
  included, and reads the rest as one bit stream, so `'aGVs bG8'` is
  `hello`; the result can hold byte 0.

The `JBASE_CRYPT_BASE64_MASK` bit (`0x40000000`) adds Base64 after
ENCRYPT's method and removes it before DECRYPT's, so
`ENCRYPT('hello', 'k', BITOR(2, XTD('40000000')))` is `YGxmZ2M=`. The
cipher methods (GENERAL, RC2, DES, 3DES, Blowfish and AES) report a
source-located error when called (MISSING-BACKENDS.md).
[ENCRYPT](https://jbc-lang.org/pages/encrypt.html), [DECRYPT](https://jbc-lang.org/pages/decrypt.html).

`DTX(number)` returns uppercase hexadecimal digits. `XTD(text)` reads
hexadecimal digits in either case up to the first other character and
returns zero if it reads no digits. It interprets the low 32 bits as
a signed two's-complement integer, consistent with the guide's examples.
jbcc provisionally truncates fractional DTX operands toward zero and
formats the low 32 bits without leading zeros. It also uses the low
32 bits for XTD inputs wider than eight digits. DTX reports an error
for a nonnumeric operand.
[DTX](https://jbc-lang.org/pages/dtx.html), [XTD](https://jbc-lang.org/pages/xtd.html).

ABS returns the magnitude of a numeric expression. For example,
`ABS(10 - 15)` returns `5`. jbcc reads decimal strings directly,
preserving their significant digits, and truncates the result when an
explicit PRECISION applies. [ABS](https://jbc-lang.org/pages/abs.html).

`ABSS(array)` applies ABS to each element and preserves array marks.
An empty element, or an empty argument, gives 0, as in TAFC PB201214
under both emulations. A nonnumeric
element produces a diagnostic at the ABSS call.
[ABSS](https://jbc-lang.org/pages/abss.html).

NEG reverses the sign of a numeric expression, including a comparison
result. For example, `NEG(2 LT 3)` returns `-1`. jbcc applies explicit
PRECISION as it does for ABS. For nonnumeric input, NEG writes a warning
to stderr at the call site and returns zero, allowing execution to continue.
[NEGS and NEG](https://jbc-lang.org/pages/negs.html).

`NEGS(array)` applies the same conversion and PRECISION to each element
and preserves field, value, and subvalue marks. An empty element gives 0,
as in TAFC PB201214 under both emulations. A nonnumeric element
becomes zero and produces a warning at the call site.
[jBASE NEGS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_NEGS.htm).

DATE() returns the process’s current local calendar date as the number of
days since 31 December 1967. For example, `OCONV(DATE(),'D-')` prints
today’s date as `MM-DD-YYYY`. [DATE](https://jbc-lang.org/pages/date.html).

`@DATE` uses the same day count from the local calendar date at program
startup. The main program and all called routines share that date,
including after local midnight. [@DATE](https://jbc-lang.org/pages/@date.html).

`GETENV(name, value)` looks up a name in the running program’s environment
and assigns the result to a scalar or matrix element. A present variable
returns 1, including when its value is empty. A missing variable returns
0 and clears the destination. Clearing on failure is provisional pending
a reference run. The reference parser also accepts `GETENV(name)`, which
returns the value directly or an empty string for a missing name.
[GETENV](https://jbc-lang.org/pages/getenv.html).

`PUTENV(expression)` creates or replaces a variable in the running
program’s environment. The first `=` separates the name from the value.
For example, `PUTENV("MODE=")` leaves MODE present with an empty value.
Success returns 1. An empty name, a missing `=`, or a host failure
returns 0. Subsequent GETENV calls and children launched by EXECUTE or
PERFORM see successful changes. [PUTENV](https://jbc-lang.org/pages/putenv.html).

`CHDIR(path)` changes the process working directory and returns 1, or
returns 0 and leaves it unchanged. An empty path returns 0. Later
relative paths, including sequential files, resolve from the new
directory. [CHDIR](https://jbc-lang.org/pages/chdir.html).

`GETCWD(var)` assigns the process working directory to `var` and returns
1, or returns 0 and leaves `var` unchanged.
[GETCWD](https://jbc-lang.org/pages/getcwd.html).

`DATA first, second` queues lines for INPUT in FIFO order. Field marks
split an expression into separate lines, including empty fields.
INPUT uses the terminal or stdin when the queue is exhausted. A length
limit can leave queued bytes for the next INPUT.
`CLEARDATA` discards all remaining queued bytes, including a partially
consumed DATA entry. Later INPUT can still read standard input or
newly queued data. [CLEARDATA](https://jbc-lang.org/pages/cleardata.html).

With queued DATA, EXECUTE and PERFORM give the child those lines as its
stdin. The child sees EOF after the queued lines and the parent resumes
with its original stdin. This one-shot handoff is jbcc's native convention.
[DATA](https://jbc-lang.org/pages/data.html).

`EXECUTE expression` and `PERFORM expression` run the resulting command in
the native host's default Bourne shell on POSIX. `EXEC` is an alias with
the same clauses, following the reference grammar's Prime and UniVerse
spelling.

The default streams are inherited from the parent. The caller waits for the
child and continues even if the command exits with a nonzero status. For
example, `PERFORM './report today'` can invoke another jbcc-built
executable. The native runtime also accepts the explicit `CHAR(255) : 's'`
shell prefix.

With `CAPTURING variable` alone, the child’s stdout is collected into the
variable and stderr stays on the caller’s error stream. One final LF is
dropped and each other LF becomes a field mark, as in TAFC PB201214
(`tests/tafc/execute-capturing.b`). An empty stream assigns an empty
string.

`RETURNING variable` and `SETTING variable` put the child’s exit code in
field 1. Either can appear before or after CAPTURING. For native commands,
jbcc provisionally appends nonempty stderr starting in field 2, replacing
each LF with a field mark. With empty stderr the result is just the status.
A signal exit is recorded as 128 plus the signal number. If both clauses
target the same variable, the status result is assigned last.

`PASSDATA expression` hands a value to a jbcc program that the command
runs, which reads it with `COLLECTDATA variable` as often as it likes;
without a PASSDATA, COLLECTDATA gives an empty string. That program's
last `RTNDATA expression` comes back in the caller's `RTNDATA variable`,
which is empty when the program has none, and RTNDATA in a program that
no EXECUTE with the clause ran is discarded. A nested EXECUTE passes
neither unless it has the clause. These follow TAFC PB201214
(`tests/tafc/execute-passdata.b`); jbcc passes the data through two
temporary files named in the child's environment.

Both collected streams keep byte 0, as TAFC does.
Alternate shells and field-mark-separated commands remain unsupported.
TAFC PB201214 runs a command without a shell, splitting it on spaces, so
`;`, `|` and quotes are plain text there; jbcc keeps the shell.
[EXECUTE](https://jbc-lang.org/pages/execute.html).

The default select list is shared with a jbcc program that EXECUTE runs,
as TAFC PB201214 shares it (`tests/tafc/execute-passlist.b`): the child
starts with what is left of the caller's default list, and the caller
continues with what is left of the child's, so a list the child SELECTs
reaches the caller. `PASSLIST expression` gives the child that list
instead; `PASSLIST` alone passes the default list. `RTNLIST` alone changes
nothing, and `RTNLIST variable` assigns an empty string, as TAFC does. A
command that is not a jbcc program leaves the caller's list as it was.
jbcc passes the lists through two temporary files named in the child's
environment.

`@SYSTEM.RETURN.CODE` and `SYSTEM(17)` read the exit status of the
most recent native EXECUTE or PERFORM, including commands run by a
called routine. The value updates with or without result clauses. It
starts at zero in jbcc, a provisional choice pending a reference run.
T24 also inspects this variable after invoking jBASE query commands.
Their record counts require a query backend.
[jBASE system variables](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/par2_PARAGRAPHS.htm),
[SYSTEM functions](https://jbc-lang.org/pages/system_functions.html).

`SYSTEM(1036)` counts contention when an update read or RECORDLOCKU tries to lock a
simulated foreign-locked record. `ASSIGN 0 TO SYSTEM(1036)` resets that
process-wide count, following T24 usage. Assignments for other keys
produce a source-located diagnostic, including the journaling request
at key 1039 and the T24 request at key 2021.
[jBASE SYSTEM](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SYSTEM.htm).

`@USERNO`, its reference compiler aliases `@USER_NO` and `@UDTNO`,
and `SYSTEM(18)` return the same port number. jbcc reads `JBCPORTNO`
at program startup. Set it to a single nonnegative decimal number to
provide a fixed port. When it is unset or empty, native builds use the
POSIX process ID as the port number. Malformed values, lists and ranges
produce a diagnostic when the program requests the port number.
[JBCPORTNO](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/env2_JBCPORTNO.htm),
[SYSTEM functions](https://jbc-lang.org/pages/system_functions.html).

jbcc also accepts the T24 spelling `@USER.NO` as a port-number alias.
The Caché MultiValue reference documents it as another spelling of
`@USERNO`. [Caché MultiValue system variables](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_gsysvariables).

`DEBUG` is a standalone statement. The guide uses it to enter the jBC
debugger. When a native jbcc program reaches it, the runtime reports the
source location and exits with an error because a jBC debugger is unavailable.
[DEBUG](https://jbc-lang.org/pages/debug.html).

`CALLJ class, method, argument SETTING result` accepts an optional
inline or multiline `ON ERROR` arm. Native jbcc reports the source
location and exits if execution reaches the call, even when an error
arm is present. Java invocation requires a JVM backend.
[jBASE CALLJ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_CALLJ.htm).

`TRANSTART`, `TRANSEND`, and `TRANSABORT` accept an optional note expression
and require a `THEN` or `ELSE` arm. `TRANSTART` also accepts `SYNC` before
the note. When a native jbcc program reaches one of these statements,
the runtime reports its source location and exits because transaction
processing requires a backend. This applies to the in-memory file layer too.
[TRANSTART](https://jbc-lang.org/pages/transtart.html),
[TRANSEND](https://jbc-lang.org/pages/transend.html),
[TRANSABORT](https://jbc-lang.org/pages/transabort.html).

jbcc also accepts `TRANSACTION START` and `TRANSACTION COMMIT` with a
`THEN` or `ELSE` arm, and bare `TRANSACTION ABORT`. These forms use
the same source-located transaction-backend diagnostic when reached.
[START](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_CTRANSACTIONSTART),
[COMMIT](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_ctransactioncommit),
[ABORT](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_ctransactionabort).

`@PATH` is the current account pathname in the jBASE guide. Native
jbcc provisionally uses the process's absolute working directory as
the account path. A failure to resolve it reports the source location.
[@PATH](https://jbc-lang.org/pages/@path.html).

`@PID` returns the native process ID. `JBCPORTNO` can set the value of
`@USERNO` independently.
[@PID](https://jbc-lang.org/pages/@pid.html).

`@USER.ROOT` starts empty and accepts a string of up to 63 bytes. An
oversized assignment reports its source location. Linked routines share
the value for the lifetime of the native process, and assigning an empty
string clears it.

`@USERSTATS` returns a snapshot with attribute numbers from `JBC.h`. The
native runtime fills fields 1–6 with the port, active program count of one,
startup time in Unix seconds, PID, account, and login. Fields 8 and 10 hold
the OS terminal type and device.

Fields 18–20 count successful in-memory opens, record reads and record
writes respectively. The read count includes READU, READV, READVU, MATREAD
and MATREADU, and a field read of an existing record counts even when the
field is empty. The write count includes WRITEV, WRITEU, WRITEVU and
MATWRITE.

Fields 21 and 22 count successful in-memory DELETE and CLEARFILE
statements. Deleting a missing key or clearing an empty file still counts
as one operation because the backend reports success. Invalid descriptors
and lock conflicts leave both counters unchanged.

Field 23 counts completed EXECUTE, EXEC and PERFORM statements, including
commands that exit with a nonzero status. Field 24 counts INPUTs that
complete with a value, including data from the DATA queue and the empty
value returned at end of input. An INPUT timeout leaves the counter
unchanged.

Field 28 holds the current `@USER.ROOT` value. Fields 41–43 hold the native
invocation and the line and path where the snapshot was taken. Other fields
are empty.
[@USERSTATS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_%40.htm).

`@TTY` returns the POSIX device name for the terminal on standard
input, such as `/dev/pts/2`. If standard input has no terminal device
name, jbcc returns `phantom`, which T24 tests for a background job. A
plain TAFC PB201214 run without a terminal gives an empty string
(`tests/tafc/at-tty.b`).
[jBASE system variables](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_%40.htm).

`@TERM.TYPE`, `@TERM_TYPE`, and `@TERMTYPE` expose the terminal type
using the T24, reference compiler, and guide spellings. Native jbcc
provisionally reads `TERM` at each use and returns an empty string if it
is unset or empty.
[@TERMTYPE](https://jbc-lang.org/pages/@termtype.html),
[jBASE terminal type](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/TERMINAL_TYPE.htm).

`@SYS.BELL` and the reference compiler spelling `@SYS_BELL` return
the bell sequence. jbcc provisionally uses the ASCII BEL byte
(`CHAR(7)`) for both spellings. jBASE obtains the sequence from the
terminal's `bel` capability.
[jBASE terminfo capabilities](https://static.zumasys.com/jbase/r99/knowledgebase/howto/general/common/CreateTerminfo/usage.htm).

`@WHO` and the login-name form of `SYSTEM(19)` return the same name.
At startup jbcc uses the first nonempty value of `JBCLOGNAME` from the
jBASE manual or `JBASICLOGNAME` from the jBC guide. Without either override,
native builds look up the process's real user ID in the POSIX user
database and return an empty string if the name is unavailable.
[jBASE SYSTEM](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SYSTEM.htm),
[SYSTEM functions](https://jbc-lang.org/pages/system_functions.html).

`@LOGNAME` and `@ACCOUNT` are aliases for the current account in the
reference compiler. jbcc takes the first nonempty startup value of
`JBCLOGNAME` or `LOGNAME`, the variables used by jBASE for pseudo accounts
and Unix accounts respectively. Without either value, jbcc provisionally
uses the login name returned by `@WHO`.
[jBASE LOGTO](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/acc2_logto.htm).

`SLEEP` pauses for one second. `SLEEP expression` accepts a nonnegative
duration in seconds, including fractions such as `SLEEP .25`. Zero
continues immediately. The native runtime truncates durations to whole
nanoseconds and resumes an interrupted wait for the remaining duration.
Clock-time strings such as `"08:30"` currently produce a diagnostic.
[SLEEP](https://jbc-lang.org/pages/sleep.html).

`MSLEEP` pauses for one millisecond, and `MSLEEP expression` for a
nonnegative whole number of milliseconds, as in `MSLEEP 100`. A fraction
is truncated. [MSLEEP](https://jbc-lang.org/pages/msleep.html).

TIME() returns the local clock time in seconds past midnight. The OCONV
mask `MT` prints hours and minutes on a 24-hour clock, and `MTS` adds
seconds. For example, `OCONV(1,'MTS')` returns `00:00:01`. Both masks
accept an explicit colon separator. The current runtime accepts whole
seconds from 0 through 86399. [TIME](https://jbc-lang.org/pages/time.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

`@TIME` returns the seconds since local midnight at program startup.
It shares the clock reading behind `@DATE` across all routines.
[@TIME](https://jbc-lang.org/pages/@time.html).

TIMEDATE() formats one reading of the local clock as a printable string,
for example `23:59:59 31 DEC 2023`. jbcc uses the guide’s default layout
with English month abbreviations. [TIMEDATE](https://jbc-lang.org/pages/timedate.html).

`TIMESTAMP()` returns Unix epoch seconds as a decimal using the POSIX
realtime clock. jbcc truncates the fraction to the active `PRECISION`,
with a default of four fractional places and a maximum of nine.
[TIMESTAMP](https://jbc-lang.org/pages/timestamp.html).

`MAKETIMESTAMP(date, time, zone)` combines an internal date and time read
in `zone` into UTC epoch seconds, keeping milliseconds.
`LOCALDATE(timestamp, zone)` and `LOCALTIME(timestamp, zone)` return the
internal date and time of a timestamp in `zone`. An empty zone is the
process's own; another value is an IANA name such as `Asia/Tokyo`, set as
`TZ` for the conversion. The playground's WASI runtime has no zone
database and accepts only an empty zone, `UTC` and `GMT`.
`TIMEDIFF(timestamp1, timestamp2, mask)` returns `timestamp2` minus
`timestamp1` as fields, and every field carries that sign: TAFC PB201214
computes it this way, although the guide's prose says the opposite.
Mask 0 gives days, hours, minutes, seconds and milliseconds, and mask 1
puts weeks first. Masks 2 to 7 count calendar months (2, 3), years
(4, 5) or years and months (6, 7) from `timestamp1` towards `timestamp2`
in UTC, clamping a day past the end of a shorter month, and split the
rest, with weeks for masks 3, 5 and 7. So from 31 January 2020 to
1 March 2021 01:00, mask 2 gives `13^1^1^0^0^0`, one month after
31 January 2020 being 29 February (`tests/tafc/timediff.b`).
`@TIMEZONE` returns `JBASE_TIMEZONE`, else `TZ`, else an empty string
(provisional: the guide says only "as per jBASE Timezone").
[MAKETIMESTAMP](https://jbc-lang.org/pages/maketimestamp.html), [LOCALDATE](https://jbc-lang.org/pages/localdate.html), [LOCALTIME](https://jbc-lang.org/pages/localtime.html), [TIMEDIFF](https://jbc-lang.org/pages/timediff.html).

`UNIQUEKEY()` returns a 36-character lowercase UUID. jbcc uses version
4 UUIDs generated from `/dev/urandom`.
[UNIQUEKEY](https://jbc-lang.org/pages/uniquekey.html).

ICONV reads dates as TAFC PB201214 does (`tests/tafc/iconv-dates.b`) with
any `D` mask (`D`, `D4`, `D/`, `D4/E`, `DG`):

- `YYYYMMDD`, as in `ICONV('20121231', 'D')`, which returns `16437`, the
  number of days since 31 December 1967; `YYYYDDD`, a day of the year;
- a day, a month name or its first three letters and a year, in either
  order and with or without spaces: `31 JAN 2020`, `JAN 31 2020`,
  `31JAN20`;
- numbers, month first, or day first with an `E` mask: `01/31/2020`;
  without a year, the current one.

Two-digit years from 30 are 19xx and below 30 are 20xx (provisional). A
day past the end of its month rolls forward and sets `STATUS()` to 3
(`31 FEB 2020` is 2 March); any other value that is not a date returns an
empty string with `STATUS()` 1. `OCONV(date, 'DG')` writes `YYYYMMDD`, so
`OCONV(ICONV('20231031', 'DG'), 'DG')` returns `20231031`. T24 R19 uses
`DG` both ways and slices the output as `[1,4]`, `[5,2]` and `[7,2]`. The
`MT` and `MTS` input masks accept `H:MM` and `H:MM:SS` with an optional AM
or PM suffix and return seconds since midnight; as in TAFC, the parts may
overflow (`25:00` is 90000) and `12 AM` stays 12. An unknown mask warns,
as TAFC prints `Unknown conversion code.`, returns an empty string and
sets `STATUS()` to 1; so does an unknown OCONV mask. An empty mask returns
the value. ICONV also takes the MC codes, as OCONV does.

`STATUS()` after a conversion follows TAFC PB201214
(`tests/tafc/conversion-*.b`):

- ICONV with a date or MD mask sets 0 on success, 1 for a value it cannot
  read (including `''`) and 3 for a rolled-over date; a time sets 1 or 3
  the same way but leaves `STATUS()` alone on success;
- OCONV with an MD, MR or ML mask, or an FMT mask, sets 0; with a date or
  time mask it sets 1 for `''` or text and otherwise leaves `STATUS()`
  alone, as do MC, MX, G and L codes;
- an unknown mask sets 1.

Codes separated by value marks run left to right, so
`OCONV('abc', 'MCU':@VM:'MCT')` is `Abc`. A date code without a part
letter (`D`, `D4`, `D/`, but not `DD`) takes the value mark and the rest of
the mask as its own options, as TAFC does: `ICONV(X, 'D':@VM:'D4')` is
`ICONV(X, 'D')`, and `OCONV(0, 'D':@VM:'')` uses the value mark as its
separator. TAFC reads any code that starts with D as a date: ICONV
ignores options it does not know, and OCONV gives the value back.
[ICONV](https://jbc-lang.org/pages/iconv.html).

`ICONVS(array, mask)` and `OCONVS(array, mask)` apply the whole mask, chain
included, to each element and preserve field, value, and subvalue marks.
Each element sets `STATUS()` as ICONV or OCONV would, so the last element
decides what is left, as in TAFC. An empty mask is reported at the call
site.
[ICONVS](https://jbc-lang.org/pages/iconvs.html), [MT conversion](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jql2_CONVERSION.MT.htm).

For dates, the OCONV mask `D` produces `DD MON YYYY`. A digit selects the
year width. With a separator (`-`, `/` or `.`), jbcc follows the guide’s
worked example and observed T24 usage. For example, `OCONV(16454,'D4/')` returns
`01/17/2013`. Append `E` for day-first order. The guide’s syntax table
instead describes day-first order for the plain numeric form. Component
masks include `DD`, `DM`, `DMA`, `DJ`, `DQ`, `DW`, `DWA`, and `DY` with
optional year width; a width above 4 shows four digits. The runtime
accepts Gregorian years 1 through 9999. As in TAFC PB201214, a fractional
day count is truncated toward zero (`OCONV(732.75, 'D')` is 01 JAN 1970),
and a value that is not a number comes back unchanged with `STATUS()` 1.
The time masks `MT` and `MTS` let hours pass 23 (`99999` is `27:46:39`),
show a negative count's magnitude, give `00:00:00` for text and `''` for
`''`; `MTH` uses a 12-hour clock (`OCONV(0, 'MTH')` is `12:00AM`).

OCONV's L and R codes are tests, as in TAFC PB201214
(`tests/tafc/conversion-tests.b`), not FMT masks:

- `L` followed by no digit gives the length; `Ln` gives the value when it
  has at most n bytes and otherwise `''`; `Ln,m` gives it when it has n to
  m bytes and otherwise `''` with `STATUS()` 1;
- `Rn,m{;n,m}...` with integer bounds gives a number that lies in any of
  the ranges and otherwise `''` with `STATUS()` 1. Any other R mask, such
  as `'R2,$#15'`, warns `Error in Range Test.` and gives `''`, as the
  guide's FMT chapter shows; FMT formats it.

A mask that starts with a digit, such as `6R`, is still an FMT mask.

`MDn`, `MRn` and `MLn` are masked decimal conversions, written as in TAFC
PB201214 (`tests/tafc/md-masks.b`). `OCONV(1234567, 'MD2')` is `12345.67`:
the value is divided by 10 to the power n, or by a second digit m in
`MDnm`, and shown with n decimals, rounding half away from zero
(`OCONV(1234567, 'MD24')` is `123.46`). A negative value keeps its sign
even when it rounds to zero. Options follow in any order: `Z` gives an
empty string for zero, `,` groups thousands, `$` prefixes a dollar sign,
`-` or `M` puts the minus sign after the number (a space for a positive
one), `C` appends `CR` for a negative value, `D` appends `DB` for a
nonnegative one, `E` encloses a negative value in `<>`, `P` skips the
scaling when the value already has a point, and `T` truncates. Text that
is not a number comes back unchanged; an empty value gives an empty
string, or `0.00`-style zero with `MR`. `ICONV(text, 'MD2')` removes
commas, multiplies by 100 and rounds to a whole number
(`ICONV('12.345', 'MD2')` is `1235`). `FMT` accepts the same masks.
[DATE](https://jbc-lang.org/pages/date.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

`OCONVS(array, mask)` works as ICONVS does, above.
[OCONVS](https://jbc-lang.org/pages/oconvs.html).

STR repeats its entire first argument, including any embedded array marks.
For example, `STR('ab', 3)` returns `ababab`. Empty input and zero
repetitions produce an empty string. The guide specifies integer counts.
For fractional or negative counts, jbcc provisionally follows SPACE. It truncates
toward zero and returns an empty string for nonpositive counts.
[STR](https://jbc-lang.org/pages/str.html).

`SPACES(counts)` replaces each count with that many ASCII spaces while
preserving field, value, and subvalue marks. A scalar count works too.
An empty input or empty element raises a runtime diagnostic at the call.
jbcc follows SPACE for numeric counts, provisionally truncating
fractions toward zero and producing empty elements for nonpositive
counts. [jBASE SPACES](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SPACES.htm).

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

TRIMS applies the default space trim independently to each field, value
and subvalue. It preserves every mark, including those surrounding empty
elements. The reference lexer accepts one argument and T24 uses
`FIELDS(TRIMS(items), " ", 1, 1)` to extract names. The jBC guide has no
TRIMS entry. Interior space collapsing follows the MultiValue description,
and preserving tab bytes follows jbcc's default TRIM pending a jBC
reference run. [MultiValue TRIMS](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_ftrims).

TRIMF removes leading space bytes and TRIMB removes trailing space bytes.
Both preserve tabs and interior spaces. They use the same runtime as
`TRIM(text, " ", "L")` and `TRIM(text, " ", "T")`, respectively.
[TRIMF](https://jbc-lang.org/pages/trimf.html), [TRIMB](https://jbc-lang.org/pages/trimb.html).

`TRIMBS(array)` removes trailing spaces and tabs from each element.
`TRIMFS(array)` removes leading spaces and tabs. Both preserve
interior whitespace, empty elements, and field, value, and subvalue
marks. [jBASE statement and function index](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/JBC1.htm).

MAXIMUM and MINIMUM compare numeric elements across field, value, and
subvalue marks. An empty element counts as zero. Nonnumeric elements are
skipped, and jbcc provisionally returns zero when all elements are
nonnumeric. Comparisons honor PRECISION and keep the first element on a
tie. The guide shows different output formatting for the two functions.
MAXIMUM returns the selected text, while MINIMUM rounds excess decimal
places to the explicit precision. jbcc follows those examples pending a
reference run. [MAXIMUM](https://jbc-lang.org/pages/maximum.html),
[MINIMUM](https://jbc-lang.org/pages/minimum.html).

`SORT(array)` splits the input at system delimiters (bytes 249–255),
sorts the elements in ascending byte order and joins them with attribute
marks. For example, `SORT('2' : @VM : '10')` returns `'10' : @AM : '2'`.
It preserves duplicate elements and leaves the source array intact. jbcc
also preserves empty elements, pending a reference run. International Mode
locale collation is outside the current runtime.
[SORT](https://jbc-lang.org/pages/sort.html).

SUMMATION returns one total across fields, values and subvalues. For
example, `SUMMATION(1 : @FM : 2 : @VM : 3)` returns 6. T24 uses it to
total balances and charges. jbcc skips nonnumeric and empty elements and
returns zero when there are no numbers. Each addition uses the current
PRECISION. These rules follow jbcc's arithmetic and the MultiValue
example pending a jBC reference run. [IBM BASIC Reference Guide, SUMMATION](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

SUM adds numeric elements at the deepest mark present in the array
(field, value, or subvalue) and preserves each higher-level mark.
For example, `SUM(1 : @FM : 2 : @VM : 3)` returns `1 : @FM : 5`.
The guide specifies that nonnumeric elements are ignored. For a group
with no numeric elements, jbcc returns zero provisionally. Both SUM and
SUMMATION add decimal digits directly, rounding each element to the
PRECISION in force as `+` does, with no integer size limit. [SUM](https://jbc-lang.org/pages/sum.html).

`HUSH ON` suppresses screen output, runtime messages and the prompt and
echo during `INPUT`. `HUSH OFF` restores output. Bare `HUSH` toggles
the state. A nonzero numeric expression enables suppression and zero
restores output. The reference grammar converts the operand to a number.
jbcc provisionally diagnoses nonnumeric operands. Output suppression spans
routine calls. Printer jobs and `EXECUTE ... CAPTURING` still receive
their output. [HUSH](https://jbc-lang.org/pages/hush.html).

`ECHO ON`, `ECHO OFF` and `ECHO expression` control terminal echo during
INPUT. The expression uses ordinary jBC truth conversion. Before an ECHO
statement, INPUT follows the terminal settings. ECHO OFF suppresses
typed characters and the echoed newline while keeping the prompt visible.
`SYSTEM(24)` reports the effective setting, including suppression by
HUSH. The native runtime restores the host terminal mode after each read.
[ECHO](https://jbc-lang.org/pages/echo.html),
[SYSTEM functions](https://jbc-lang.org/pages/system_functions.html).

`INPUT @(column,row):Target` emits the cursor sequence before the input
prompt. The colon after the coordinates is optional. Coordinates use the
same zero-based convention as `CRT @(column,row)`.
[INPUT](https://jbc-lang.org/pages/input.html).

`INPUTCLEAR` and `CLEARINPUT` clear terminal type-ahead. Queued DATA
and nonterminal stdin stay available for subsequent reads.
[INPUTCLEAR](https://jbc-lang.org/pages/inputclear.html).

`KEYIN()` and `IN()` read one byte without a prompt. The reference
compiler generates the same operation for both spellings. jbcc reads
queued DATA first and then standard input, sharing the same stream as
INPUT. On terminals it temporarily disables editing and echo while
preserving interrupt handling. jbcc returns an empty string at EOF, and
byte 0 as a one-byte value, as TAFC PB201214 does (`tests/tafc/nul-input.b`).
[KEYIN](https://jbc-lang.org/pages/keyin.html).

`INPUT Var` writes the current prompt and reads a line from standard input.
`PROMPT expression` sets the prompt for subsequent reads. The default is
`?`, and `PROMPT ''` suppresses it. The prompt appears only when standard
input is a terminal: with piped or redirected input the program writes no
prompt and reads through the next LF, as TAFC PB201214 does
(`tests/tafc/input-prompt.b`). The line keeps byte 0. On a terminal,
`INPUT Var:` keeps typed characters visible and suppresses the echoed
newline.
`INPUT Var, n` reads up to `n` bytes. Enter ends the read early. At
the limit, INPUT returns immediately and leaves subsequent bytes,
including any following LF, for the next read. With terminal echo enabled,
reaching the limit echoes a newline unless the statement ends in a colon.
Provisionally, jbcc truncates fractional lengths toward zero. A zero
length consumes no input, and a length below `-1` raises an error.

`INPUT Var, -1` checks for pending input without prompting, waiting or
consuming bytes. Following T24 usage and the UniVerse BASIC reference,
jbcc provisionally assigns `1` if DATA or standard input has bytes
available and `0` otherwise. On a terminal it can detect a key before
Enter and restores the terminal mode after the check. With a `FOR`
clause the poll is still immediate. Pending input selects THEN, and an
empty buffer selects ELSE.
[IBM BASIC Reference Guide, INPUT](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

`INPUT Var, n_` keeps up to `n` bytes and consumes the rest of the line.
With terminal echo enabled, excess bytes sound the bell. Enter ends
the read and echoes a newline. Both `_:` and `:_` suppress that newline.
Use a space before the underscore after a named length, as in
`INPUT Var, Limit _`. The same line consumption applies to queued DATA
and piped input.
[jBASE INPUT](https://docs.rocketsoftware.com/bundle/jbase_lib_59/page/hpy1666031229329.html).

`INPUT Var FOR n THEN ... ELSE ...` waits up to `n` tenths of a second
for the first byte and restarts the interval after each byte. Enter or
the length limit selects THEN. A timeout selects ELSE and assigns the
bytes received so far, including an empty string if none arrived.
Either arm may be omitted. With `FOR 0`, jbcc checks immediately for
available input. Fractional intervals are provisionally truncated toward
zero, and a negative whole interval raises an error.

In jbcc an empty line assigns an empty string. At EOF, INPUT assigns any
remaining bytes, or an empty string if none remain. Timed INPUT takes
the success branch at EOF. These EOF rules are
provisional pending a reference run. [INPUT](https://jbc-lang.org/pages/input.html),
[PROMPT](https://jbc-lang.org/pages/prompt.html).

`@SENTENCE` reads the invocation in the main program or any called routine.
For example, starting `./report today` gives `./report today`, and
`@SENTENCE[' ',2,1]` gives `today`. For native executables,
jbcc provisionally uses the exact program name supplied in `argv[0]` and
joins all arguments with one space. Embedded spaces and empty arguments
are preserved, and shell quoting is already removed by the time the
program starts.

`@PARASENTENCE` returns the invoking paragraph or sentence. A native
launcher can provide that text through `JBCC_PARASENTENCE`, which jbcc
reads at startup. When the value is empty or unset, `@PARASENTENCE`
returns the same invocation as `@SENTENCE`. Both are available in
called routines, and later environment changes leave the startup text
intact.

`SENTENCE()` and `SENTENCE('')` return the full invocation. `SENTENCE(0)`
returns the program name, and positive integer positions select individual
arguments starting at 1. Indexed reads preserve argument boundaries,
including embedded spaces and empty arguments. Negative and out-of-range
positions return an empty string. Indexed reads leave the `GET (ARG.)`
cursor in place. jbcc requires an integer value for a nonempty index.
[SENTENCE](https://jbc-lang.org/pages/sentence.html).

jbcc provisionally gives `@COMMAND` the same invocation string. The
reference compiler recognizes it as a system variable, and T24's
JGLOBUS.DATABASE.COPY.JBASE extracts arguments from its second
space-delimited field onward. In `CALL @COMMAND`, COMMAND is an
ordinary variable that holds the target routine name.

`GET (ARG.) Value` reads the next native command-line argument.
`GET (ARG., n) Value` reads argument `n`, counting from 1 after the
program name. Zero also reads the next argument. A successful read
moves the shared program cursor forward from that argument, and a
failed read leaves the cursor in place. A quoted argument with spaces
or an explicitly empty argument is returned as one value. Optional
`THEN` runs on success. On failure, an explicit `ELSE` retains the
destination's previous value. With no `ELSE`, failure assigns an
empty string. Nonnumeric, empty and fractional indices are errors.
[GET(ARG.) reference](https://www.ibm.com/docs/en/iis/11.7.0?topic=functions-getarg-statement).

Single-line and multiline IF support THEN, ELSE, and nested branches.
Close a multiline arm with END. Its ELSE can follow on the same line or
on the next line. The reference preprocessor joins a line beginning with
THEN, ELSE or LOCKED to the preceding statement, including across blank
lines and full-line `*` or `!` comments.
The system constants `@TRUE` and `@FALSE` evaluate to 1 and 0.
Comparisons return the same values. The reference preprocessor accepts
`=<` for `LE` and `=>` for `GE`. For example, `balance => required` also
succeeds when the two amounts are equal. Two decimal strings compare numerically;
other pairs compare in byte order. Numeric zero and the empty string are
false. Decimal comparisons round both sides to the PRECISION in force.
See the [Boolean variables](https://jbc-lang.org/pages/boolean_variables.html)
and [IF](https://jbc-lang.org/pages/if_statement.html) chapters.

AND (`&`) and OR (`!`) have equal precedence and group left to right.
Comparisons bind more tightly. For example, `1 OR 0 AND 0` evaluates to
`0`. Both operators return `1` or `0` and skip the right operand when the
left decides the result. At the start of a statement, `!` introduces a
comment. Grouping follows the [jBC grammar](https://github.com/jbc-lang/jbc-language/blob/master/spec/jbc.y).
Short-circuit evaluation follows the original C generator's use of C's
`&&` and `||` in `operator_integer_gen`.

PRECISION sets the number of decimal places for arithmetic and
comparisons; see the arithmetic rules above. For example, `PRECISION 6`
followed by `CRT 2 / 3` prints `0.666666`. As TAFC PB201214 compiles it,
the first PRECISION statement in a program, subroutine or function, when
its argument is an integer literal, is that unit's precision from its
first line, even inside a branch that never runs. Later PRECISION
statements change it when they execute, and accept any expression whose
value is a nonnegative integer. A unit without PRECISION uses 4. A local
GOSUB shares the current setting. An external subroutine or function runs
at its own precision and restores the caller's on return, as observed with
cataloged routines in TAFC (`tests/routines/precision-scope`).
[PRECISION](https://jbc-lang.org/pages/precision.html),
[Boolean variables](https://jbc-lang.org/pages/boolean_variables.html).

MATCH and MATCHES compare the whole input against a pattern. A count followed
by A, N or X selects ASCII letters, digits or any bytes, respectively. A
zero count allows any length, including zero, and `n-m` before a code
allows n to m bytes. `...` matches any run of bytes, so
`'JOHN DORY' MATCHES "'JOHN'..."` is true. The codes may be lower case.
For example, `'QA42' MATCHES "2A2N"` is true, as is
`'QA42' MATCHES "'QA'1-3N"`. Quoted literals match exactly, and a value mark
(`@VM`) separates alternative patterns. Other unquoted text, such as the
prefix in `PL5N` or the `5C` in `"5C"`, is literal; `C` is not a code under
prime, and two periods are literal. Under `--emulation jbase`, `C` selects
alphanumeric bytes, the codes are upper case only, and neither ranges nor
`...` exist, as TAFC PB201214 shows.
Concatenation binds more tightly than MATCH, so a program can build a
pattern expression directly on its right. [MATCHES](https://jbc-lang.org/pages/matches.html).

`MATCHFIELD(text, pattern, field)` returns the part of a whole-string
match consumed by the numbered pattern component, starting at 1. It uses
the prime pattern codes under both emulations, as TAFC PB201214 does.
For example, `MATCHFIELD('QA123end', '2A0N3A', 2)` returns `123`.
Literal components count. A failed match or a missing component returns
an empty string. The field number must be an integer. For ambiguous
matches jbcc provisionally uses the first matching alternative and the
shortest possible final component, applying the same rule to the prefix.
[MATCHFIELD](https://jbc-lang.org/pages/matchfield.html).

The reference grammar also accepts a format mask after its value, as in
`Total "10R"` or `Total Masks<2>`. This syntax uses the same masks as
`FMT(value, mask)`. Its precedence is below arithmetic and above
concatenation, so `"sum=":2 + 3 "R%3"` produces `sum=005`. jbcc resolves
bare mask names through known variables and matrix elements. In routines
with jumps, a scalar mask can be initialized in a later source block,
such as a GOSUB routine. The mask must have a value when it is read.
Clause keywords remain delimiters in this position. Use explicit FMT
when a mask variable shares a clause keyword.

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

`FMT(value, 'MX')` and `OCONV(value, 'MX')` write each byte as two
upper-case hexadecimal digits, so `FMT('ABCDEF', 'MX')` returns
`414243444546` and `FMT(@FM, 'MX')` returns `FE`. `ICONV(hex, 'MX')`
turns pairs of hexadecimal digits back into bytes, as in
`ICONV('4020412042', 'MX')`, which returns `@ A B`. As in TAFC, decoding
stops at the first pair that is not hexadecimal and ignores an odd last
digit, so `ICONV('414', 'MX')` is `A`; a `00` pair is byte 0. jbcc works
on bytes, so a
character outside ASCII shows as the bytes of the source encoding.

`FMT` and `OCONV` accept the `MC` conversions of the guide's `OCONV`
table. `MCA`, `MCN` and `MCB` keep only ASCII letters, digits, or both,
and `MC/A`, `MC/N` and `MC/B` remove them. `MCL` and `MCU` change case,
and `MCT` capitalises each word and lowers the rest, so `LONG STRING`
becomes `Long String`. `MCC;s1;s2` replaces every `s1` with `s2`, using
the character after `MCC` as the separator. `MCDX` writes a nonnegative
decimal integer in hexadecimal and `MCXD` reads it back, so
`OCONV('FB', 'MCXD')` returns `251`. `MCP` replaces each non-printable
byte, anything outside ASCII 32 to 126 as `ISPRINT` classifies it, with
`.`, or with the character `c` in `MCPc`, but shows field, value and
subvalue marks as `^`, `]` and `\`, and byte 255 as `_`, as TAFC
PB201214 does. The guide shows both: the text mark
in `LONG STRIN.G TO BE SP.LIT` and the marks in `1^2]3^4\5`. The guide's
`MCPN{x}` writes each byte outside ASCII 32 to 126, marks included, as
`x` (default `.`) and two upper-case hexadecimal digits, and `MCNP{x}`
reads them back, as in TAFC PB201214; `x` itself is not escaped, so the
round trip loses an `x` followed by two hex digits. `G{n}cx` takes `x`
groups delimited by `c` after skipping `n`, so
`OCONV('LONG STRING TO BE SPLIT', 'G1 3')` returns `STRING TO BE`.
[OCONV](https://jbc-lang.org/pages/oconv.html),
[FMT](https://jbc-lang.org/pages/fmt.html).

`FMT` also accepts pattern masks: `L(pattern)`, `R(pattern)` or a bare
pattern starting with `#`. In the pattern, `#` takes one character of the
value and `#n` takes n; everything else is literal. `R` fills the slots
from the value's rightmost characters and `L` from its leftmost, and
missing characters become spaces. So `FMT(1234567890, 'R((###) ###-###)')`
returns `(234) 567-890` and `FMT('202203241105', '####-##-##_##:##')`
returns `2022-03-24_11:05`. The guide never combines a pattern with a
decimal precision, so jbcc rejects `R2(...)`.

Numeric `FMT` masks follow the guide's table: after `L` or `R` and the
precision, a scaling digit (`R22` divides by 100), `Z` (zero prints as
spaces), `,` (thousands), a credit indicator (`C` adds `CR` after a
negative value, `D` adds `DB` after a positive one, `E` encloses a
negative value in `<>`, `M` puts the minus sign after it, `N` drops it),
`$` and `&x`, then the fill `#n`, `%n` or `*n`. So
`FMT(123456.78, 'R2,$#15')` returns `"    $123,456.78"` and
`FMT(-123456.78, 'R2,C&*$#15')` returns `"**$123,456.78CR"`. `&x` makes
`x` the fill character, overriding the `#`, `%` or `*` fill, and `x` itself
is not shown, so `'R2,&$#15'` gives `"$$$$$123,456.78"`, as in TAFC
PB201214; the guide's comments show blanks. A value wider than the field is
not cut. As the guide's table says, `FMT`
formats `D` and `MT` masks as `OCONV` does (`FMT(16376, 'D4/')` returns
`10/31/2012`), and `OCONV` accepts `FMT`'s `L`, `R` and width masks.

Width-prefixed `T` masks such as `35T` wrap at spaces when possible.
They split overlong words, pad each block on the right, and insert
a text mark between blocks. jbcc provisionally uses the same
byte widths and edge-space trimming as FOLD.

`FMTS(array, mask)` applies the supported FMT masks to each field,
value and subvalue, preserving delimiters and empty elements. An empty
array gives an empty result with a valid mask. An empty or unsupported
mask reports a source-located formatting error.
[jBASE FMTS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_FMTS.htm).

CRT and its alias DISPLAY write to standard output even with PRINTER ON.
PRINT uses the current output device, initially standard output. Commas
separate items with tabs. A final colon suppresses the newline. An output
statement with no arguments emits a newline.
[CRT reference](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_crt.htm).

`HEADING expression` puts a title on the first page and repeats it on
page breaks. `PAGE` advances the page number and `PAGE n` sets it. A
replacement `HEADING` or `HEADINGE` starts a new page. Prefixing the text
with `@AM` defers it until the next break. jbcc also defers replacement
for `HEADINGN`; that timing is provisional. Quoted options support page
numbers (`P` and four-column `PP`), newlines (`L`), date (`D`), time
and date (`T`) and continuous output (`N`). The shortcuts `^`, `^^`
and `]` also work. Centering and backslash options produce diagnostics.
[HEADING](https://jbc-lang.org/pages/heading.html) and
[PAGE](https://jbc-lang.org/pages/page.html).

The native runtime counts output lines against the terminal height and
waits for Enter at page breaks when both input and output are terminals,
unless the heading or footing specifies `N`. For redirected output the provisional
layout is 24 lines per page, with a form feed between pages.

`FOOTING expression` reserves lines at the bottom of each page and
uses the same template options as HEADING. It prints with the outgoing
page number before a break or terminal pause. jbcc provisionally pads a
short page to the footer position at a break, at printer close or at
normal program exit. `FOOTING ''` clears the footer. `FOOTING ON n`
sets it for the selected print unit. [FOOTING](https://jbc-lang.org/pages/footing.html).

`PRINTER ON` switches PRINT to the printer. `PRINTER OFF` switches back
to the terminal and leaves the job open. `PRINTER CLOSE` closes the job.
`PRINT ON n`, `HEADING ON n` and `PAGE ON n` share the selected unit’s
output and page state. Units 1 through 127 are independent. jbcc routes
unit 0 to the current default destination. The reference grammar accepts a
parenthesized expression or a sum or difference for the PRINT unit.
[PRINT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_PRINT.htm)
and [PRINTER](https://jbc-lang.org/pages/printer.html).

`@LPTRHIGH` reports the line count for the current PRINT destination.
It queries the terminal attached to standard output when printing to
the screen. When terminal dimensions are unavailable, jbcc uses 24
lines, the same default as report pagination. When a printer unit is
selected, it returns that unit's page height.
[@LPTRHIGH](https://jbc-lang.org/pages/@lptrhigh.html).

To capture printer output locally, set `JBCC_PRINT_DIR` to an existing
directory when running the executable. Each new job creates a unique
`unit-<number>-*` file. This file backend uses a provisional 24-line
page size. `PRINTER RESET` resets the selected unit’s heading and page
counter while preserving the open job, following the usage in T24’s
PRINTER.ON routine. A qualified `PRINTER CLOSE ON n` closes only that
unit. For the grammar’s qualified ON and OFF forms, jbcc treats
`PRINTER ON ON n` as selecting the default destination and
`PRINTER OFF ON n` as releasing it if selected. This behavior is
provisional pending a reference run. Printer operations requiring a new job report a runtime diagnostic
if the directory is unset or unavailable.

```sh
mkdir -p /tmp/jbcc-reports
JBCC_PRINT_DIR=/tmp/jbcc-reports just run tests/io/print-units.b
```

The reference parser also allows `IF condition THEN value ELSE value`
in an expression. Only the selected value is evaluated. In the reference
grammar, ELSE has the same left-associative precedence as exponentiation,
so `IF C THEN 2 ELSE 3 + 10` adds 10 to the selected value. Write
`IF C THEN 2 ELSE (3 + 10)` to put the addition inside the ELSE arm.
Use parentheses inside an angle-bracket selector, as in
`R<(IF C THEN 1 ELSE 2)>`.

FOR supports inclusive bounds, a default step of one, optional STEP, and an
optional variable name after NEXT. Following the reference parser, jbcc
warns if that name differs from the innermost FOR counter. The NEXT still
increments the counter from that FOR header. The limit and step are
evaluated at the start of each iteration. The captured step increments the
counter after the body.

A scalar read inside FOR can use a value initialized by a plain assignment
on an earlier iteration. jbcc checks the value at the read, including on
the first iteration.

FOR accepts WHILE and UNTIL guards in its header. The reference grammar
also allows guards between statements in FOR and LOOP bodies, with an
optional DO after the condition.

An inline arm can end at a loop guard. `THEN END` and `ELSE END` specify
empty arms and execution continues after the conditional. In `LOOP READNEXT
ID ELSE ID = "" WHILE ID <> ""`, the guard tests the ID after READNEXT and
its ELSE arm have run. An ELSE inside a nested conditional still binds to
the nearest eligible THEN.

An inline arm inside a FOR also ends at the enclosing NEXT. For example,
`FOR I = 1 TO 3 ; IF I = 2 THEN CRT I ; NEXT I` increments I on every
iteration and prints only 2. jbcc also recognizes `NEXT = value` and
`NEXT:` as an assignment and a label where a statement can begin.

T24 uses `UNTIL found` immediately before `NEXT`. When the body reaches
that guard and `found` is true, the FOR exits with its counter at the
current value.

CONTINUE skips the rest of the innermost iteration. In FOR it advances the
counter by the captured step. In LOOP it resumes at the top, even when a
guard appears later in the body. Outside a loop it issues a compile-time
warning and execution proceeds normally.

Loop membership follows the location of the statement in the source. A
`GOSUB` from inside a loop to a label outside it does not bring that loop
into scope for `CONTINUE`, bare `EXIT` or `BREAK`.
[CONTINUE](https://jbc-lang.org/pages/continue.html). See the [FOR](https://jbc-lang.org/pages/for.html) and
[LOOP](https://jbc-lang.org/pages/loop.html) chapters.

Bare `BREAK` and `EXIT` leave the innermost FOR or LOOP, including from
inside a CASE arm. A FOR counter keeps its current value. Outside a loop
the compiler warns at the statement and execution continues.
[BREAK](https://jbc-lang.org/pages/break.html).

`BREAK OFF` suppresses SIGINT in the current process, including the
signal normally generated by the terminal interrupt key. `BREAK ON`
restores the process's previous interrupt handler. Repeated calls with
the same setting have no extra effect. With the default POSIX handler,
an enabled interrupt terminates the executable. jbcc has no interactive
debugger. [BREAK ON/OFF](https://jbc-lang.org/pages/break_on_off.html).

`EXIT(expression)` ends the process, including when executed in a
subroutine. jbcc truncates a fractional status toward zero and requires
the result to fit a C int. This conversion policy is provisional pending
a reference run. [EXIT](https://jbc-lang.org/pages/exit.html).

STOP and ABORT terminate the standalone process, including from a called
routine. STOP exits with status 0 and ABORT exits with status 1 in the
native builds. Both accept optional comma-separated message expressions.
jbcc renders those arguments directly to standard error. A numeric first
argument appears as a message identifier, as in `ABORT [201] file` for
`ABORT 201, "file"`. A text first argument appears as written. Additional
arguments are separated by spaces. This rendering and the ABORT status
are provisional standalone behavior. The reference uses a message
catalogue and distinguishes the statements for calling jCL programs.
[STOP](https://jbc-lang.org/pages/stop.html), [ABORT](https://jbc-lang.org/pages/abort.html).

## Dimensioned arrays and shared storage

DIM and DIMENSION accept comma-separated declarations with positive integer
bounds, including expanded EQUATE constants. Indices run from zero through
the declared bound, inclusive, in this subset. Supply one index per
dimension.

Local matrices belong to one invocation. Passing an element to CALL passes
that slot by reference.

Matrix references, including MAT call arguments, can appear earlier in the
source than the DIM or COMMON declaration. The compiler determines their
rank from the declaration, including in inserts. Fixed-size matrices are
available from routine entry. Runtime-sized matrices still require
execution of the declaration before use. This follows the reference
compiler's assumed-array rule.

Before a local DIM appears in the source, an unsubscripted assignment,
expression or CALL argument can use the same name as a scalar. jbcc
provisionally keeps that scalar value in separate storage from the matrix.

For T24 sources, jbcc also accepts bounds such as
`DIM Grid(Config<1>, N + 1)`. This follows the reference parser’s `dimvar`
rule in dynamic-array mode. The guide describes the constant-bound form.

Each time execution reaches a declaration with expression bounds, jbcc
evaluates them. A repeated DIM of a local matrix reuses its slot. For a
runtime-sized matrix, the first declaration reached binds the bounds for
that invocation. Subsequent declarations preserve the elements when the
rank and bounds match.

A rank change is a compile-time error. Executing a declaration that would
change the bounds or using a runtime-sized matrix before its declaration
has executed reports an error. Unassigned reads and out-of-range subscripts
also produce runtime diagnostics.

`MAT A = expression` evaluates the expression once and fills every slot,
including index zero. `MAT A = MAT B` copies the values of a fully
assigned matrix. An unassigned source slot raises a runtime error at the
copy statement, including when that slot falls beyond the destination.
The reference compiler checks that both operands are dimensioned and
passes them to a runtime routine. T24 uses unequal vector bounds in
both directions.

For unequal shapes, jbcc provisionally copies the all-zero slot, then
copies one-based elements in row-major order until either matrix ends.
Extra destination elements retain their previous values and assignment
state. In a multidimensional destination, slots with a mix of zero and
positive subscripts also retain their values. Identical shapes copy every
slot. These rules apply to local matrices, COMMON matrices and MAT
parameters. The unequal-shape policy draws on the OpenQM manual pending
a jBC reference run. [jBC MAT](https://jbc-lang.org/pages/mat.html),
[OpenQM reference, MAT](https://krowemoh.com/static/qm.pdf).

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
internal delimiters. SETTING is optional and counts the fields placed,
including empty fields between delimiters; one trailing delimiter ends the
record without adding an empty field. When fields are left over, SETTING
is 0, and under `--emulation jbase` the rest is joined to the last
element instead of element zero. jbcc clears unused slots inside the
range and treats empty input as zero fields. An empty delimiter splits
the record into bytes. These follow TAFC PB201214
(`tests/tafc/matparse-edges-*.b`).
[MATPARSE](https://jbc-lang.org/pages/matparse.html).

`INMAT(A)` reports the bounds of dimensioned array `A`, using one value
mark between dimensions, as in the guide's two-dimensional example.
For instance, after `DIM A(2,4)`, it returns `2:@VM:4`. This also works
with a matrix passed by reference.

`INMAT()` returns the element count from the most recent MATREAD, MATREADU,
or MATPARSE in the process. It returns zero initially and when the input
exceeds the available slots. For a ranged MATPARSE, the selected range
determines overflow. A failed or locked MATREAD also sets the
count to zero in jbcc. SETTING continues to report the count specified by the individual
statement. [INMAT](https://jbc-lang.org/pages/inmat.html).

COM and COMMON accept scalars and dimensioned arrays. Declarations of the
same named or unnamed block share slots by position across routines in one
program. A block name can be an identifier or a sequence of digits,
including one substituted by `EQUATE`. Leading zeros are part of the name.

Repeating a scalar or a matrix in the same block within a compilation unit
reuses its original slot, including when an include is expanded twice. This
follows the reference parser’s `common_identifier` allocation rule and its
dynamic-dimension generator.

Repeated COMMON declarations must agree on rank and bounds. jbcc checks
constant bounds at compile time and expression bounds when the declaration
executes.

A member listed with and without dimensions in the same block keeps the
slot of its first occurrence and takes the dimensioned declaration's
bounds, following the Prime compiler layout.

For T24 compatibility, a later DIM or DIMENSION of a COMMON matrix reuses
its original shared slot. The reference compiler accepts changes to bounds
in resize-enabled emulation. jbcc translates a DIM with the same rank and
reports a source-located error if execution would change the bounds. A rank
change is a compile-time error.
[jBASE DIM](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_DIMENSION.htm).

A DIM in a routine can also dimension a member that its COMMON block lists
as a scalar, as T24 R13 does in `AM.RECOMMEND.ALERT`. The local jBC
201015.001 reference dimensions the member's COMMON slot in place. jbcc
gives the member shared matrix storage keyed by its block and position, so
every unit that dimensions it sees the same elements. A unit that
dimensions it with different bounds reports a source-located error. Units
that use the member as a scalar keep a separate value.

Prime mode emits array accesses with fewer or more subscripts than the
COMMON declaration supplies. jbcc translates these accesses and reports a
source-located error if execution reaches one.

The compiler also checks member count, rank, and known bounds across
input files. For T24 declarations such as
`COMMON /CACHE/ Rows(Config<1>), Tail`, jbcc evaluates the bound when
execution reaches the declaration. Each matrix has its own storage, so
the scalar after it keeps the same position in every routine. Indices and
MAT operations use the saved bounds, even if Config changes later.
Re-entering the declaration or binding the same member in another routine
checks its dimensions and preserves its values. A different shape produces
a source-located diagnostic. This timing and mismatch policy is provisional
pending a reference run. Under prime emulation every COMMON scalar and
matrix element starts at 0 and counts as assigned, as in TAFC PB201214
(`tests/tafc/common-*.b`); under `--emulation jbase` they start
unassigned. [DIMENSION](https://jbc-lang.org/pages/dimension.html),
[COMMON](https://jbc-lang.org/pages/common.html).

`CLEARCOMMON` sets every scalar and matrix element of the unnamed COMMON
to 0 and leaves named blocks unchanged, as the guide's jBASE example
shows. The guide notes that TAFJ also clears named blocks.
[CLEARCOMMON](https://jbc-lang.org/pages/clearcommon.html).

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
  field. Missing components read as empty strings. Sparse assignments
  fill intervening positions with marks. The runtime uses single-byte
  `@FM` (also `@AM`), `@VM` and `@SM`. The text mark `@TM` is byte 251
  and can separate text within a subvalue. The reference compiler also defines
  `@SVM` as an alias for `@SM` (byte 252) and `@IM` and `@RM` as names for
  byte 255. [Dynamic arrays](https://jbc-lang.org/pages/dynamic_arrays.html)
- `EXTRACT(R, field[, value[, subvalue]])` reads a component using the
  same field, value and subvalue marks as angle brackets. The guide
  specifies numeric indices and an empty result for a negative field.
  Following T24 usage, trailing zero value and subvalue indices omit
  those levels. jbcc provisionally truncates fractions toward zero and
  returns an empty string for other nonpositive or missing positions.
  [EXTRACT](https://jbc-lang.org/pages/extract.html)
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
  LOOP and FOR bodies. The reference grammar also accepts an optional
  colon after a GOTO or GOSUB target, as in `GOTO finish:` or `GOSUB 100:`.
  The reference lexer accepts `GO label` and `GO TO label` as spellings
  of GOTO, including in indexed ON statements. GOSUB starts a fresh
  control-flow invocation, shares the routine's variables, and supports
  nested returns. Execution falls through
  labels encountered sequentially. STOP terminates the program. [GOSUB](https://jbc-lang.org/pages/gosub.html)
- A jump can enter a FOR body. With the default step, NEXT increments
  the current counter and the loop then checks its current bound. The
  caller must assign the counter before reaching NEXT. For a loop with
  an explicit STEP, NEXT reports a source diagnostic if the jump skipped
  the step expression. This policy is provisional. T24's
  BL.BILL.CROSSVAL assigns the counter before jumping and can set the
  bound before NEXT. The reference generator emits a direct jump and
  delegates NEXT to its runtime macro. [FOR](https://jbc-lang.org/pages/for.html)
- `ON n GOTO a, b` and `ON n GOSUB a, b` evaluate the integer selector
  once. Label positions start at 1. A plain RETURN from the selected
  GOSUB resumes at the next statement. By default an out-of-range selector
  produces a warning and selects the nearest end of the list. For the
  guide's generic Pick behavior, compile the generated C with
  `-DJBCC_ON_FALLTHROUGH` (or pass it in `CC_FLAGS` with `--exe`).
  Out-of-range selectors then continue at the next statement silently.
  [ON GOTO and ON GOSUB](https://jbc-lang.org/pages/ongoto.html)
- `RETURN TO label` unwinds one local GOSUB and resumes at the label in
  its caller. With no outstanding GOSUB it returns from an external
  SUBROUTINE. In the main program it reports a runtime error. The label must
  exist in the same source unit. The reference grammar accepts a trailing
  colon, and the reference compiler rejects this form in a FUNCTION.
  The nested-call test's expected output is inferred from the self-targeting
  unwind in T24's DBUPDATE. [RETURN](https://jbc-lang.org/pages/return.html)
- `PROGRAM name` documents the source. The name generates no C symbol and
  execution continues with the following statement. The native snippet
  exercises the guide's documented behavior with a dotted, hyphenated name
  and a quoted name containing a semicolon. [PROGRAM](https://jbc-lang.org/pages/program.html)
- SUBROUTINE parameters and plain variable arguments to CALL share storage,
  including output arguments. Expressions are passed in temporary slots.
  A static subroutine name can contain punctuation, as in
  `CALL !HUSHIT(1)`, `CALL *REPORT(1)`, or `CALL REPORT-NAME(1)`.
  Direct CALL accepts single, double, or backslash delimiters around
  a name and strips them. SUB and SUBROUTINE headers read a bare name
  through the next whitespace, opening parenthesis, or statement
  separator. Quote characters in a header are literal. A direct CALL
  keeps its literal target when an
  EQUATE shares the name. Arguments still expand EQUATEs. In
  `CALL @Name(args)`, jbcc expands any EQUATE for Name, then uses the
  resulting variable's value to select a linked subroutine. Lookup is
  case-sensitive. jbcc checks the target's parameter count and scalar
  or MAT parameters at runtime.
  For example, `Name = 'GET.STATUS'; CALL @Name(Rec, Answer)` can update
  Answer just like a direct call.
  With a declared matrix, `CALL @Names(I)(Rec, Answer)` reads the name
  from the first parenthesized group and passes arguments from the
  second. The argument group is optional. The name is captured before
  evaluating any arguments. The reference compiler accepts a
  one-dimensional subscript with a positive literal or a variable. jbcc
  uses its usual matrix subscript rules, including expressions and
  multiple dimensions.
  A comma at the end of a line continues the argument list on the next
  line. The reference preprocessor applies this rule before parsing, so
  it also works in routine headers and expressions. A trailing semicolon
  comment, blank lines and intervening comment lines are allowed.
  Each invocation has its own locals. A RETURN outside a local GOSUB ends
  the invocation. Reading an unassigned output reports a runtime diagnostic.
  [SUBROUTINE](https://jbc-lang.org/pages/subroutine.html)
- `CALLONEXIT(name[:@VM:arguments])` registers a linked subroutine
  with one scalar parameter. The parameter receives the text after the
  first value mark, or an empty string. Name lookup is case-sensitive.
  Registrations run in order when the program ends normally or exits
  through the jbcc runtime. The first registration for a name wins.
  Registration returns 0 on success and a nonzero error code for an
  empty name or an unavailable callback. Registrations during callback
  dispatch return a nonzero code. Signal-triggered exits are outside
  this native implementation.
  [CALLONEXIT](https://jbc-lang.org/pages/callonexit.html)
- `CALLC JBASESubroutineExist(name, info)` returns 1 for a linked
  subroutine and 0 otherwise. Lookup is case-sensitive and checks the
  subroutines supplied to jbcc when building the executable. The native
  implementation writes an empty string to the reserved info argument.
  [JBASESubroutineExist](https://jbc-lang.org/pages/jbasesubroutineexist.html)
- EQU or EQUATE defines token substitutions, including comma-separated
  definitions. T24 also uses definitions between semicolon-separated
  statements. Each definition applies from that point onward, including
  later statements on the same line. LIT and LITERALLY treat a single- or
  double-quoted operand as source text. The text can supply an expression
  or multiple statements. For example, `EQUATE SHOW.IT LIT "CRT 'ready'"`
  defines a statement, and `EQUATE MESSAGE TO 'ready'` defines a string
  value. Tokens from quoted expansions point inside the definition.
  A name inside its own expansion stays a plain name, as in the local
  reference and the C preprocessor: after `EQU A.B TO A.B`, `A.B` is the
  variable (or, in R19, the component constant) `A.B`.
  $INSERT and INCLUDE search the including file's directory, followed by
  each `-I DIR` in order. Included tokens retain their source locations.
  When neither has `JBC.h`, jbcc uses its built-in copy and prints a note
  on stderr. The built-in `JBC.h` defines only what the guide's examples
  use: 26 constants, such as `JBASE_CRYPT_ROT13`,
  `JIOCTL_COMMAND_FILESTATUS` and `USER_PROC_ACCOUNT`, and the `DEFC`
  declarations of the in-memory cache functions, as in TAFC PB201214's
  `JBC.h`. It is not the jBASE header. A real `JBC.h` on
  the include paths always wins, and `--no-builtin-includes` reports the
  missing file instead. The playground uses the built-in copy too, while
  the corpus checker never does, so corpus results reflect the headers
  given with `-I`.
  [EQUATE](https://jbc-lang.org/pages/equate.html)
- `#ifdef` and `#ifndef` test whether a case-sensitive symbol has been
  defined by EQUATE or `#define`. A defined value of zero counts as
  present. Nest blocks with optional `#else` and close them with
  `#endif` or `#end` in the same file. Directives start at column one
  and accept either `#` or `$` as a prefix. `#define NAME replacement`
  captures existing substitutions and preserves an existing definition
  of NAME. Definitions are shared across includes for the translation
  unit, so an include can guard itself against repeated insertion.
  Inactive branches skip code, new definitions and include lookups.
- BEGIN CASE evaluates conditions in order, executes the first true arm,
  and resumes after END CASE. Use CASE 1 for a default. The reference
  grammar allows zero arms. When the block is empty or contains only
  comments, execution continues with the statement after END CASE. [CASE](https://jbc-lang.org/pages/case.html)

## Built-in functions

CHAR returns the byte for its argument's integer part modulo 256, as in
TAFC PB201214: `CHAR(300)` is `,`, `CHAR(-1)` is byte 255 and `CHAR(65.9)`
is `A`. A code that comes to 0, such as `CHAR(0)` or `CHAR(256)`, gives
byte 0.

Strings can hold byte 0, as TAFC's can (NUL-BYTES.md,
`tests/tafc/nul-core.b`, `nul-arrays.b`). Concatenation, LEN, SEQ,
substrings and their assignment, LEFT, RIGHT, comparisons (byte order, then
length), CRT and PRINT, STR, TRIM, UPCASE and DOWNCASE, QUOTE, CHECKSUM,
the MX, MCP, MCPN, MCNP, MCA, MCN and MCB conversions, dynamic array
extraction and assignment, INSERT, DELETE, REPLACE, REMOVE, LOCATE, SORT,
FIELD, FIELDS, GROUP, INDEX, COUNT, DCOUNT, CHANGE, EREPLACE, SWAP, CONVERT,
the element-wise functions such as LENS, COUNTS, CATS, SPLICE, STRS,
OCONVS and FMTS, the element comparisons, OSREAD, OSWRITE, WRITESEQ,
READBLK, WRITEBLK, file records and keys, CAPTURING, RETURNING, PASSDATA,
RTNDATA, passed select lists, INPUT, KEYIN and DATA handle it too.

`CHECKSUM(value)` sums each unsigned byte times its one-based position
in the string representation. For example, `CHECKSUM('AB')` returns 197
and an empty string returns 0. jbcc reports an out-of-range result if
the sum exceeds the native unsigned integer range. Byte 0 counts as a
byte, so the guide's `CHECKSUM(CHAR(0):'!')` is 66, as in TAFC.
[CHECKSUM](https://jbc-lang.org/pages/checksum.html).

`DYNTOXML(array, xsl[, result])`, `XMLTODYN(xml, xsl[, result])` and
`XMLTOXML(xml, xsl[, result])` accept a writable scalar or matrix element
as the optional result code. An empty stylesheet requests generic
conversion for DYNTOXML and XMLTODYN. Executing any of these functions
reports a source-located error because XML conversion requires a backend.
[DYNTOXML](https://jbc-lang.org/pages/dyntoxml.html),
[XMLTOXML](https://jbc-lang.org/pages/xmltoxml.html),
[XMLTODYN](https://jbc-lang.org/pages/xmltodyn.html).
`DYNTOXMLEXT(array, xsl[, result])`, which T24 R19 uses but neither the
guide nor the PB201214 headers define, parses the same way and reports
the same error when reached.

`DATELOCALETOGREGORIAN(date, format, calendar, format, locale)` and
`DATEGREGORIANTOLOCALE` with the same arguments convert dates between
calendars in T24 R19 (`EB.API` `ConvertLocaleDateToGregorian`). Neither
the guide nor the PB201214 headers define them. They parse, and a reached
call reports a source-located error because calendar conversion requires
a backend.

`READXML var FROM [file,] key` and `READXMLU` parse like READ and READU,
with `SETTING`, `ON ERROR`, `LOCKED` for READXMLU, and THEN or ELSE. The
guide describes a transform through the file's `DICT @READXML` style
sheet. A reached statement reports a source-located error because that
transform requires an XML backend.
[READXML](https://jbc-lang.org/pages/readxml.html).

`JBASECOREDUMP(suffix, mode)` accepts two expressions. A reached call
reports a source-located error because application snapshots require a
backend. [JBASECOREDUMP](https://jbc-lang.org/pages/jbasecoredump.html).

`VALIDATE_PRODUCT_LICENSE(product)` accepts one expression, as in the
reference grammar and keyword table. The local jBC 201015.001 reference
lowers it to a TAFC licence check. A reached call reports a
source-located error because licence checks require a backend.

`SEQ(value)` returns the unsigned value of the first byte of its string
representation. For example, `SEQ("ABC")` is 65 and `SEQ(@FM)` is 254.
jbcc provisionally returns 0 for an empty string. UTF-8 strings use the
same byte rule in the current runtime.
[jBASE SEQ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SEQ.htm).

T24 declares `SEQX` as a function in `I_COMMON`. The corpus implementation
uses a character table in its ASCII/EBCDIC compatibility path and calls
SEQ in UTF-8 mode. jbcc resolves it through DEFFUN and the linked function
implementation. [T24 Programming Standards](https://www.acosani.it/infobasic/libri/T24%20Programming%20Standards.pdf).

`ASCII(value)` converts IBM EBCDIC code page 037 bytes to ISO-8859-1
bytes. `EBCDIC(value)` reverses that mapping. The guide describes a
character table and gives an example that CP037 reproduces. It leaves
the exact table unspecified, so this code page is provisional. The
conversion operates on bytes, including high bytes and array marks.
[ASCII](https://jbc-lang.org/pages/ascii.html), [EBCDIC](https://jbc-lang.org/pages/ebcdic.html),
[CP037 mapping](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/EBCDIC/CP037.TXT).

`UTF8(value)` encodes ISO-8859-1 bytes as UTF-8, including bytes used
as array marks in jBC values. For example, `UTF8(@FM)` emits the two
bytes for U+00FE. `LATIN1(value)` decodes UTF-8 characters in the range
U+0001 through U+00FF back to bytes. jbcc provisionally reports a
source-located error for malformed UTF-8 or an unrepresentable
character. Both functions operate on the supplied runtime value,
independently of the source encoding flag.
[UTF8](https://jbc-lang.org/pages/utf8.html), [LATIN1](https://jbc-lang.org/pages/latin1.html), [jBASE CHAR](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_CHAR.htm).

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
selected dynamic-array component. CONVERT and CHANGE check conditionally
assigned scalar targets at runtime before updating them. The function
form returns a new value. Under prime emulation its arguments are
`CONVERT(from, to, text)`, the order T24 uses, so
`CONVERT('ab', 'xy', 'aabbc')` returns `xxyyc`. Under
`--emulation jbase` they are `CONVERT(text, from, to)`. A repeated source
byte uses its first mapping, as TAFC does. [CONVERT](https://jbc-lang.org/pages/convert.html).

`INDEX(text, needle, occurrence)` returns the one-based byte position of
the requested match, or zero when it is missing. For example,
`INDEX('ab--ab', 'ab', 2)` returns 5. As in TAFC PB201214, matches do
not overlap, a fractional occurrence is truncated toward zero, an empty
needle is found at position 1, and a nonpositive occurrence returns zero.
[INDEX](https://jbc-lang.org/pages/index.html).

LEFT and RIGHT extract leading and trailing bytes respectively. For example,
`RIGHT("The world is my lobster", 7)` returns `"lobster"`. A length below
one gives an empty string, and a length exceeding the input size gives the
whole string. Both functions use the existing substring rules for numeric
lengths, truncating fractional values toward zero. In an expression,
`Text[n]` is equivalent to `RIGHT(Text, n)`. For example,
`Record<2>[3]` reads the last three bytes of the second field.
[LEFT](https://jbc-lang.org/pages/left.html), [RIGHT](https://jbc-lang.org/pages/right.html).

LEN counts bytes in the current byte-oriented runtime. FIELD accepts a
one-based occurrence and optional field count. The expression
`Text[delimiter, occurrence, count]` calls the same FIELD runtime as
`FIELD(Text, delimiter, occurrence, count)`. For example,
`"a/b/c/d"["/",2,2]` returns `b/c`. An occurrence or count below one
means one, as in TAFC PB201214, so `FIELD(S, ':', 0)` is the first field.
FIELD, COUNT and DCOUNT support multi-byte delimiters. COUNT counts
nonoverlapping occurrences under prime and overlapping ones under
`--emulation jbase`, as TAFC PB201214 does (`COUNT('aaaa', 'aa')` is 2
and 3); DCOUNT and COUNTS follow COUNT. DCOUNT returns zero
for an empty record. For an empty delimiter, COUNT and DCOUNT return the
byte length and FIELD returns the whole input, as TAFC does. With a
multi-byte delimiter and a count above one, TAFC's results follow no
consistent rule; jbcc matches the whole delimiter throughout. NOT uses
the same truth conversion as IF.
[FIELD](https://jbc-lang.org/pages/field.html), [COUNT](https://jbc-lang.org/pages/count.html),
[DCOUNT](https://jbc-lang.org/pages/dcount.html), [LEN](https://jbc-lang.org/pages/len.html).

`COUNTS(array, substring)` counts matches, as COUNT does, in each element
and preserves field, value and subvalue marks. A match cannot cross a mark.
An empty substring returns each element's byte length. Ordinary empty
elements return zero. The guide describes a distinct null value, which
jbcc's value model currently lacks.
[jBASE COUNTS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_COUNTS.htm).

`Text[delimiter, occurrence, count] = replacement` replaces the byte
span selected by the bracket expression. Delimiters outside that span
are preserved. With `:=`, the new text is appended to the selected span.
The same syntax works on matrix elements and dynamic-array components.
This follows the reference generator's three-operand assignment form.
For an occurrence beyond the end, jbcc provisionally inserts enough
delimiters to reach it. An empty delimiter permits replacing the whole
value at occurrence one. Assignment leaves the saved FIELD positions
unchanged. These edge cases await a jBASE runtime comparison.

`COL1()` and `COL2()` report the one-based byte positions immediately
before and after the last scalar FIELD selection, including the bracket
form. `COL1()` returns 0 at the start of the string, and `COL2()` can
return the string length plus one. jbcc provisionally keeps these
positions for the process and resets both to 0 for a missing occurrence
or an empty delimiter. An existing empty field still has positions.
Element-wise FIELDS leaves the saved positions intact.
[COL1 and COL2](https://jbc-lang.org/pages/col1_and_col2.html).

`GROUP(text, delimiter, first [, count])` uses the same selection
and position tracking as FIELD in jbcc. It matches the full delimiter
and keeps delimiters between the returned fields. The reference
compiler defaults an omitted count to one. A start beyond the last
field returns an empty string.
[jBASE GROUP](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/group_function.html).

`BYTELEN(value)` counts bytes, including each field, value and subvalue
mark. For example, `BYTELEN('é')` is 2 for a UTF-8 literal. It uses the
same byte-count operation as LEN in the current runtime.
[BYTELEN](https://jbc-lang.org/pages/bytelen.html).

`LENDP(value)` uses the same byte count as LEN and BYTELEN in jbcc's
current mode. Trailing spaces, control bytes and array marks each count
as one byte. For example, `LENDP('é漢')` returns 5 for a UTF-8 literal.
The jBASE guide describes Unicode display positions under International
Mode. [jBASE LENDP](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_LENDP.htm).

`FOLD(text, width)` wraps text into fields separated by attribute
marks. It prefers spaces as break points, trims spaces at line edges,
and splits words longer than the width. A zero width folds at one byte,
following the guide's example. jbcc provisionally measures width in
bytes and folds each existing field independently.
[jBASE FOLD](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_FOLD.htm).

`COMPARE(left, right[, justification])` returns -1, 0 or 1 using
bytewise string ordering. The default `L` compares from the left.
For `R`, jbcc provisionally compares as if the shorter string had leading
spaces, reusing LOCATE's right-justified ordering. This produces the
guide's TAFJ result for `XY999` and `XY1000`. An explicit justification
must be `L` or `R`.
[COMPARE](https://jbc-lang.org/pages/compare.html).

EQS and NES compare corresponding fields, values and subvalues using
scalar equality, including numeric comparison for numeric pairs. Both
retain the combined array structure. EQS returns 1 for an equal pair and
0 for an unequal pair. NES returns 0 and 1 respectively. A missing
element counts as unequal. For the guide's null-element rule, jbcc
provisionally treats an explicitly empty element as null and leaves
that result position empty. A scalar occupies the first position.
A direct `REUSE(scalar)` in either argument repeats it at every position;
`REUSE` of a dynamic array has no effect, as in TAFC.
[EQS](https://jbc-lang.org/pages/eqs.html), [NES](https://jbc-lang.org/pages/nes.html).

`LES`, `LTS`, `GES`, and `GTS` use the same array structure and scalar
ordering. They test less than or equal, less than, greater than or equal,
and greater than, respectively. Each ordered comparison supplies an
empty string for a missing element and compares it with the available
element. An explicitly empty element still leaves its result position
empty under the provisional null rule. All four accept `REUSE(scalar)`
in either argument.
[jBASE LES](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_LES.htm),
[UniVerse vector functions](https://docs.rocketsoftware.com/bundle/universebasicuser_ug_1221/page/sat1687881202320.html).

`ADDS(left, right)`, `SUBS`, `MULS` and `DIVS` add, subtract, multiply
and divide corresponding fields, values and subvalues with the arithmetic
and PRECISION of the scalar operators. Under prime emulation, as TAFC
PB201214 runs them, a missing or empty element counts as 0, so
`ADDS('', 1:@VM:2)` is `1]2` and `MULS('', 3)` is 0. A nonnumeric element
warns at the call site and counts as 0, and a zero or empty divisor warns
and gives 0 for that position; execution continues.

Under `--emulation jbase` the earlier rules apply: ADDS copies an
unmatched element, MULS gives 0 for one, DIVS keeps the dividend for a
missing divisor, and an empty element in a pair leaves its position
empty; SUBS counts empty or missing elements as 0.

A direct `REUSE(scalar)` in either argument repeats that scalar at every
position and evaluates it once. `REUSE` of a dynamic array has no effect,
so its elements pair as usual, as in TAFC (`ADDS(REUSE(1:@VM:2), 3)` is
`4]2`). `array * REUSE(scalar)`, `REUSE(scalar) * array` and the matching
`/` forms use the same element-wise rules; this follows the infix form
seen in T24's LI.SECURED.ONLINE.
[ADDS](https://jbc-lang.org/pages/adds.html), [SUBS](https://jbc-lang.org/pages/subs.html),
[MULS](https://jbc-lang.org/pages/muls.html), [DIVS](https://jbc-lang.org/pages/divs.html).

`array / REUSE(scalar)` and `REUSE(scalar) / array` divide element by
element, preserving the dynamic-array marks. jbcc evaluates each REUSE
operand once. A numeric zero divisor reports a runtime error at the
division operator, following jbcc's scalar `/` rule.

CATS concatenates corresponding fields, values and subvalues. An unmatched
element is copied through, and a wholly empty operand returns the other
array. jbcc treats an empty element within an array as contributing zero
bytes, pending a reference run. A direct `REUSE(scalar)` can supply a
prefix or suffix at every position. [CATS](https://jbc-lang.org/pages/cats.html).

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

### In-memory cache

`JBC.h` declares the cache functions with `DEFC`, and jbcc's runtime
implements them. A declaration with the header's `VAR` signature lowers to
that runtime, including in the browser. Other `DEFC` functions still report
that they need the jBASE C runtime. The built-in `JBC.h` carries the same
declarations and the `CACHE_*` equates, so the guide's examples run as
written. The snippet `tests/snippets/cache.b` reproduces each example's
output.

- `CachePut(bucket, item, value)` creates the bucket if needed and counts a
  put. `CacheGet(bucket, item)` returns the value or an empty string. It
  counts a get, plus a hit when the item exists. `CacheExists` returns 1
  or 0. `CacheDelete`, `CacheKeyList` and `CacheBucketList` leave the
  statistics unchanged. The two lists are sorted by name, as in TAFC.
- `CacheStats(bucket, counter)` reads `CACHE_HITS`, `CACHE_GETS`,
  `CACHE_PUTS`, `CACHE_SIZE` and `CACHE_NB_ITEMS`; `CACHE_SIZE` is the
  number of items, as in TAFC PB201214. `CacheClearStats` resets the
  counters. `CacheClear` removes a bucket with its counters and options,
  so a later `CacheGet` counts nothing, and `CacheClearAll` removes every
  bucket.
- `CacheGetOption` returns zeros for a missing bucket and otherwise
  `CACHE_MAX_SIZE` (default 1048576) and `CACHE_PURGE_THRESHOLD`
  (default 90). `CacheSetOption` creates the bucket. When a bucket's
  item count exceeds `CACHE_MAX_SIZE * CACHE_PURGE_THRESHOLD / 100`, jbcc
  removes its least recently written or read items until it fits. The
  guide only says that "the most outdated data" is purged, so this order
  is provisional. Unknown counters and options read as 0.
  The functions return an empty string where the guide shows no result.
  [CachePut](https://jbc-lang.org/pages/cacheput.html),
  [CacheStats](https://jbc-lang.org/pages/cachestats.html),
  [CacheGetOption](https://jbc-lang.org/pages/cachegetoption.html).

### Catalogue functions without T24 calls

The functions below appear in the guide or the reference keyword table,
but the T24 corpora never call them. Each one follows the guide's
description and reproduces its examples, which the snippets in
`tests/snippets/` check. The local TAFC PB201214 runtime stops at its
licensed-user check, so no reference run confirms these results.
Choices marked provisional rest on the function's name or a dialect
convention rather than on the guide.

- `TAN(degrees)` takes degrees like SIN and COS. `ASIN`, `ACOS` and
  `ATAN` have no guide page and return degrees by the same convention
  (provisional). Their results are rounded to 12 places, so `ASIN(-0.5)`
  is -30. [TAN](https://jbc-lang.org/pages/tan.html).
- `FADD(a, b)` rounds to PRECISION like FSUB. `FMUL` and `FDIV` ignore
  PRECISION. Their guide examples, 14.48652932 and 0.1428571429, show ten
  significant digits, which jbcc uses. `FCMP(a, b)` returns -1, 0 or 1
  for floating-point order (provisional). Null operands and a zero
  divisor report source-located errors.
  [FADD](https://jbc-lang.org/pages/fadd.html), [FDIV](https://jbc-lang.org/pages/fdiv.html).
- `SADD(a, b[, places])` and `SSUB(a, b[, places])` add and subtract
  decimal strings exactly, then keep 14 fractional places as TAFC PB201214
  does: a sum of operands with the same sign rounds half away from zero,
  and one with opposite signs truncates toward zero
  (`tests/tafc/string-math-rounding.b`). The optional third argument
  changes the limit. A nonnumeric operand of SADD, SSUB, SMUL or SDIV
  warns `Non-numeric value -- ZERO USED` and counts as 0. `SCMP(a, b)`
  returns -1, 0 or 1 for decimal order (provisional; it crashes TAFC
  PB201214).
  [SADD](https://jbc-lang.org/pages/sadd.html), [SSUB](https://jbc-lang.org/pages/ssub.html).
- `BITSET`, `BITRESET`, `BITCHANGE` and `BITCHECK` operate on a
  per-process table of 128 flags. Each returns the bit's previous value.
  Bit 0 sets or resets the whole table for BITSET and BITRESET, and is an
  error for the other two. Codes -1 to -3 are kept as separate switches
  without the guide's break-key or restart effects (provisional).
  `BITLOAD()` returns the table as uppercase hexadecimal without trailing
  zero digits. `BITLOAD(hex)` loads the table from the left, stops at the
  first non-hexadecimal character, clears the remaining bits, and returns
  the previous table. The guide names that result `VALUE.OLD`
  (provisional). [BITCHANGE](https://jbc-lang.org/pages/bitchange.html),
  [BITLOAD](https://jbc-lang.org/pages/bitload.html). BITTEST is reserved
  in the guide and remains unsupported.
- `ISCNTRL`, `ISGRAPH`, `ISPRINT`, `ISPUNCT` and `ISXDIGIT` test every
  byte with C-locale ASCII rules and return 0 for an empty string. Bytes
  above 127, the system marks included, belong to no class, so
  `ISCNTRL(@FM)` is 0 as in TAFC PB201214; the guide's example says 1.
  [ISCNTRL](https://jbc-lang.org/pages/iscntrl.html), [ISPRINT](https://jbc-lang.org/pages/isprint.html).
- `ANDS`, `ORS` and `MODS` pair elements as ADDS does. The guide's null
  rules use jbcc's empty string as null. For ANDS, a null beside a true
  value gives null, as in UniVerse (provisional). `IFS(cond, true, false)`
  picks the element at the same field, value and subvalue position for
  each condition element, and reproduces the guide's TAFC output.
  [ANDS](https://jbc-lang.org/pages/ands.html), [ORS](https://jbc-lang.org/pages/ors.html),
  [MODS](https://jbc-lang.org/pages/mods.html), [IFS](https://jbc-lang.org/pages/ifs.html).
- `SEQS`, `CHARS` and `STRS` apply SEQ, CHAR and STR to each element and
  keep null elements null. STRS returns an empty string for a repeat count
  below one. `LENSDP` is LENS in the byte runtime.
  [SEQS](https://jbc-lang.org/pages/seqs.html), [CHARS](https://jbc-lang.org/pages/chars.html),
  [STRS](https://jbc-lang.org/pages/strs.html).
- `SOUNDEX(text)` uses the guide's code table. It keeps the first letter,
  ignores other characters and reads a repeated letter once, so
  `SOUNDEX('Pfister')` is P123 rather than the census P236.
  [SOUNDEX](https://jbc-lang.org/pages/soundex.html).
- `REGEXP(text, expression)` uses POSIX extended expressions. It returns
  the one-based position of the first match, 0 for no match and -1 for an
  invalid expression. [REGEXP](https://jbc-lang.org/pages/regexp.html).
- `CHANGETIMESTAMP(stamp, adjustments)` applies
  `Years^Months^Weeks^Days^Hours^Minutes^Seconds^Milliseconds`. Years and
  months move along the UTC calendar. A day missing from the target month
  becomes that month's last day (provisional), and the other fields add
  fixed durations. [CHANGETIMESTAMP](https://jbc-lang.org/pages/changetimestamp.html).
- `DELENV(name)` removes an environment variable and returns 1, or 0 if
  the variable was absent. `DIR(path)` returns `size^date^time^D` with the
  local modification date and time in internal format. A directory has
  size 0, and a missing path returns an empty string (provisional).
  `GETUSERNAME(uid)` returns the login name.
  `GETUSERGROUP(uid)` returns the primary group number, since the guide
  says Windows returns zero. These four functions are unavailable in the
  browser. [DIR](https://jbc-lang.org/pages/dir.html),
  [GETUSERGROUP](https://jbc-lang.org/pages/getusergroup.html).

The rest of the catalogue still has no jbcc support. CRC, FFIX, FFLT,
ERRTEXT, PERROR, CONTROLCHAR and TA have no guide description precise
enough to implement. JQL*, TRANS, XLATE, TRANSQUERY, TRANSSYNC, SPOOLER,
SELECTINFO, the XML.* functions and the licence calls need a database,
spooler or licence backend.

## Statements and values T24 does not use

These come from the guide and behave as TAFC PB201214 runs them; the
probes in `tests/tafc/` record its output.

- `OUT n` writes one byte, the integer part of n modulo 256, with no
  newline.
- `GROUPSTORE value IN target USING start, replace{, delimiter}` inserts
  value before group start (replace 0) or replaces that group, adding empty
  groups as needed; the delimiter defaults to `@FM`.
- `INPUTNULL c` sets the character that `INPUT @` reads as an empty answer;
  plain INPUT keeps it.
- `LOCK n` and `UNLOCK {n}`: one process holds every execution lock it
  asks for, so LOCK takes THEN.
- `PROCREAD var` takes ELSE, since no jCL program starts a jbcc program, and
  `PROCWRITE` does nothing. `RQM` is SLEEP.
- `PAUSE {seconds}` waits, forever without a timeout, unless a `WAKE` for
  this process came first.
- `IN var {FOR tenths} THEN | ELSE` reads one byte from standard input,
  not from the DATA queue, and sets var to its code.
- `CHAIN command` and `ENTER name` (or `ENTER @variable`) run the command
  and end the program with its exit status; the `(I` option is dropped, as
  separately built programs share no COMMON.
- `PRINTERR id:@FM:argument` prints ` ** Error [ id ] ** ` and the message
  for 201 and 202, and TAFC's "Error message ... not found" line for others.
- `READL` and `READVL` read with a shared lock, which `RECORDLOCKED` reports
  as 1 (2 for READU). `MATWRITEU` keeps the record lock, and `DELETEU`
  deletes as DELETE does. `SELECTV`, `SSELECTV`, `SELECTN` and `SSELECTN`
  select as SELECT and SSELECT do.
- `TRANS(file, key, field, code)` and `XLATE` read a field from an open
  in-memory file, `"DICT name"` for a dictionary. Field -1 is the whole
  record and 0 the key, and the result's marks are lowered one level. A
  missing record gives `''` with code X, the key with C (also for an empty
  field), and a warning with V. Keys separated by value marks give one result
  each.
- `@DAY`, `@MONTH` and `@YEAR` are the day, month and two-digit year of
  `@DATE`; `@UID` is the process's user id; `@EOF` is `CHAR(4)`; `@LEVEL`
  is 0; `@DATA`, `@CODEPAGE`, `@LOCALE`, `@USER.THREAD` and `@CALLSTACK` are
  empty.
- `SYSTEM(1)` is 0 (no printer), `SYSTEM(2)` and `SYSTEM(3)` the terminal's
  width and depth (`COLUMNS` and `LINES`, else 80 and 24), `SYSTEM(7)` the
  terminal type, `SYSTEM(12)` the milliseconds since midnight,
  `SYSTEM(35)` to `SYSTEM(39)` the C locale's `C`, `0`, `,`, `.` and `$`,
  `SYSTEM(40)` the program name and `SYSTEM(1017)` `UNIX`. For the keys T24
  reads, `SYSTEM(11)` is the default select list's count, `SYSTEM(1019)`
  the host, and `SYSTEM(1021)` a TAFC-style release string that names jbcc
  and contains `TEMENOS`, so T24's `SYSTEM(1021)[1,4] = 'TAFJ'` test takes
  the TAFC path; 25, 32, 43, 47, 91, 600, 1025, 2003 and 2021 are 0 and
  1027, 1029, 1039 and 2090 are empty, as in TAFC PB201214.
  `ASSIGN value TO SYSTEM(n)` keeps the value for `SYSTEM(n)` to return,
  as TAFC does (`tests/tafc/system-keys-t24.b`).

## Sequential files

`OPENSEQ path TO F` and `OPENSEQ directory, name TO F` open regular files
on the native filesystem. Relative paths use the executable’s working
directory. `READONLY` takes a shared advisory lock. A writable open takes
an exclusive lock. Contention with another process takes `LOCKED` when
supplied, otherwise `ELSE`. A program can open a file it already has open
through OPENSEQ or OSOPEN again, as TAFC PB201214 allows. POSIX terminals also open without a file lock. Pipes and
other devices take the I/O error branch.
[OPENSEQ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_OPENSEQ.htm).

A missing file takes `ELSE` and leaves a pending handle. `CREATE F THEN … ELSE …`
creates and opens an empty file through that handle. If another handle
created the file first, CREATE takes ELSE and preserves the existing
contents. Passing an empty value to CREATE gives a source-located error.
The first `WRITESEQ` can also create the file. `OPENSEQ EXISTING` and
`READONLY` disable deferred creation. [CREATE](https://jbc-lang.org/pages/create.html).

`OPENDEV path TO F` uses the same grammar and regular-file handles as
`OPENSEQ`, following the reference lexer. It starts at the beginning
of the file by default. A missing path takes `ELSE` with status 128.
Lock contention takes `LOCKED` when present or `ELSE` otherwise.
For terminal paths, this provides a handle for querying settings.
[OPENDEV](https://jbc-lang.org/pages/opendev.html).

`TTYGET Settings FROM F [SETTING S] THEN … ELSE …` queries an open
terminal handle using POSIX `tcgetattr`. The reference parser requires
`FROM` and permits either conditional arm. The dynamic array follows
the positions documented by IBM and used by the T24 sources. jbcc fills
input mode, minimum bytes and timeout in field 1, echo in `<7,1>`,
baud code, data bits, stop bits and output parity in `<10,2>` through
`<10,5>`, and signal keys and break handling in `<11,1>` and
`<11,3>`. Other positions and baud rates outside the legacy table
return empty values. jbcc maps canonical mode to line mode and
noncanonical mode to raw mode. A regular file returns 32768 and a
closed or pending handle returns 128. Errors clear the destination and
take `ELSE` when supplied. Printer and tape channel forms remain
unsupported. [TTYGET](https://www.ibm.com/docs/en/iis/11.7.0?topic=functions-ttyget-statement).

`TTYSET Settings ON F [SETTING S]` applies the fields supported by
`TTYGET` to a POSIX terminal. It accepts either conditional arm.
Empty positions preserve the current setting. The initial mapping
accepts line and noncanonical modes, numeric baud codes 1 through 15,
and noncanonical timeouts in multiples of 100 milliseconds. In line
mode, the terminal ignores the noncanonical byte count and timer.
jbcc validates the full request before applying changes. An empty
request, an unsupported populated position, an invalid value, or a
regular file returns status 32768. A closed or pending handle returns
128. If the driver applies only part of a request, jbcc attempts to
restore the prior settings and reports status 32768. On success
`SETTING` and `STATUS()` both report 0.
[IBM BASIC Reference Guide](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

`NOBUF F` disables stdio buffering on an open sequential handle. Call
it after OPENSEQ or CREATE and before any operation on the stream. It
also affects aliases of the handle, and repeating it after success is
allowed. With `SETTING`, jbcc returns 0 on success and 128 for a missing
or pending handle. It returns 32768 if the buffered stream was already
used or the buffering change fails. Conditional arms are optional,
following the reference grammar. Without an arm or SETTING, a failure
produces a source-located runtime error.
[NOBUF](https://jbc-lang.org/pages/nobuf.html).

`OSOPEN path TO F` uses the same regular-file handles, locks, and
conditional clauses as OPENSEQ, following the reference lexer's mapping.
It also searches `JEDIFILEPATH` for a missing bare name and accepts
`WRITEONLY` alongside `READONLY`. Line and block operations on the
handle respect the access mode. Opening with `WRITEONLY` preserves
existing bytes until a write. `OSCLOSE F` closes the handle and
invalidates aliases. It accepts `ON ERROR` for a failed close.
[OSOPEN](https://jbc-lang.org/pages/osopen.html),
[OSCLOSE](https://jbc-lang.org/pages/osclose.html).

`OSBREAD value FROM F [AT offset] LENGTH count` reads bytes from an
open OSOPEN or OPENSEQ handle. Offset and count are nonnegative integers.
The offset is zero-based. jbcc provisionally reads from the current
position when AT is omitted and leaves the cursor after the bytes read.
A short read returns the available bytes, and a read at or beyond EOF
returns an empty value with status 0. Byte 0 becomes byte 128, as in
TAFC PB201214.
`SETTING` and `STATUS()` report the result. Failures take `ON ERROR`
when present or report the statement location.
[OSBREAD](https://jbc-lang.org/pages/osbread.html).

`OSBWRITE value TO F [AT offset] [NODELAY]` writes bytes to an open
writable handle and converts byte 128 to NUL. ON is a synonym for TO.
The cursor advances by the bytes written. Omitting AT provisionally
uses the current cursor. jbcc flushes every block and also requests
`fsync` for NODELAY. The statement accepts `SETTING` and `ON ERROR`.
A failed write reports the source location when no error arm is present.
[OSBWRITE](https://jbc-lang.org/pages/osbwrite.html).

`OSREAD value FROM path` reads a regular file into a scalar or
record context variable. It strips one final LF, turns every other LF into
a field mark and keeps carriage returns, as TAFC PB201214 does, so a file
of lines reads as a dynamic array. It keeps byte 0, as TAFC does
(`tests/tafc/nul-io.b`). A bare name that is missing
from the working directory is searched for in the colon-separated
`JEDIFILEPATH`. The reference grammar accepts `SETTING` and `ON ERROR`
with a required THEN or ELSE arm. jbcc uses sequential file status codes
and clears the destination on failure. A missing file takes ELSE with
status 128. Other I/O errors take ON ERROR when present or report the
statement location.
[OSREAD](https://jbc-lang.org/pages/osread.html).

`OSWRITE value [APPEND] TO path` replaces a regular file or creates it
if absent. It accepts ON instead of TO. APPEND follows the reference
grammar. A missing bare name is looked up in `JEDIFILEPATH` before jbcc
creates it in the working directory. The write preserves supplied line
endings and converts byte 128 to NUL. jbcc takes an exclusive lock before
truncating or writing. The statement accepts `SETTING` and `ON ERROR`,
and a failure without an error arm reports the statement location.
[OSWRITE](https://jbc-lang.org/pages/oswrite.html).

`OSDELETE path [SETTING code] [ON ERROR statements]` removes an OS file.
A bare name is resolved in the working directory first, then in
`JEDIFILEPATH` if it is missing. A path containing a slash is used as
given. The POSIX backend uses `unlink`, which removes a symbolic link
itself and rejects directories. `STATUS()` returns 0 for success and 1
for failure. jbcc assigns the same value to the optional `SETTING`
variable accepted by the reference grammar. A failed deletion runs
`ON ERROR` or reports the statement location.
[OSDELETE](https://jbc-lang.org/pages/osdelete.html).

`DELETESEQ directory, item` or `DELETESEQ path` removes a sequential file,
joining the directory and item with `/` as OPENSEQ does. It accepts
`SETTING`, `ON ERROR` and `LOCKED`, and requires THEN or ELSE, as in the
reference grammar. The POSIX backend uses `unlink` without a
`JEDIFILEPATH` search. A missing file sets status 128 and takes ELSE;
other failures run `ON ERROR` when present.
[DELETESEQ](https://jbc-lang.org/pages/deleteseq.html).

`TIMEOUT F, seconds` accepts an open sequential handle and nonnegative
decimal seconds. A pending or closed handle and an invalid duration
report an error at the statement. The regular-file backend completes
READSEQ and READBLK with available bytes or EOF, so the requested
timeout requires no timer there. EOF still yields status 128. Terminal
handles report a source-located error until device timeouts are supported.
[TIMEOUT](https://jbc-lang.org/pages/timeout.html).

`READBLK Block FROM F, Size` reads a positive number of bytes at the
current position, including line endings and field marks. A complete
block takes THEN. Following the guide's EOF rule, jbcc provisionally
takes ELSE with an empty destination on a short read, and the position
advances past any bytes consumed. A block keeps byte 0, as in TAFC.

`WRITEBLK Block TO F` (or `ON F`) writes at the current byte position
without adding a newline. A missing file must first be created with
CREATE using its pending handle. The reference grammar accepts SETTING
and requires at least one conditional arm on either statement. jbcc
uses the sequential status codes, with 0 on success, 128 for EOF or a
missing handle, and 24576 for a read-only write. Empty operands raise a
source-located error. [READBLK](https://jbc-lang.org/pages/readblk.html),
[WRITEBLK](https://jbc-lang.org/pages/writeblk.html).

`SEEK F, offset, origin` positions a regular-file handle in bytes. Origins
0, 1 and 2 count from the start, current position and end respectively.
Both numeric operands default to zero, so `SEEK F ELSE STOP` rewinds.
Seeking past EOF extends the file only when a subsequent write occurs.
A pending handle takes ELSE and leaves the path absent. Following the
reference parser, jbcc accepts `SETTING` before the required THEN or ELSE
arm. Empty operands produce a source-located runtime error. jbcc takes
ELSE for fractional offsets, invalid origins and positions outside the
host file-offset range. [SEEK](https://jbc-lang.org/pages/seek.html).

`REWIND [UNIT(channel)] [ON channel]` issues a tape rewind with a required
THEN or ELSE arm. The channel defaults to 0 and must be an integer from
0 through 9. The reference grammar accepts FROM in place of ON and gives
UNIT precedence when both operands appear. jbcc has no attached tape
media, so every valid channel takes the no-media path with `SYSTEM(0)`
set to 1. This leaves the file `STATUS()` value intact.
[Rocket jBASE REWIND](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/rewind_statement.html).

`READT [UNIT(channel)] record [FROM channel]` requires a THEN or ELSE
arm. The reference grammar accepts scalar and matrix-element destinations
and the same channel forms and precedence as REWIND. With no attached media,
jbcc sets `SYSTEM(0)` to 1 and takes ELSE when present. It provisionally
clears the destination based on UniVerse's documented failed-read behavior.
[jBASE READT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_READT.htm),
[IBM UniVerse READT](https://www.ibm.com/docs/en/iis/11.3.0?topic=functions-readt-statement).

`WRITET [UNIT(channel)] record [ON channel]` evaluates the record
expression and requires a THEN or ELSE arm. It accepts TO from the guide
and FROM from the reference grammar as alternatives to ON. UNIT takes
precedence over a trailing channel. With no attached media, jbcc sets
`SYSTEM(0)` to 1 and takes ELSE when present.
[WRITET](https://jbc-lang.org/pages/writet.html).

`WEOF [UNIT(channel)] [ON channel]` requests an end-of-file mark on a
tape channel. Following the reference grammar, jbcc accepts FROM in
place of ON and requires a THEN or ELSE arm. UNIT takes precedence,
and the default channel is 0. With no attached media, jbcc sets
`SYSTEM(0)` to 1 and takes ELSE when present.
[WEOF](https://jbc-lang.org/pages/weof.html).

`WEOFSEQ F` truncates at the current byte position. After a `READSEQ`,
the retained prefix includes the line terminator. The next read sees EOF,
and the next write starts at that same position. WEOFSEQ accepts `SETTING`,
`ON ERROR` and optional `THEN` or `ELSE` arms. On a pending writable
handle jbcc creates an empty file, following the usage in T24’s ATM.CONTROL.
That case is provisional pending a reference run. [WEOFSEQ](https://jbc-lang.org/pages/weofseq.html).

`READSEQ` consumes a line, strips the newline and takes `ELSE` at EOF.
For long lines jbcc returns the first 1,024 bytes and advances to the
following line. That advancement is provisional pending a reference run.
A line ends at byte 0: the rest of it is skipped, as TAFC PB201214 reads
it (`tests/tafc/nul-io.b`).
[READSEQ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_READSEQ.htm).

`WRITESEQ` adds a newline at the current position. Its `APPEND` option
seeks to the end before each write, and `WRITESEQF` also synchronizes
the file to disk. The grammar’s `OPENSEQ APPEND` starts at the end of
an existing file. `CLOSESEQ` releases the lock and invalidates aliases.
`SETTING` returns 0 on success, 128 for missing files or EOF, 24576 for
denied writes, and 32768 for other I/O failures. jbcc uses −2 for lock
contention, following its existing lock convention.
[WRITESEQ](https://jbc-lang.org/pages/writeseq.html) and
[CLOSESEQ](https://jbc-lang.org/pages/closeseq.html).

`FLUSH F` flushes the sequential stream and accepts `SETTING` and
optional branch clauses. An unopened pending file takes ELSE with
status 128 and stays absent. An empty handle produces a source-located
error. Native writes already flush the stdio stream, and WRITESEQF also
synchronizes the file to disk. [FLUSH](https://jbc-lang.org/pages/flush.html).

`FILEINFO(handle, 0)` returns 1 for a valid open handle or 0 for an
unassigned variable, a failed open, or a pending sequential file.
`FILEINFO(handle, 2)` follows the UniVerse pathname convention used by
T24, provisionally returning an absolute path for a sequential handle,
the logical name for an in-memory file, or an empty string for an
invalid handle. Other keys produce a source-located diagnostic.
[jBC FILEINFO](https://jbc-lang.org/pages/fileinfo.html),
[UniVerse BASIC Reference](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf).

`IOCTL(handle, 100, output)` retrieves the name of an open file. Use
`-1` for the default record file. On success it returns 1 and stores
the registered memory-file name or the absolute sequential-file path
as text. On failure it returns 0 and preserves the output variable.
Other command numbers produce a source-located diagnostic.
[jBASE IOCTL](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/sup22_IOCTL.htm).

`INDICES(file)` queries the file's secondary indexes. The optional
expression in `INDICES(file, indexName)` requests information about one
index. The file operand is a variable or a matrix element, as in the
reference grammar. Executing either form reports a source-located error
because jbcc's file backend has no secondary-index metadata.
[jBASE file index metadata](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/JRCS_INTERFACE.htm).

## In-memory file tests

The test backend starts with empty files explicitly named at translation
time. Each execution starts fresh. To run the example:

```sh
./jbcc --memory-file CUSTOMERS tests/io/records.b -o /tmp/records.c
cc -std=c99 /tmp/records.c -o /tmp/records
/tmp/records
```

`OPEN '', Name` opens the same data file as `OPEN Name`. To exercise
`OPEN 'DICT', Name`, pass `--memory-dict NAME` at translation time.
The in-memory backend registers the data and dictionary sections independently.
For example, `--memory-file CUSTOMERS --memory-dict CUSTOMERS` provides
both sections, each with its own records. Opening an unregistered section
takes the failure branch.

The reference lexer maps OPENPATH to OPEN. Both use the same record
store. Register the exact relative or absolute path with `--memory-file`,
for example `--memory-file data/customers`. The in-memory backend compares
path strings literally. A host file at that path needs its own backend.
`OPENPATH path TO F SETTING S` sets S to 0 on success or 128 if the
registered file is missing. Omit the descriptor to select the default.
[OPENPATH](https://jbc-lang.org/pages/openpath.html).

`STATUS info FROM F SETTING S THEN … ELSE …` returns a dynamic array for
an open descriptor. For memory files, attribute 6 counts the bytes in the
current record values, attribute 20 contains the registered name or path,
and attribute 21 contains `MEMORY`, the test backend’s type. The other
attributes are empty. In particular, hashed-file modulo and separation
(22 and 23) and the T24-specific lookup at 27 yield empty strings.

For regular sequential files, attributes 1–4 give the current byte offset,
EOF flag, stream error flag and remaining byte count. Attributes 5–12
come from the open file’s permissions, size, link count, owner, group,
inode and device numbers. Attributes 13–18 give access, modification and
status-change times as local seconds since midnight and jBC dates.
Attribute 19 is zero, 20 gives the absolute path and 21 is `SEQ`.
STATUS observes the stream in place. An invalid nonempty descriptor clears
the output, sets S to 128 and takes ELSE. An empty descriptor raises a
source-located runtime error. Success sets S to 0. The SETTING clause is
optional. [STATUS statement](https://jbc-lang.org/pages/status_statement.html).

`STATUS()` reports the last record or sequential file operation's
result, including inside its success, failure, or LOCKED arm. The
initial result is 0, and a called routine's file operation updates
the same process-wide value. The STATUS statement still returns file
attributes and updates the operation result. `STATUS()` can differ
from `SETTING`. For example, a successful MATREAD sets the field count
but `STATUS()` returns 0.

jbcc provisionally reports its backend's status codes, including
128 for missing records or files and -2 for a simulated foreign lock.
The function currently tracks record and sequential file operations.
Conversion status and reference-specific OS error numbers remain
outside this implementation. [STATUS function](https://jbc-lang.org/pages/status.html).

READ and WRITE accept an explicit descriptor and key, or just a key for
the default file. For example, after `OPENPATH path ELSE STOP`,
`WRITE 'Ada' ON '1'` and `READ name FROM '1' ELSE STOP` use the same file.
OPEN and READ require THEN or ELSE. READ accepts optional SETTING
and ON ERROR. The memory backend provisionally sets the READ status
to the empty string on success. A missing record or invalid descriptor
clears the record destination, sets the status to 128 and takes ELSE.
Other incremental file errors are routed to ON ERROR when supplied.
A failed OPEN also clears its destination.

WRITE accepts SETTING and ON ERROR as well as THEN and ELSE. It sets
its optional status to 128 for an invalid descriptor or 32768 for a
simulated foreign lock. On success it releases an owned update lock
and sets the status to the empty string, the same provisional success
status as WRITEU.
A failed WRITE with no status or branch terminates at the source location.
Stored records survive reassignment and loop temporary cleanup.
[OPEN](https://jbc-lang.org/pages/open.html), [READ](https://jbc-lang.org/pages/read.html),
[WRITE](https://jbc-lang.org/pages/write.html).

`CLOSE F` unassigns the named record descriptor, so `ASSIGNED(F)`
returns 0. `CLOSE F,G` processes the variables from left to right. A
single descriptor accepts `ON ERROR`; an unhandled invalid descriptor
produces a source-located runtime error. The reference grammar requires
a variable. Other variables and the default descriptor can still access
the same records, and reopening the file preserves its contents.
[CLOSE](https://jbc-lang.org/pages/close.html).

The memory backend releases the program’s locks on that file at each
explicit close, even if it has another descriptor for the file. Simulated
foreign locks survive. Closing a local descriptor through a reference
argument also cancels its pending cleanup when the opening routine returns.
Lock lifetime varies by jBASE version and configuration.
[jBASE record locking](https://static.zumasys.com/jbase/r99/knowledgebase/howto/general/common/RecordLocking.htm).

`FILELOCK` and `FILEUNLOCK` use an explicit descriptor or the default
file. In the in-memory backend, a simulated foreign record lock prevents
acquisition. A `LOCKED` arm handles that conflict with status `-2`.
Without that arm, the conflict takes the error path with status `32768`.
`ON ERROR` handles invalid descriptors, which report status `128`.
`FILELOCK` also accepts `SETTING`. The in-memory lock is owned by the
program and appears as an owned lock in `RECORDLOCKED`. Closing the file
or using `FILEUNLOCK` clears it. `FILEUNLOCK` leaves record locks in place.
[FILELOCK](https://jbc-lang.org/pages/filelock.html), [FILEUNLOCK](https://jbc-lang.org/pages/fileunlock.html).

READU acquires an update lock on a key in an explicit or default file.
An existing record takes THEN. A missing record takes ELSE and keeps the
lock so the caller can create it. Re-reading an owned key succeeds if the
record exists. In the test backend, SETTING receives the empty string on
success, 128 for a missing key, and 32768 for an invalid descriptor.
ON ERROR handles the invalid descriptor.

Use `--memory-file F --memory-lock F busy` to simulate another process
holding an update lock on the key `busy`. READU takes LOCKED, preserves
the destination and sets SETTING to -2 in this backend. A fixture lock is
permanent for the run. A conflicting READU without LOCKED reports its
source location. Timed WAIT and cross-process synchronization are outside
the in-memory backend.

RECORDLOCKED returns 2 for an owned update lock, -2 for a simulated
foreign lock, and 0 for an unlocked key. WRITE, MATWRITE and DELETE
release an owned lock on the affected key. Use `RELEASE F, Key` or
`RELEASE Key` for a single key, or bare `RELEASE` for all owned locks.
All three forms accept `ON ERROR`. With that clause, the in-memory
backend provisionally sets STATUS() to 128 for an invalid descriptor
and executes the arm. Success sets STATUS() to zero. A valid descriptor
succeeds even when the requested key has no owned lock. RELEASE only
removes locks held by the current process. Without an error arm, it
discards the backend status.
Returning from a routine that opened a file into a local variable
releases that process’s locks on the file. [READU](https://jbc-lang.org/pages/readu.html),
[RELEASE](https://jbc-lang.org/pages/release.html), [RECORDLOCKED](https://jbc-lang.org/pages/recordlocked.html).

`RECORDLOCKU F, key` acquires an update lock without reading a record.
Supply just the key to use the default file. The reference compiler
uses its update-lock and no-record flags, so an unused key can be
reserved. The native backend supports `SETTING`, `ON ERROR`, `LOCKED`,
`THEN` and `ELSE`. A simulated foreign lock takes `LOCKED` with status
−2. Waiting for a simulated lock produces a source-located diagnostic.

WRITEU writes a record to an explicit or default file and preserves an
owned update lock. In the in-memory backend, writing an unlocked key
leaves it unlocked. A regular WRITE, MATWRITE, DELETE, or RELEASE can
release the retained lock. WRITEU sets the optional status to 128 for an
invalid descriptor or 32768 for a simulated foreign lock, and either
failure takes ON ERROR when supplied. jbcc provisionally uses an empty
status on success, as with READU. [WRITEU](https://jbc-lang.org/pages/writeu.html).

WRITEV and WRITEVU replace a single field in an explicit or default file.
For example, `WRITEV "value" TO F, Key, 7` changes field seven, fills any
gap with empty fields, and creates the record if needed. Field numbers
must be positive integers. WRITEV releases an owned update lock after
writing. WRITEVU preserves an owned lock and leaves an unlocked key
unlocked in this backend. Both use the same provisional success status
and failure handling as WRITEU. [WRITEV](https://jbc-lang.org/pages/writev.html),
[WRITEVU](https://jbc-lang.org/pages/writevu.html).

DELETE removes a record by key. `DELETE F, Key` uses the descriptor F.
`OPEN Name ELSE ...` sets the default descriptor for `DELETE Key`. A
missing record counts as success. In this backend, `SETTING Code` receives
0 on success or 128 for an invalid descriptor. `ON ERROR` runs on failure.
An optional `LOCKED` arm handles simulated foreign record locks. It keeps
the lock in place and reports `-2` via `STATUS()` and `SETTING`, matching
jbcc's CLEARFILE convention. Without that arm, contention is an error
with status `32768`. A failed DELETE with neither `ON ERROR` nor
`SETTING` terminates with the source location.
[DELETE](https://jbc-lang.org/pages/delete.html).

CLEARFILE removes every record from the selected in-memory file. Its
descriptors stay open for subsequent reads and writes. Use `CLEARFILE F`
for an explicit descriptor or bare `CLEARFILE` for the default file.
jbcc sets the optional `SETTING` variable to the empty string on success,
consistent with the guide’s example, or to 128 for an invalid descriptor.
`ON ERROR` handles failure in the same way as for DELETE. The reference
parser also allows `LOCKED` after the optional error arm. A simulated
foreign record lock takes this arm and leaves all records and locks in
place. jbcc reports `-2` through `STATUS()` and `SETTING` in that arm.
Without a `LOCKED` arm, contention follows the existing error path with
status `32768`.
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

READVU reads the same fields as READV and acquires an update lock like
READU. A missing record takes ELSE with status 128 and keeps the lock.
A simulated foreign lock takes LOCKED with status -2 and preserves the
destination. An invalid descriptor clears the destination and takes
ON ERROR with status 32768 in the in-memory backend. WRITE or RELEASE
can release the owned lock. [READVU](https://jbc-lang.org/pages/readvu.html).

MATREAD fills a dimensioned array from a record in the selected in-memory
file. For example, `MATREAD A FROM F, Key SETTING N ELSE STOP` splits the
record on field marks, varying the last matrix subscript fastest. The final
element receives any excess fields with their separators intact. A short
record clears the unused elements. On success N counts all record fields,
including those packed into the final element. jbcc counts an empty record
as zero fields. A missing record preserves the matrix, sets N to 128, and
takes ELSE. Omitting `F,` uses the default descriptor. The in-memory backend
supports ON ERROR with the same status handling as READV. [MATREAD](https://jbc-lang.org/pages/matread.html).

MATREADU uses the same field mapping and acquires the same update lock as
READU. A missing key remains locked for creation. The matrix retains its
previous contents on a miss (SETTING 128), a simulated foreign lock
(SETTING -2, LOCKED), or an invalid descriptor (SETTING 32768, ON ERROR).
MATWRITE to the same key releases the lock. [MATREADU](https://jbc-lang.org/pages/matreadu.html).

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

File `SSELECT F TO L` takes a snapshot of the open file's record IDs
in ascending byte order. Record IDs in this snapshot use field marks as
separators, so an ID containing a field mark splits into separate entries.
Omit the source for the default file and omit
`TO` for list 0. A named or numbered destination has its own cursor.
A missing file clears the destination and runs the optional `ON ERROR`
arm. The reference grammar permits `SETTING`. jbcc provisionally reports
an empty status on success and 128 on failure, matching SELECT. An
unhandled failure without `SETTING` produces a runtime diagnostic.
[SSELECT](https://jbc-lang.org/pages/sselect.html).

`READNEXT Key FROM L THEN ... ELSE ...` returns one key, and
`LOOP WHILE READNEXT Key FROM L DO` uses the same operation as a Boolean
expression. On exhaustion jbcc clears the destination and returns false.
For ordinary keys the optional multi-value position is zero.

`@ID` holds the current record ID and is shared across routines.
`@ID = Key` sets it explicitly, as in the guide's ITYPE example.
`READNEXT @ID` writes the next key in either statement or expression
form. A regular READNEXT destination leaves the context unchanged.
jbcc starts `@ID` as an empty string and clears it when a
`READNEXT @ID` reaches the end of its list. These two empty-value rules
are provisional pending a reference run. [ITYPE](https://jbc-lang.org/pages/itype.html),
[jBASE SSELECT](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_SSELECT.htm).

`@RECORD` holds the current record text in a separate slot shared
across routines. It supports whole-value assignment, dynamic-array
extraction, and use as a destination for READ, READU, READV, or READVU.
Reading into another variable leaves this slot intact. jbcc starts it
as an empty string. A missing record read into it clears it, following
the existing READ destination behavior.
[ITYPE](https://jbc-lang.org/pages/itype.html).

`@FILENAME` holds the current file name for dictionary evaluation. In
jbcc it starts empty and is shared across routines in a separate slot
from `@ID` and `@RECORD`. Whole-value assignment and an explicit read
destination can set it. An ordinary OPEN or READ leaves the name in
place. The startup value and sharing policy are provisional.
[ITYPE](https://jbc-lang.org/pages/itype.html).

`@COMPANYNO` is a session value that a program can read and assign with
`@COMPANYNO = expression`, shared across routines in its own slot. T24 R19
sets it from the company record (`@COMPANYNO =
R.COMPANY(EB.COM.LOCAL.CONTENT.POS)` in `EB.QUERY.BUILDER`) and clears it
when loading a company. Neither the guide nor the 2011 reference compiler
defines it ("Unknown @ system constant"), so jbcc treats it as a plain
session value that starts empty and has no other effect; the startup
value is provisional.

`ITYPE(descriptor)` accepts one expression for a compiled dictionary
descriptor. In jBASE, evaluation uses the current `@FILENAME`, `@ID`,
and `@RECORD` context. Reaching an ITYPE call in jbcc reports a
source-located error because dictionary evaluation requires a backend.
[ITYPE](https://jbc-lang.org/pages/itype.html).

With an explicit string or dynamic array, SELECT makes a list of its fields
in source order. Value and subvalue marks stay inside their fields. Leading,
interior and trailing empty fields are entries. jbcc treats a completely
empty source as an empty list. Reassigning the source leaves the selected
fields available to READNEXT. A standalone `//` line, as used in the
guide’s CLEARSELECT example, is accepted as a separator. [SELECT](https://jbc-lang.org/pages/select.html),
[READNEXT](https://jbc-lang.org/pages/readnext.html).

`SELECTE TO L` copies the active default list into a variable or numbered
list. In jbcc the destination starts at the default list's current
cursor and the two cursors advance independently. An empty default list
produces an empty destination. Optional `SETTING Code` receives 0.
This cursor behavior is provisional for the in-memory backend.

`FORMLIST Keys TO L` starts a fresh cursor over the field-mark-separated
entries in `Keys`. Omitting `TO` selects the default list. A number from
0 through 10 selects a numbered list. A quoted decimal integer such as
`TO "1"` addresses the same list as `TO 1`. The reference grammar also accepts
`SETTING N`. Its runtime result is undocumented in the guide, so jbcc
provisionally sets `N` to the entry count, including empty fields. An
empty array has zero entries. [FORMLIST](https://jbc-lang.org/pages/formlist.html).

For named saved lists, set `JBCC_LIST_DIR` to an existing directory shared
by the executables. `WRITELIST Items TO Name` (also `ON Name`) atomically
replaces the named list. jbcc stores field-mark-separated bytes and encodes
the list name as a single filename. This directory format is specific to
jbcc. `SETTING Status` reports zero on success, 128 for a missing directory,
24576 for permission errors and 32768 for other write errors. A failed write
runs the optional `ON ERROR` arm.

`READLIST L FROM Name SETTING N THEN ... ELSE ...` assigns the list and
its element count. Use `READNEXT` to iterate it. An empty saved list takes
THEN with count zero. A missing list takes ELSE and clears both outputs
(the count becomes zero). The reference grammar also permits omitting
FROM. In jbcc, omitted FROM, an empty name or literal `FROM 0` transfers
the remaining entries of the default select list and clears that cursor.
This transfer behavior is provisional. `FROM '0'` reads a named list.
Writing to an empty name sets the default list for the current process.
[READLIST](https://jbc-lang.org/pages/readlist.html),
[WRITELIST](https://jbc-lang.org/pages/writelist.html).

`@SELECTED` reports the count from the last default external selection.
The guide distinguishes this from BASIC SELECT and selections into
other lists. In jbcc, `WRITELIST Items ON ''` supplies the count, including
empty fields. The count starts at zero and is shared across routines.
jbcc provisionally keeps the recorded count through READNEXT,
CLEARSELECT and list retrieval. jQL commands require a query backend to
supply the count. [@SELECTED](https://jbc-lang.org/pages/@selected.html).

`GETLIST Name TO L SETTING N THEN ... ELSE ...` retrieves the same saved
list and element count as READLIST. The reference grammar permits omitting
`TO L` to restore the default cursor, as in `GETLIST Name ELSE STOP`
followed by `READNEXT Key`. A numbered destination such as `TO 2` is
also supported. An empty name retrieves the remaining default selection.
`DELETELIST Name` removes the stored list from `JBCC_LIST_DIR`. A cursor
already retrieved can finish iterating its copy. Provisionally, deleting
an absent name succeeds and deleting an empty name clears the default
cursor. [GETLIST](https://jbc-lang.org/pages/getlist.html),
[DELETELIST](https://jbc-lang.org/pages/deletelist.html).

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
Under prime emulation the last coordinate is where the search starts, at
the level below the coordinates before it:

- `record<f>` searches fields, starting at field f;
- `record<f,v>` searches the values of field f, starting at value v;
- `record<f,v,s>` searches the subvalues of value v, starting at s.

So `LOCATE ID IN LIST<1> SETTING POS`, common in T24, searches the fields
of LIST. An optional comma and starting position apply only without
coordinates; after coordinates TAFC ignores it. Under `--emulation jbase`,
every coordinate selects: `record<f>` searches the values of field f,
`record<f,v>` the subvalues of value v, and a third coordinate is the
starting subvalue; a separate start then produces a compiler diagnostic.
In both emulations a trailing zero coordinate is dropped, so `<2,0>`
means `<2>`. The function form `LOCATE(key, record{, f{, v}}; pos{; order})`
takes the same coordinates. Positions are one-based within the searched
level.

A match sets `pos` and takes the THEN branch. An unordered miss sets it
one past the end, or to the starting position when that is further. With
`BY`, a miss returns the insertion position for an already sorted array.
jbcc supports AL/DL (byte order), AR/DR (right-justified), and AN/DN
(numeric when both values are numbers). Under prime, AR/DR compare two
numbers numerically, two other values right-justified and a mixed pair
byte by byte, so `100` sorts before `B` and `b2` before `b10`. Either
branch can use `NULL` as a no-op. These rules follow TAFC PB201214 runs
(`tests/tafc/locate-*.b`). [LOCATE](https://jbc-lang.org/pages/locate.html).

## Check whether a variable has a value

`ASSIGNED(X)` returns 1 after X receives any value, including zero or an
empty string. `UNASSIGNED(X)` returns the opposite. Both can inspect a
scalar, a COMMON variable, a routine argument, or a dimensioned matrix
element. Testing a variable leaves it untouched. For example,
`IF UNASSIGNED(X) THEN X = ''` supplies a default while preserving any
existing value. A dynamic-array extraction such as
`UNASSIGNED(X<I,J>)` is evaluated, and its result is always assigned. The
local jBC 201015.001 reference applies the test to any expression this way;
jbcc accepts extractions and R19 component calls, such as
`UNASSIGNED(IN.Config.getBicDetails())`, and otherwise requires a variable.
A component call is treated like an extraction, so its result counts as
assigned. This is provisional, because the dump does not define the
generated accessor.
[ASSIGNED](https://jbc-lang.org/pages/assigned.html),
[UNASSIGNED](https://jbc-lang.org/pages/unassigned.html).

## Walk a dynamic array

`REMOVE item FROM record SETTING mark` reads the next delimited string.
For `record = 'a' : @FM : 'b'`, successive calls return `a` with mark 2,
then `b` with mark 0. Further calls return mark 0 and leave `item`
unchanged. Bytes 255 through 249 give delimiter codes 1 through 7.

`REMOVE(record, mark)` returns the next delimited string as an expression
and assigns the same delimiter code. jbcc uses the same cursor for both
forms on a bare variable or matrix element. An exhausted function call
returns an empty string and code 0. Following the reference grammar,
the first argument may also be a computed value. jbcc treats that value
as a fresh array for the call.
Both forms check a conditionally assigned source at runtime. If the
source has no value, the diagnostic points to the source operand.

The cursor belongs to the variable. Assigning `record = record` rewinds it,
and copying the value to another variable starts an independent traversal.
COMMON variables, matrix elements and by-reference arguments preserve their
own cursor across calls. [REMOVE in the jBASE manual](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_REMOVE.htm).

## User-defined functions

Declare a function before its first use with `DEFFUN DOUBLE.IT()`. Parameter
names in a declaration are optional. The compiler checks each call against
the supplied `FUNCTION` definition. A standalone call such as
`DOUBLE.IT(N)` discards the result. As with `CALL`, scalar variables and
matrix elements are passed by reference and expressions use temporary slots.
Pass a whole matrix with `CALL UPDATE(MAT Rows)` or `F(MAT Rows)`, and
declare the receiving parameter with `MAT` in SUBROUTINE or FUNCTION.
The callee uses the caller’s storage and bounds, including for COMMON
matrices and calls that forward the parameter. When a DEFFUN lists
parameters, mark its matrix parameters with MAT as well. T24 routines
often repeat DIM for a MAT parameter. Pending a reference run, jbcc
checks that such a declaration matches the caller’s dimensions exactly.
An empty string literal can stand in for a MAT argument. Executing DIM
for that parameter allocates storage local to the invocation. Using the
parameter as a matrix before DIM reports a source-located error.

```sh
./jbcc --exe tests/routines/function.caller.b tests/routines/DOUBLE.IT -o /tmp/function-caller
/tmp/function-caller
```

The caller prints `43` from `1 + DOUBLE.IT(21)`. The function returns
`N * 2` through a hidden result argument. A bare `RETURN` gives an empty
string. The example follows the calling convention in the
[DEFFUN](https://jbc-lang.org/pages/deffun.html) and
[FUNCTION](https://jbc-lang.org/pages/function.html) chapters.

`DEFC [type] name([type, ...])` declares a C function. Supported
types are INT, FLOAT, VAR and STRING. Declarations apply from their source
position and calls are checked for arity. Executing a declared function
reports that it requires the jBASE C runtime and exits with the call
location. [DEFC](https://jbc-lang.org/pages/defc.html).

## Check a local source corpus

The coverage goal is to translate every program, subroutine and function in
the local T24 sources to valid C99, expanding include fragments wherever
they are used. The latest counts and the next language feature are in
[the compiler plan](PLAN.md).

The commands below use `201001-R10` in a sibling `t24-extract` checkout.

```sh
python3 tools/check_corpus.py ../t24-extract/201001-R10 -j 8 > /tmp/jbcc-corpus.json
```

The checker visits regular files recursively. It counts `I_` files as include
fragments and expands them when referenced by a compilation unit. It runs
the compiler's preprocessor, parser and C generator on each remaining file.
For direct external calls it declares a prototype per observed arity so
the system C compiler can check the generated unit with C99 warnings as
errors. Different argument counts for one target produce a
`linkage_diagnostic` in the JSON report. Executable builds still validate
each call against its target's actual parameter list.
For indirect calls and exit callbacks it checks the dispatch code using the
current unit. Native tests exercise lookup across multiple linked units.
Additional include directories can be supplied with `-I`.
Legacy T24 sources include `JBC.h`, `jportB.h` and `jimiB.h` from the
PB201214 installation. A sibling `jbc-extract` checkout holds that
installation as a tarball. Unpack its headers once into `.cache/`, which
git ignores:

```sh
just tafc-headers    # writes .cache/PB201214/include
```

The checker accepts the same source encoding option as the compiler.
For legacy T24 sources with those headers, run

```sh
python3 tools/check_corpus.py ../t24-extract/201001-R10 -I .cache/PB201214/include \
  -j 8 --source-encoding bytes > /tmp/jbcc-corpus.json
```

For R10, add `--t24-source-fixes` to apply the three known corrections
to files at the corpus root in memory before parsing.
The report's `source_fixes` entries give the original file, line, column,
and replacement for each edit. Diagnostics on edited lines use the
columns of the text passed to the lexer. The scan reads the original
files from disk. To include legacy scalar reads in the same scan, pass
both `--t24-source-fixes` and `--defer-unassigned-reads`.

Use `--quiet-next-warnings` to print one total on stderr for FOR/NEXT
name mismatches. Other warnings still print individually and the JSON
report keeps its normal diagnostics. Direct `jbcc` invocations print
the source location of each mismatch.

The JSON report records a status per relative path, diagnostic locations,
and counts by first blocker. A translated unit passed C syntax checking.
With `--defer-unassigned-reads`, the per-file `warnings` list records
deferred reads in translated units.
Linking its external dependencies and verifying its behavior require separate
tests. UTF-8 decoding failures are counted separately and identify the
source or include that could not be decoded.

### T24 corpus flags

The T24 extracts are real vendor code, not test material. Each release
carries its own weirdness: typos that a later compiler tolerated, files
left out of the dump, generated code that the dump does not define,
conversion slips and inconsistent component exports. The checker's T24
flags let the scans use as much of these sources as possible for testing
jbcc, without letting jbcc itself accept anything the language does not
allow. They follow three rules:

- They affect only `tools/check_corpus.py`. The compiler, the playground
  and native builds never apply them.
- They never edit the extract. Fixes and generated files live in memory
  or in a separate directory.
- Every use is reported in the JSON report (`source_fixes`,
  `include_stubs`, `include_lookups`, `warnings`, the `excluded` status
  and its `reason`), so a scan shows exactly what it relied on.

Source handling:

- `--source-encoding bytes` reads each source byte for byte, as Latin-1,
  instead of decoding UTF-8. T24 sources contain bytes from older code
  pages, and literals must keep them unchanged. All T24 scans use it.
- `--defer-unassigned-reads` turns a read that jbcc cannot prove is
  assigned into a runtime check and a `warnings` entry, instead of a
  translation error. This includes the target of `CONVERT` and `CHANGE`,
  as in R19 `IN2BMT`, which converts a variable two lines before
  assigning it. T24 relies on variables assigned through COMMON or
  in other routines, which a single-unit scan cannot see.
- `--quiet-next-warnings` replaces the many `NEXT` name mismatch warnings
  (`FOR I ... NEXT J`) with one total on stderr.
- `--t24-source-fixes` applies a short list of known corrections in memory
  and reports each as `source_fixes` with the original file, line, column
  and text. Each fix is a pattern bound to one file, and the files on
  disk are not changed:
  - R10 (corpus root), R13 (`T24.BP/`), R07 (`GLOBUS.BP/`) and R19
    (`SE/SE_TestRetail`): `STEST.AZ.PD.DATES.CHK` reads
    `<.AZ.SLS.TYPE.I,POS>` with a stray leading dot.
  - R10: `TK.VALIDATE.SYSGEN.FILES` names a variable `1ST.RECORD`, which
    cannot start with a digit, and `LIST.DATA` writes `FM` for `@FM`.
  - R07: `COMPARE.DB.JBASE` includes `/usr/jbc/include/JBC.h` by an
    absolute path; `MG.EOD.REDEFINE.CONTRACT.RATES` passes an extra
    argument to a matrix element; `TU.LIB.STD.CDF` and `TU.LIB.STD.INV`
    write decimal coefficients in exponent form.
  - R19, fixes named by path from the root: two AA `DAS` inserts end an
    `EQU` with a comma and repeat `EQU` on the next line;
    `CALEND.PAY.RESERVE.ACCOUNT.LOAD` writes two assignments on one line
    without a `;`; `AT.GEN.ISO.RES.MSG` lacks the `:` before a second
    `FMT` in a `PRINT`.
- `--stub-r07-la-parameter` supplies a translation-only
  `I_F.LA.PARAMETER` (`tools/corpus_stubs/r07/`) for the R07 units that
  include it, because the R07 dump lacks it. Each use is reported in
  `include_stubs`.

Selection and exclusion:

- `--t24-catalog SQLITE` uses the `t24-extract` catalog to classify files
  (production source, include, `.tut` test, data record, component) and
  scans only production sources.
- `--source-prefix PATH` scans only catalogued sources under `PATH`
  (whole path segments, repeatable).
- `--t24-exclude-local-routines` reports routines that are not Temenos
  code as `excluded` with a reason. R13 keeps one Raiffeisen Bank Polska
  routine, `T24.BP/V.PL.B2LIM.NET`, whose includes are absent.
- `--t24-exclude-test-framework` reports R19's test framework components,
  `SE/SE_Test*` (the SEAT harness and its tests, 1,321 units), as
  `excluded`, because they are out of scope for production translation.

R19 components and generated code:

- `--t24-indexed-includes` resolves `$INSERT` through the catalog: the
  including file's directory, its component, the include paths and then
  a release-wide index. R19 keeps inserts in module trees, not on one
  path. Each lookup is reported with the rule that resolved it. When
  several candidates are byte-identical, as R19's two copies of
  `I_DAS.POR.CLG.IN.SETTLEMENT.PENDING`, the first is used and the lookup
  lists them as `identical_copies`; different candidates stay ambiguous.
- `--t24-domain-inserts DIR` generates the `I_<Service>_<Class>` inserts
  that T24 generates from `.domain` models and the dump leaves out, from
  the catalogued classes, into `DIR`. Each generated lookup is reported
  with its `.domain` file.
- `--t24-exclude-missing-domains`, with `--t24-domain-inserts`, reports a
  unit as `excluded` when it includes an `I_<Service>_<Class>` insert
  whose class no catalogued `.domain` file declares; the reason names the
  insert. In R19, six `OB_PMT` units include inserts for
  `PORCreditTransferInitiation` and `BulkDetails`, which the dump's domain
  models lack. The lookup also records `domain_class: absent` without the
  flag.
- `--t24-component-calls` checks `Component.member(...)` calls against
  the catalogued `.component` declarations: visibility, argument count
  and scalar or matrix positions. The dump does not define the code T24
  generates from these declarations, so the checker applies these rules,
  each taken from how all R19 sources use the form:
  - table operations (`Read`, `ReadU`, `Write`, `Delete` and the others)
    and `table<Name>(id, error)` reads;
  - `get`, `set` and `clear` accessors, with the matrix rank from the
    binding (`->MAT.LEG(2)`);
  - hook `interface` members, called with the implementing method's name
    first, and `published` members, which are public;
  - methods without a body, which Java implements;
  - duplicate definitions of one component are partial exports: a member
    declared in any of them counts, unless they declare it differently;
  - a standard operation on a table that a catalogued component does not
    declare is accepted, with a `warnings` entry naming the table;
  - likewise a `get`, `set` or `clear` accessor of a property the
    component does not declare, as `LC.Foundation.getFDrawings()`, takes
    its arguments as given, with a `warnings` entry; a property the
    component's definitions declare differently stays an error;
  - a scalar passed for a matrix parameter is a placeholder: the call gets
    an empty matrix, as R19 `EbReadParameter` callers expect.
- `--t24-stub-members`, for testing only, accepts any arguments for the
  members listed in `T24_MEMBER_STUBS` in `tools/check_corpus.py`, with a
  `warnings` entry for each unit that uses one. It lists
  `TF.L3Helper.testPublishedMethod`, a Java varargs helper declared with 3
  parameters and called by the SEAT tests with 2 to 8; the 40
  `PP.InwardGenericTransactions.map<message>toPOR<part>` mappers, which
  `OB_PMT` holds as routines but no definition declares; other methods
  no definition declares, such as `TF.Core.DumpCommon`, the `TF.Core`
  coverage and call-recording methods and the `PpIn<message>Write`
  writers of `PP.InwardGenericTransactions`; and four
  methods whose declarations omit the `()` matrix marker on a parameter
  every caller passes with `MAT`, such as `AU.API.TransferBalance`.
- `--t24-relax-access`, for testing only, reports a call to a `private`
  or `module` member from another package as a `warnings` entry instead
  of an error. Three R19 units make such calls, which T24's own build
  evidently allowed.
- `--t24-stub-void-results`, for testing only, lets a method declared
  without a result be used as a value. The call is made and the value is
  `0`, with a `warnings` entry. R19 has about 25 such uses, as in
  `AF = EB.SystemTables.setAf(X)`, where the method is otherwise always a
  statement; they look like conversion slips.

The checker never uses jbcc's built-in `JBC.h`: scans see only the
headers given with `-I`, such as PB201214's.

### R07 corpus

The earlier R07.003 corpus is in `../t24-extract/200707-R07`. Its
`GLOBUS.BP` and `SENSITIVE.BP` folders are both on the include search
path. This scan uses the headers in the R07 extract.

```sh
python3 tools/check_corpus.py ../t24-extract/200707-R07 \
  -I ../t24-extract/200707-R07/GLOBUS.BP -I ../t24-extract/200707-R07/SENSITIVE.BP \
  --t24-catalog ../t24-extract/catalog.sqlite -j 12 --source-encoding bytes \
  --defer-unassigned-reads --quiet-next-warnings --t24-source-fixes --stub-r07-la-parameter \
  --api-catalogue ../jbc-language/spec \
  > /tmp/jbcc-r07.json
```

`--t24-catalog` reads the SQLite catalog's classifications for the named
extract. It counts jBC include fragments and C headers separately from
compilation units. Files absent from the catalog follow the usual `I_`
name rule. If only `catalog.sqlite.xz` exists, unpack it as described in
the extraction checkout's README. See the [R07 baseline](PLAN.md#r07-baseline)
for the first scan's results.

The optional `--stub-r07-la-parameter` enables a translation-only fallback for the
missing `I_F.LA.PARAMETER`. An include found next to its caller or on the
normal search path takes precedence. The stub supplies no field positions.
Each affected unit has an `include_stubs` entry in the JSON, and its
translation result provides no runtime validation of the missing layout.

The optional `--t24-source-fixes` applies the R07 workarounds in memory.
`COMPARE.DB.JBASE` uses the extracted `GLOBUS.BP/JBC.h` in place of the
absolute installation path. `STEST.AZ.PD.DATES.CHK` has its leading-dot
selector corrected as in R10. `MG.EOD.REDEFINE.CONTRACT.RATES` uses the
same one-subscript `CR.REC(CR.EVENT.DATE)` access as the surrounding code.
`TU.LIB.STD.CDF` and `TU.LIB.STD.INV` use the exact fixed-point forms of
their scientific-notation coefficients. The JSON records each edit.

Render the R07 API report with:

```sh
python3 tools/api_coverage.py /tmp/jbcc-r07.json > /tmp/jbcc-r07-coverage.md
```

### R13 corpus

The R13 corpus is in `../t24-extract/201307-R13`. Like R07, it has two
flat BP folders, `T24.BP` and `SENSITIVE.BP`, and both go on the include
search path. It has no C headers, so this scan takes `JBC.h` from the
PB201214 headers unpacked by `just tafc-headers`.

```sh
python3 tools/check_corpus.py ../t24-extract/201307-R13 -I .cache/PB201214/include \
  -I ../t24-extract/201307-R13/T24.BP -I ../t24-extract/201307-R13/SENSITIVE.BP \
  --t24-catalog ../t24-extract/catalog.sqlite -j 8 --source-encoding bytes \
  --defer-unassigned-reads --quiet-next-warnings --t24-source-fixes \
  --t24-exclude-local-routines --api-catalogue ../jbc-language/spec \
  > /tmp/jbcc-r13.json
```

`--t24-source-fixes` corrects the leading-dot selector in
`T24.BP/STEST.AZ.PD.DATES.CHK`, as in R10 and R07. The optional
`--t24-exclude-local-routines` skips `T24.BP/V.PL.B2LIM.NET`, a
Raiffeisen Bank Polska routine whose includes are not in the dump. The
JSON reports it with the status `excluded` and a reason. With these
options every other R13 unit passes strict C99 checking. See the
[R13 baseline](PLAN.md#r13-baseline) and [R13-CORPUS.md](R13-CORPUS.md)
for the constructs added for R13.

### R19 corpus

`201809-R19` is componentised T24: module trees and flat folders,
`$PACKAGE` and `$USING`, calls to component members and inserts
generated from `.domain` models. Select production sources from the
catalog, resolve includes through it and check component calls. The
full scan uses every [T24 corpus flag](#t24-corpus-flags):

```sh
python3 tools/check_corpus.py ../t24-extract/201809-R19 -I .cache/PB201214/include \
  --t24-catalog ../t24-extract/catalog.sqlite --t24-indexed-includes \
  --t24-domain-inserts .cache/domain-inserts/201809-R19 --t24-exclude-missing-domains \
  --t24-component-calls --t24-stub-members --t24-stub-void-results --t24-relax-access \
  --source-encoding bytes --defer-unassigned-reads --quiet-next-warnings \
  --t24-source-fixes -j 8 > /tmp/jbcc-r19.json
```

On 2026-11-27 it translated 39,669 of the 39,675 catalogued production
units to C that passes strict C99 checking, excluded 6 and rejected none,
in 4 min 59 s with 8 workers. It resolved 59,706 include references and
generated 17,225 domain inserts. Repeat `--source-prefix` to scan only
some paths. [R19-CORPUS.md](R19-CORPUS.md) records each step and decision.

Indexed lookup checks the including file's directory, its catalogued
component, the ordinary include search paths and then the release-wide
index. An indexed lookup with multiple matches at the current step
reports the candidates. The report lists resolved paths and lookup rules
per unit.

R19 sources include inserts generated from `.domain` models, named
`I_<Service>_<Class>`. The dump keeps only 30 of them. With
`--t24-domain-inserts DIR`, an indexed lookup that finds nothing else
generates the insert from the catalogued fields of that class, in the
component whose name ends in `<Service>`. Each field becomes
`EQU <Class>.<field> TO <n>`, numbered from 1 in declaration order;
associations count as fields. The rule reproduces the 20 kept inserts
whose `.domain` file is present. The checker writes the inserts to `DIR`
and reports each lookup as `generated`, with the `.domain` file it came
from. Two components with different layouts for one class make the
lookup ambiguous.

The compiler preserves `$PACKAGE` and `$USING` in source order.
The JSON reports their names and locations, including directives read
before a failed include. With `--t24-component-calls`, the checker reads
catalogued `.component` declarations for fully qualified methods,
property accessors and simple literal constants. It checks visibility
against the unit's `$PACKAGE` and checks scalar and matrix argument
positions. It recognizes indexed property access and whole-array
accessors such as `getDynArrayFromRNew()`. A property bound to a COMMON
matrix as `->R.NEW()` takes one index; a binding with a number, such as
`->MAT.LEG(2)`, gives the matrix rank, and its accessors take that many
indices, as in `FX.Contract.getMatLeg(LEG, FLD.NO)`. In all 116 numbered
R19 bindings the number is the rank the insert declares, and all 904
calls pass that many indices. A writable property also
has `clear<Name>()`, with no arguments, as R19 sources call it on scalar
and matrix-backed properties. Method declarations can give the result
type before or after the parameters, add `implements <interface>`, or be
`external` service methods, which count as public. Parameters can omit
the direction, use domain types with a multiplicity such as
`CustomerDomain:Parent [0..1]` or lists such as `list<string>`, and be
separated by newlines. Hook components declare `interface` members with no
body, as in `AA.ActivityHook.checkValidateRoutine`. Every R19 call passes
the implementing method's name before the declared parameters, so the
checker expects one more argument than the declaration lists; an
interface with a result type is a function. It also recognizes untyped
scalar properties. Where the catalog has multiple definitions for one
component, they are treated as partial exports: a member declared in any
of them is kept, and a member they declare differently is dropped. For
example, `OB_AFW/TF.ErrorHandling.component` lacks `consumeException`,
which `TF/TF_ErrorHandling` declares.

For `t24:` table declarations, the checker recognizes numbered field
constants and the call signatures observed in R19 sources. Reads return
the record: `Read`, `CacheRead`, `ReadNau` and `ReadHis` take the id and
an error variable, and the locking `ReadU`, `ReadUNau` and `ReadUHis` add a retry
argument. `Write`, `WriteNau` and `WriteHis` take the id and record, and
`Delete`, `DeleteNau` and `DeleteHis` take the id. The component also
has `table<Name>(id, error)`, a read with the table's visibility, as in
`AC.AccountOpening.tableAccount(ID, ERR)`. Field numbers are
available across components, as seen in R19 sources that reference
fields in private tables. Calls still follow the table's visibility.

The export leaves out some tables that sources read through a known
component, such as `PP.SODEODGUI.PptSodeodjoblist` and
`PP.InwardGenericTransactions.PpInDirectDebit`. A standard table operation
(`Read`, `ReadU`, `Write`, `Delete` and the others above) on an undeclared
table of a catalogued component is accepted with the standard signature
and public access, and the unit reports a warning naming the table. An
unknown component or a nonstandard operation is still rejected, and so is
an upper-case name: `EB.CONVERSION.LOG.WRITE` is a routine, while
generated table names are mixed case.

A scalar passed for a matrix parameter is accepted as a placeholder:
R19 passes one where the caller uses only another result, as in
`ST.CompanyCreation.EbReadParameter(file, lock, DIM.REC, R.REC, ...)`,
which reads the dynamic record `R.REC`. The call receives an empty matrix,
as for `''`, and the scalar keeps its value. A matrix passed for a scalar
parameter is still rejected.

`--t24-exclude-test-framework` reports the units of R19's test framework
components, `SE/SE_Test*` (the SEAT harness and its tests, 1,321 units),
as excluded with the reason "T24 test framework component", as
`--t24-exclude-local-routines` does for local routines. They are out of
scope for production translation.

With `--t24-source-fixes`, R19 fixes name each file by its path from the
extract root. Two `DAS` inserts, `I_DAS.AA.PRODUCT.DESIGNER` and
`I_DAS.AA.PRODUCT.LINE`, end an `EQU` with a comma and repeat `EQU` on the
next line; the local reference preprocessor reports a syntax error there,
so the checker drops the comma.

The pilot checks C syntax one unit at a time, using external prototypes
for qualified calls. Package-aware linkage and table runtime behavior
are still pending.

### API coverage

[COVERAGE.md](COVERAGE.md) summarizes recognized expression and `DEFC` calls
in R13 against the documentation repo's catalogues. Run the scan with
`--api-catalogue` to add guide references, forms, counts, source examples,
and test references to the JSON report. The report uses paths from your
local checkout and corpus.

```sh
R=../t24-extract/201307-R13
python3 tools/check_corpus.py $R -I .cache/PB201214/include -I $R/T24.BP -I $R/SENSITIVE.BP \
  --t24-catalog ../t24-extract/catalog.sqlite -j 8 --source-encoding bytes \
  --defer-unassigned-reads --quiet-next-warnings --t24-source-fixes \
  --t24-exclude-local-routines --api-catalogue ../jbc-language/spec > /tmp/jbcc-api-coverage.json
python3 tools/api_coverage.py /tmp/jbcc-api-coverage.json > COVERAGE.md
```

Calls counted after include and equate expansion can appear in several
translation units. The JSON tracks occurrences and C99-checked units
separately. Its snippet references identify source that contains a call.
Reviewed runtime assertions are recorded independently.

## Cross-check with TAFC

`tools/tafc_crosscheck/` runs jBC programs through jbcc and through the
reference runtime, TAFC PB201214, and compares their standard output.
TAFC runs in Docker from the sibling `jbc-internals` checkout: the
tarball `TAFC_PB201214_LINUX_ELF_AS6_106034-unbound.tar.gz` and the image
`jbc-internals-tafc-runner:local`, which is built from
`jbc-internals/docker` if missing. Each program runs under
`JBCEMULATE=prime`, as T24 does, unless a comment line near its top
names another emulation, such as `* tafc-emulation: jbase`.
[TAFC-CROSSCHECK.md](TAFC-CROSSCHECK.md) records the findings and the
plan that follows from them.

```sh
just tafc-guide                    # every guide code block, from ../jbc-language
just tafc-probe probe.b dir/       # probes side by side
just tafc-probe --record tests/tafc  # also save NAME.tafc.stdout
just tafc-recorded                 # jbcc against tests/tafc, no Docker
```

The guide and probe runs write `report.txt` and `report.json` under
`.cache/tafc/`. The guide report classifies each block as `same`,
`differ`, `jbcc-rejects`, `jbcc-fails` (TAFC ran it and exited with
status 0), `tafc-rejects` or `tafc-no-program`, and marks a difference
as volatile when the source reads the clock, the process or random
numbers. Comparison ignores carriage returns, trailing spaces and blank
lines at either end. A probe runs under its file name, which TAFC's
warnings and `SYSTEM(40)` show; guide blocks run as `P0001` and so on.

`tests/tafc/` holds probes with the standard output TAFC printed, as
`NAME.tafc.stdout`. `tests/test_tafc_probes.py` builds each one with jbcc
as part of `just test` and compares its output with TAFC's; the few
differences kept on purpose are skipped with their reason. A probe can name
jbcc options in a comment, such as `* jbcc-options: --memory-file VENDORS`
for a file TAFC creates with `CREATE-FILE`. `just tafc-recorded` lists the
same comparison without pytest.

TAFC prints its runtime warnings, such as `Divide by zero !!`, on
standard output, so they appear in the recorded output. Two TAFC
programs run in parallel by default (`--tafc-jobs`). More can fail to
start with licensing-semaphore or shared-memory errors, and the
container retries a program that fails that way.

## Python formatting

Use `just format` to sort imports and format Python sources, including
the `jbcc` script. Run `just check` to check both without modifying files.
Both recipes invoke Ruff through `uvx`.

## Test corpus

Run the full suite with pytest 9 through uv.

```sh
just test
just test tests/test_io.py
```

Run the same suite in parallel with pytest-xdist. The recipe defaults to
automatic worker selection. Pass a worker count and any pytest filters
after it.

```sh
just test-parallel
just test-parallel 4 -k executable_mode
```

With Clang as `cc`, native tests share one compiled object for the default
runtime, including across pytest-xdist workers. Feature-specific runtime
builds and compiler driver tests use embedded C. Other C compilers use
embedded C for every native build. Pass `--embedded-runtime` to compare
both modes.

Use a full run after changing the compiler, C runtime, or fixtures.
The tests exercise these files through subprocesses, so Python
test-selection caches alone cannot establish coverage for such changes.

Put self-contained, single-source success cases in `tests/snippets/` as
`.b` and `.stdout` pairs. Each pair is a parametrized pytest case named
after its source file. The runner invokes the CLI, compiles with strict
C99 warnings, and checks for exit zero, byte-for-byte stdout and empty
stderr. Python tests cover diagnostics, multiple sources, runtime setup
and side effects. Keep their static jBC source in checked-in `.b` files
as well. Generate source in Python when the test needs to construct or
vary it. Tests are grouped by behavior in `tests/test_*.py`.
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
- `quine2.b` is a multi-line quine. It keeps its own lines in a
  `^`-separated string, splits them with `DCOUNT` and `FIELD`, and builds
  quotes and separators with `CHAR`. Its native test also compares stdout
  with the source file.
- `banner.b` animates a 24-by-79 character display until a key is available.
  It exercises dimensioned arrays, substring assignment, fractional
  arithmetic, trigonometry, and terminal I/O. Build it with
  `./jbcc --exe tests/programs/banner.b -o /tmp/banner`. Run `/tmp/banner` in an
  ANSI terminal and enter a line to stop. The native test captures the blank
  opening frame and checks every pixel of the next frame before sending input.
- `snake.b` is a terminal Snake game with a 40-column by 20-row field.
  Run it with
  `./jbcc --run tests/programs/snake.b`. Steer with `w`, `a`, `s` and `d`,
  and press `q` to quit. These keys take effect without pressing Enter.
  The native test checks the opening board, turns the snake and quits
  through a pseudo-terminal.
- `life.b` runs Conway's Game of Life on a 40-column by 30-row board
  with dead cells beyond the edges. Run it with
  `./jbcc --run tests/programs/life.b` and press `q` to quit.
- `rule110.b` prints 32 generations of the Rule 110 automaton on a
  63-cell row, starting with one live cell and dead cells beyond the edges.
  Run it with `./jbcc --run tests/programs/rule110.b`.
- `fizzbuzz.b` prints FizzBuzz for 1 to 100 with `MOD` and string
  concatenation.
- `sieve.b` runs the Sieve of Eratosthenes up to 200 and prints the primes
  ten to a row, right-aligned with `FMT`.
- `hanoi.b` solves the Towers of Hanoi for four disks. `GOSUB` has no local
  variables, so the recursion saves its arguments in dimensioned arrays
  indexed by depth.

SIN and COS take degrees. INT truncates toward zero. Explicit two-argument
substring selection and replacement use one-based byte positions (negative
positions count from the end). For single-index replacement,
`S[length] = text` replaces the last `length` bytes and `S[length] := text`
appends within that selection. The reference generator treats the index
as a length. jbcc truncates fractional lengths, clamps oversized lengths
to the full string, and treats a nonpositive length as an empty selection
at the end. [String variables](https://jbc-lang.org/pages/string_variables.html).

The guide defines `@(column,row)` with a
zero-based origin. jbcc returns an ANSI cursor-position string, so
`@(5,2)` emits `ESC[3;6H` when printed. The runtime truncates fractional
coordinates toward zero and reports a negative result at the call site.
The guide’s SCREENCODE table defines `@(-1)` to clear the screen and home
the cursor, `@(-2)` to home the cursor, `@(-3)` to clear from the cursor to
the end of the screen, and `@(-4)` to clear to the end of the current line.
Each returns the sequence TAFC PB201214 writes for `TERM=vt100`
(`tests/tafc/at-minus-codes.b`): `@(-1)` is `ESC[H ESC[J`, `@(-5)`
`ESC[5m` (blink), `@(-13)` `ESC[7m` (reverse), `@(-15)` `ESC[4m`
(underline), `@(-6)`, `@(-8)`, `@(-14)` and `@(-16)` end them, `@(-9)` is a
backspace, `@(-10)` and `@(-19)` move up and right, `@(-17)` and `@(-18)`
turn the printer on and off, and `@(-20)` is a line feed. Other negative
codes are empty, as vt100 defines none. `@(n)` moves to column n of the
current line.
`SYSTEM(14)` counts unread DATA bytes, including line endings. Native
jbcc adds the bytes reported by the POSIX input device to the DATA count
when both sources have pending input. On a terminal, it can count
keystrokes before Enter. Querying the count leaves the bytes available
for later reads. [CLEARDATA](https://jbc-lang.org/pages/cleardata.html).

Native mode links the math library for programs
that use SIN, COS, TAN, ASIN, ACOS, ATAN, PWR, SQRT, EXP, LN, FADD,
FSUB, FMUL, FDIV or FCMP, including infix powers. When compiling their generated C manually, use
`cc -std=c99 banner.c -lm -o banner`. [SIN](https://jbc-lang.org/pages/sin.html),
[COS](https://jbc-lang.org/pages/cos.html), [INT](https://jbc-lang.org/pages/int.html).

## Evidence for the implementation

See [Sources for jbcc](SOURCES.md) for manuals, search filters, local
reference materials, and the scope of the compiler and runtime probes.

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

## License

The project's original code is released under the [MIT License](LICENSE).
The [third-party notices](THIRD-PARTY-NOTICES.md) cover the CP037
mapping data distributed with jbcc.
