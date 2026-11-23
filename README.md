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
parentheses, arithmetic, concatenation, and compound assignments. The reference
lexer accepts spaces and tabs before the equals sign in `+=`, `-=`, `*=`
and `/=`. For example, `R<1> + = 1` increments the first field, a form
used in T24. An assignment target may have whitespace before the opening
angle bracket. Both `T.SEQU <-1> = A+1` and `T.SEQU < - 1 > = A + 1`
append a field. The reference grammar allows one to three indices followed
by an optional substring selector. Reads also allow whitespace, as in `X = R <FIELD>` and
`LOCATE X IN R <FIELD> SETTING POS`. The reference preprocessor pairs
angle brackets within an expression and checks for intervening logical
operators. jbcc keeps a spaced comparison chain such as `A < B > C`
when an operand follows the closing bracket. Before a binary operator,
`R <1> + 3` reads field one and adds three. Use `LT` and `GT` to make
ambiguous comparisons explicit. Concatenating assignment uses the single
token `:=`.
Addition binds more tightly than
concatenation. Names are case-sensitive. Reads require an assigned value. Routines with GOTO, GOSUB or RETURN TO check this at runtime because jumps can bypass assignments. Separate statements with a newline or semicolon. A statement beginning
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

`DIV(dividend, divisor)` returns the fractional quotient with the same
PRECISION rules as `/`. The guide specifies an empty result if either
operand is empty. jbcc applies that rule before numeric validation and
reports a zero divisor at the DIV call for nonempty operands.
[DIV](https://jbc-lang.org/pages/div.html).

`DROUND(value[, places])` rounds decimal values and removes trailing
fractional zeros. It defaults to the active PRECISION, or four places
before a PRECISION statement runs, following the jBASE manual. An
explicit nonnegative integer overrides that default. jbcc provisionally
uses exact decimal rounding with midpoint ties away from zero.
[jBASE DROUND](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_DROUND.htm).

`SMUL(left, right[, places])` multiplies decimal strings exactly before
limiting the output scale, so products can exceed the native integer range.
It ignores the active PRECISION. jbcc provisionally truncates toward zero
and removes trailing fractional zeros. The default is 16 fractional
places, which reproduces the guide's fractional example. The reference
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

ALPHA returns 1 when every byte in a nonempty value is an ASCII letter.
Digits, punctuation and array marks return 0. jbcc provisionally returns
0 for an empty string pending a reference run. The guide describes Unicode
classification separately under International Mode. [ALPHA](https://jbc-lang.org/pages/alpha.html).

NUM tests whether an expression has numeric text and returns 1 or 0.
It follows the guide’s prime-emulation examples. Signed decimals and leading
zeros are accepted, as are the empty string and the single characters
`.`, `+`, and `-`. Spaces, thousands separators, and exponent notation
return 0. [NUM](https://jbc-lang.org/pages/num.html).

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

ABS returns the magnitude of a numeric expression. For example,
`ABS(10 - 15)` returns `5`. jbcc reads decimal strings directly,
preserving their significant digits, and truncates the result when an
explicit PRECISION applies. [ABS](https://jbc-lang.org/pages/abs.html).

`ABSS(array)` applies ABS to each nonempty element and preserves empty
elements and array marks. jbcc provisionally uses the scalar ABS error
behavior for nonnumeric elements, with a diagnostic at the ABSS call.
[ABSS](https://jbc-lang.org/pages/abss.html).

NEG reverses the sign of a numeric expression, including a comparison
result. For example, `NEG(2 LT 3)` returns `-1`. jbcc applies explicit
PRECISION as it does for ABS. For nonnumeric input, NEG writes a warning
to stderr at the call site and returns zero, allowing execution to continue.
[NEGS and NEG](https://jbc-lang.org/pages/negs.html).

`NEGS(array)` applies the same conversion and explicit PRECISION to
each nonempty element. It preserves field, value, and subvalue marks and
keeps empty elements empty, following the jBASE reference prose. A
nonnumeric element becomes zero and produces a warning at the call site.
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

`EXECUTE expression` and `PERFORM expression` run the resulting command
in the native host's default Bourne shell on POSIX. The default streams
are inherited from the parent. The caller waits for the child and continues
even if the command exits with a nonzero status. For example,
`PERFORM './report today'` can invoke another jbcc-built executable.
The native runtime also accepts the explicit `CHAR(255) : 's'` shell
prefix. With `CAPTURING variable` alone, the child’s stdout is collected into
the variable and stderr stays on the caller’s error stream. Each LF,
including a final LF, becomes one field mark. An empty stream assigns
an empty string. `RETURNING variable` and `SETTING variable` put the child’s
exit code in field 1. Either can appear before or after CAPTURING.
For native commands, jbcc provisionally appends nonempty stderr starting
in field 2, replacing each LF with a field mark. With empty stderr the
result is just the status. A signal exit is recorded as 128 plus the
signal number. If both clauses target the same variable, the status
result is assigned last. NUL bytes in either collected stream produce a
runtime diagnostic. Alternate shells and field-mark-separated commands
remain unsupported.
[EXECUTE](https://jbc-lang.org/pages/execute.html).

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

`@PATH` is the current account pathname in the jBASE guide. Native
jbcc provisionally uses the process's absolute working directory as
the account path. A failure to resolve it reports the source location.
[@PATH](https://jbc-lang.org/pages/@path.html).

`@PID` returns the native process ID. `JBCPORTNO` can set the value of
`@USERNO` independently.
[@PID](https://jbc-lang.org/pages/@pid.html).

`@TTY` returns the POSIX device name for the terminal on standard
input, such as `/dev/pts/2`. If standard input has no terminal device
name, jbcc provisionally returns `phantom`, following the check used
by T24's PRO.
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

ICONV accepts compact Gregorian dates in `YYYYMMDD` form with masks `D`
and `D4`. For example, `ICONV('20121231', 'D')` returns `16437`, the
number of days since 31 December 1967. The `MT` and `MTS` input masks
accept `H:MM` and `H:MM:SS` with an optional AM or PM suffix and return
seconds since midnight. Unsupported masks and input formats produce a
diagnostic at the call site. An impossible date also produces
a diagnostic, a provisional choice pending a reference run.
[ICONV](https://jbc-lang.org/pages/iconv.html).

`ICONVS(array, mask)` applies the supported scalar conversions to
each nonempty element and preserves field, value, and subvalue marks.
Value-mark-separated masks run left to right. An empty array yields an
empty string. An invalid element yields an empty result and `STATUS()`
of 1. jbcc returns an empty result with status 2 for unsupported
masks, and reports an empty mask at the call site. A successful
conversion sets status 0.
[ICONVS](https://jbc-lang.org/pages/iconvs.html), [MT conversion](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jql2_CONVERSION.MT.htm).

For dates, the OCONV mask `D` produces `DD MON YYYY`. A digit from 0 through 4 selects the
year width. With a separator (`-`, `/` or `.`), jbcc follows the guide’s
worked example and observed T24 usage. For example, `OCONV(16454,'D4/')` returns
`01/17/2013`. Append `E` for day-first order. The guide’s syntax table
instead describes day-first order for the plain numeric form. Component
masks include `DD`, `DM`, `DMA`, `DJ`, `DQ`, `DW`, `DWA`, and `DY` with
optional year width. The runtime accepts Gregorian years 1 through 9999
and reports unsupported masks at the call site. [DATE](https://jbc-lang.org/pages/date.html),
[OCONV](https://jbc-lang.org/pages/oconv.html).

`OCONVS(array, mask)` applies the supported output masks to nonempty
elements, preserving field, value, and subvalue marks. Value-mark-separated
masks run left to right. If any stage fails for an element, jbcc returns
that element's original text and sets `STATUS()` to 1 while converting
the remaining elements. A successful call sets status 0. An unsupported
mask yields an empty result with status 2, and an empty mask produces a
diagnostic at the call site.
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
SUMMATION add decimal digits directly. Each addition rounds to at most
15 fractional places by default or truncates to an explicit PRECISION.
Integer additions retain the signed 64-bit overflow check. [SUM](https://jbc-lang.org/pages/sum.html).

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

`INPUTCLEAR` and `CLEARINPUT` clear terminal type-ahead. Queued DATA
and nonterminal stdin stay available for subsequent reads.
[INPUTCLEAR](https://jbc-lang.org/pages/inputclear.html).

`INPUT Var` writes the current prompt and reads a line from standard input.
`PROMPT expression` sets the prompt for subsequent reads. The default is
`?`, and `PROMPT ''` suppresses it. On a terminal, `INPUT Var:` keeps
typed characters visible and suppresses the echoed newline. With piped
input, the program writes the prompt and reads through the next LF.
`INPUT Var, n` reads up to `n` bytes. Enter ends the read early. At
the limit, INPUT returns immediately and leaves subsequent bytes,
including any following LF, for the next read. With terminal echo enabled,
reaching the limit echoes a newline unless the statement ends in a colon.
Provisionally, jbcc truncates fractional lengths toward zero. A zero
length consumes no input, and a negative integer length raises an error.

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
`@SENTENCE[' ',2,1]` gives `today`. The guide documents a space-separated
invocation for the related `SENTENCE` function. For native executables,
jbcc provisionally uses the exact program name supplied in `argv[0]` and
joins all arguments with one space. Embedded spaces and empty arguments
are preserved, and shell quoting is already removed by the time the
program starts. [SENTENCE](https://jbc-lang.org/pages/sentence.html).

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

`MATCHFIELD(text, pattern, field)` returns the part of a whole-string
match consumed by the numbered pattern component, starting at 1.
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
bare mask names through known variables and matrix elements. Clause
keywords remain delimiters in this position. Use explicit FMT when a
mask variable shares a clause keyword.

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

Width-prefixed `T` masks such as `35T` wrap at spaces when possible.
They split overlong words, pad each block on the right, and insert
a text mark between blocks. jbcc provisionally uses the same
byte widths and edge-space trimming as FOLD.

`FMTS(array, mask)` applies the supported FMT masks to each field,
value and subvalue, preserving delimiters and empty elements. An empty
array gives an empty result with a valid mask. An empty or unsupported
mask reports a source-located formatting error.
[jBASE FMTS](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_FMTS.htm).

CRT writes to standard output. PRINT uses the current output device, initially
standard output. Commas separate items with tabs.
A final colon suppresses the newline. A bare PRINT or CRT emits a newline.

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

FOR supports inclusive bounds, a default step of one, optional STEP,
and an optional variable name after NEXT. Following the reference parser,
jbcc warns if that name differs from the innermost FOR counter. The NEXT
still increments the counter from that FOR header. The limit and step are evaluated
at the start of each iteration. The captured step increments the counter
after the body. FOR accepts WHILE and UNTIL guards in its header.
The reference grammar also allows guards between statements in FOR and
LOOP bodies, with an optional DO after the condition. An inline arm can
end at a loop guard. In `LOOP READNEXT ID ELSE ID = "" WHILE ID <> ""`,
the guard tests the ID after READNEXT and its ELSE arm have run. An ELSE
inside a nested conditional still binds to the nearest eligible THEN.
T24 uses
`UNTIL found` immediately before `NEXT`. When the body reaches that
guard and `found` is true, the FOR exits with its counter at the current
value. CONTINUE skips the rest of the innermost iteration.
In FOR it advances the counter by the captured step. In LOOP it resumes
at the top, even when a guard appears later in the body. Outside a loop
it issues a compile-time warning and execution proceeds normally.
[CONTINUE](https://jbc-lang.org/pages/continue.html). See the [FOR](https://jbc-lang.org/pages/for.html) and
[LOOP](https://jbc-lang.org/pages/loop.html) chapters.

Bare `BREAK` and `EXIT` leave the innermost FOR or LOOP, including from
inside a CASE arm. A FOR counter keeps its current value. Outside a loop
the compiler warns at the statement and execution continues.
[BREAK](https://jbc-lang.org/pages/break.html).

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
internal delimiters. SETTING is optional and counts input fields placed in
the selected one-based slots, including empty fields between or after
delimiters. jbcc clears unused slots inside the range and treats empty
input as zero fields. An empty delimiter treats nonempty input as one
field. These edge cases are provisional pending a reference run.
[MATPARSE](https://jbc-lang.org/pages/matparse.html).

`INMAT(A)` reports the bounds of dimensioned array `A`, using one value
mark between dimensions, as in the guide's two-dimensional example.
For instance, after `DIM A(2,4)`, it returns `2:@VM:4`. This also works
with a matrix passed by reference.

`INMAT()` returns the element count from the most recent MATREAD, MATREADU,
or MATPARSE in the process. It returns zero initially and when the input
exceeds the available slots. For a ranged MATPARSE, jbcc uses the selected
range to determine overflow. A failed or locked MATREAD also sets the
count to zero in jbcc. SETTING continues to report the count specified by the individual
statement. [INMAT](https://jbc-lang.org/pages/inmat.html).

COM and COMMON accept scalars and dimensioned arrays. Declarations of the
same named or unnamed block share slots by position across routines in one
program. Repeating a scalar or a matrix in the same block within a
compilation unit reuses its original slot, including when an include is
expanded twice. This follows the reference parser’s `common_identifier`
allocation rule and its dynamic-dimension generator. Repeated matrix
declarations must agree on rank and bounds. jbcc checks constant bounds
at compile time and expression bounds when the declaration executes.
The compiler also checks member count, rank, and known bounds across
input files. For T24 declarations such as
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
  of GOTO, including in indexed ON statements. GOTO can jump within or leave a FOR. A jump that
  would enter a FOR without executing its header gets a source diagnostic.
  GOSUB starts a fresh control-flow invocation and shares
  the routine's variables and supports nested returns. Execution falls through
  labels encountered sequentially. STOP terminates the program. [GOSUB](https://jbc-lang.org/pages/gosub.html)
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
  A static subroutine name can start with `!`, as in the T24 call
  `CALL !HUSHIT(1)`. The prefix is part of the name when matching a CALL
  to a SUB or SUBROUTINE definition, following the reference compiler’s
  direct call-name reader. In `CALL @Name(args)`, the value of Name selects
  a subroutine supplied to jbcc. Lookup is case-sensitive. The target's
  parameter count and scalar or MAT parameters are checked at runtime.
  For example, `Name = 'GET.STATUS'; CALL @Name(Rec, Answer)` can update
  Answer just like a direct call.
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
- EQU or EQUATE defines token substitutions, including comma-separated
  definitions. T24 also uses definitions between semicolon-separated
  statements. Each definition applies from that point onward, including
  later statements on the same line. $INSERT and INCLUDE search the
  including file's directory, followed by each `-I DIR` in order. Included
  tokens retain their source locations. [EQUATE](https://jbc-lang.org/pages/equate.html)
- BEGIN CASE evaluates conditions in order, executes the first true arm,
  and resumes after END CASE. Use CASE 1 for a default. The reference
  grammar allows zero arms. When the block is empty or contains only
  comments, execution continues with the statement after END CASE. [CASE](https://jbc-lang.org/pages/case.html)

## Built-in functions

CHAR returns a single byte for integer codes 1 through 255. CHAR(0)
reports a runtime diagnostic while strings use NUL termination.

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
lengths, truncating fractional values toward zero. In an expression,
`Text[n]` is equivalent to `RIGHT(Text, n)`. For example,
`Record<2>[3]` reads the last three bytes of the second field.
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

`BYTELEN(value)` counts bytes, including each field, value and subvalue
mark. For example, `BYTELEN('é')` is 2 for a UTF-8 literal. It uses the
same byte-count operation as LEN in the current runtime.
[BYTELEN](https://jbc-lang.org/pages/bytelen.html).

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
A direct `REUSE(scalar)` in either argument repeats it at every position.
[EQS](https://jbc-lang.org/pages/eqs.html), [NES](https://jbc-lang.org/pages/nes.html).

`ADDS(left, right)` adds corresponding fields, values and subvalues
using the same arithmetic and PRECISION as `+`. It copies an unmatched
element unchanged and leaves a paired position empty if either element
is empty. jbcc provisionally treats a wholly empty operand as one empty
element. A direct `REUSE(scalar)` in either argument repeats that scalar
at every position and evaluates it once. [ADDS](https://jbc-lang.org/pages/adds.html).

`SUBS(left, right)` subtracts corresponding fields, values and subvalues.
Empty or missing elements count as zero, including a wholly empty
operand. Nonnumeric elements cause an error at the call site. SUBS uses
the scalar subtraction rules for PRECISION and overflow and accepts
direct `REUSE(scalar)` in either operand. [SUBS](https://jbc-lang.org/pages/subs.html).

`MULS(left, right)` multiplies corresponding fields, values and
subvalues. An unmatched element gives zero. An empty element in a pair
gives an empty result. MULS uses the same array alignment and scalar
`REUSE` as ADDS, including the provisional treatment of a wholly empty
operand as one empty element. Products follow the PRECISION and overflow
rules of scalar multiplication. [MULS](https://jbc-lang.org/pages/muls.html).

`array * REUSE(scalar)` and `REUSE(scalar) * array` use the same
element-wise multiplication as MULS. jbcc accepts REUSE as a direct
operand and evaluates the wrapped scalar once. This follows the
infix form seen in T24's LI.SECURED.ONLINE.
[MULS](https://jbc-lang.org/pages/muls.html).

`DIVS(left, right)` divides corresponding fields, values and subvalues
with the same PRECISION rules as scalar division. A missing divisor
preserves the dividend and a missing dividend gives zero. An empty
element in a pair gives an empty result. A wholly empty operand
provisionally counts as one empty element. For a numeric pair with a
zero divisor, jbcc warns at the call site, emits zero for that position,
and continues. Direct `REUSE(scalar)` works on either side.
[DIVS](https://jbc-lang.org/pages/divs.html).

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

## Sequential files

`OPENSEQ path TO F` and `OPENSEQ directory, name TO F` open regular files
on the native filesystem. Relative paths use the executable’s working
directory. `READONLY` takes a shared advisory lock. A writable open takes
an exclusive lock. Contention takes `LOCKED` when supplied, otherwise
`ELSE`. Pipes and devices currently take the I/O error branch.
[OPENSEQ](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_OPENSEQ.htm).

A missing file takes `ELSE` and leaves a pending handle. `CREATE F THEN … ELSE …`
creates and opens an empty file through that handle. If another handle
created the file first, CREATE takes ELSE and preserves the existing
contents. Passing an empty value to CREATE gives a source-located error.
The first `WRITESEQ` can also create the file. `OPENSEQ EXISTING` and
`READONLY` disable deferred creation. [CREATE](https://jbc-lang.org/pages/create.html).

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
returns an empty value with status 0. NUL bytes become byte 128.
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
record context variable. It keeps internal line endings, strips one final
LF, and replaces each NUL byte with byte 128. A bare name that is missing
from the working directory is searched for in the colon-separated
`JEDIFILEPATH`. The reference grammar accepts `SETTING` and `ON ERROR`
with a required THEN or ELSE arm. jbcc uses sequential file status codes
and clears the destination on failure. A missing file takes ELSE with
status 128. Other I/O errors take ON ERROR when present or report the
statement location.
[OSREAD](https://jbc-lang.org/pages/osread.html).

`TIMEOUT F, seconds` accepts an open sequential handle and nonnegative
decimal seconds. A pending or closed handle and an invalid duration
report an error at the statement. The regular-file backend completes
READSEQ and READBLK with available bytes or EOF, so the requested
timeout requires no timer there. EOF still yields status 128.
[TIMEOUT](https://jbc-lang.org/pages/timeout.html).

`READBLK Block FROM F, Size` reads a positive number of bytes at the
current position, including line endings and field marks. A complete
block takes THEN. Following the guide's EOF rule, jbcc provisionally
takes ELSE with an empty destination on a short read, and the position
advances past any bytes consumed. Embedded NUL bytes take ELSE with
status 32768 because jbcc values use NUL-terminated strings.

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
Embedded NUL bytes produce an I/O error.
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
OPEN and READ require THEN or ELSE. WRITE accepts SETTING and ON ERROR
as well as its existing THEN and ELSE forms. In the in-memory backend,
a failed OPEN or READ clears its destination. WRITE sets its optional
status to 128 for an invalid descriptor or 32768 for a simulated foreign
lock. On success it releases an owned update lock and sets the status to
the empty string, the same provisional success status as WRITEU.
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

With an explicit string or dynamic array, SELECT makes a list of its fields
in source order. Value and subvalue marks stay inside their fields. Leading,
interior and trailing empty fields are entries. jbcc treats a completely
empty source as an empty list. Reassigning the source leaves the selected
fields available to READNEXT. A standalone `//` line, as used in the
guide’s CLEARSELECT example, is accepted as a separator. [SELECT](https://jbc-lang.org/pages/select.html),
[READNEXT](https://jbc-lang.org/pages/readnext.html).

`FORMLIST Keys TO L` starts a fresh cursor over the field-mark-separated
entries in `Keys`. Omitting `TO` selects the default list. A number from
0 through 10 selects a numbered list. The reference grammar also accepts
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

`REMOVE(record, mark)` returns the next delimited string as an expression
and assigns the same delimiter code. jbcc uses the same cursor for both
forms on a bare variable or matrix element. An exhausted function call
returns an empty string and code 0. Following the reference grammar,
the first argument may also be a computed value. jbcc treats that value
as a fresh array for the call.

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
For direct external calls it declares the observed signature so that the system C
compiler can check the complete generated unit with C99 warnings as errors.
For indirect calls and exit callbacks it checks the dispatch code using the
current unit. Native tests exercise lookup across multiple linked units.
Additional include directories can be supplied with `-I`.

The JSON report records a status per relative path, diagnostic locations,
and counts by first blocker. A translated unit passed C syntax checking.
Linking its external dependencies and verifying its behavior require separate
tests. UTF-8 decoding failures are counted separately.

## Test corpus

```sh
python3 -B -m unittest discover -s tests -v
```

With uv installed, the same suite can run in parallel.

```sh
uvx --with pytest-xdist pytest -n auto
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
positions count from the end). The guide defines `@(column,row)` with a
zero-based origin. jbcc returns an ANSI cursor-position string, so
`@(5,2)` emits `ESC[3;6H` when printed. The runtime truncates fractional
coordinates toward zero and reports a negative result at the call site.
The guide’s SCREENCODE table defines `@(-1)` to clear the screen and home
the cursor, `@(-2)` to home the cursor, `@(-3)` to clear from the cursor to
the end of the screen, and `@(-4)` to clear to the end of the current line.
Each returns an ANSI sequence that takes effect when printed.
`SYSTEM(14)` counts unread DATA bytes, including line endings. Native
jbcc adds the bytes reported by the POSIX input device to the DATA count
when both sources have pending input. Querying the count leaves the
bytes available for later reads. [CLEARDATA](https://jbc-lang.org/pages/cleardata.html).

Native mode links the math library for programs
that use SIN, COS, PWR, SQRT, EXP or LN, including infix powers. When compiling their generated C manually, use
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
