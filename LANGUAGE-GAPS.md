# Language gaps

What jbcc does not do yet, or does only provisionally. Each item names
where it shows up. The README describes what is implemented.

## Needs a backend jbcc does not have

These parse and compile, and report the missing backend when reached.
MISSING-BACKENDS.md lists them in full, with how often T24 uses each.

- XML: `DYNTOXML`, `DYNTOXMLEXT`, `XMLTODYN`, `XMLTOXML`, `READXML` and
  `READXMLU`.
- Calendar conversion: `DATELOCALETOGREGORIAN` and
  `DATEGREGORIANTOLOCALE`.
- `ENCRYPT` and `DECRYPT` methods other than ROT13, XOR11 and BASE64.
- Licensing, snapshots, the debugger and C functions declared with
  `DEFC`: `VALIDATE_PRODUCT_LICENSE`, `JBASECOREDUMP`, `DEBUG`, and `DEFC`
  calls other than the `JBC.h` cache functions.
- Named time zones in the playground: its WASI runtime has no zone
  database, so only an empty zone, `UTC` and `GMT` work there.

## Provisional, waiting for evidence

Each is documented in the README as a guess.

- `@COMPANYNO` starts empty.
- `UNASSIGNED` of an R19 component call counts its result as assigned.
- A COMMON member that a routine `DIM`s shares its elements between units
  that dimension it; a scalar use elsewhere keeps a separate value.

## Differences from TAFC PB201214 kept on purpose

See TAFC-CROSSCHECK.md for the probes.

- A numeric literal under a later, lower PRECISION: TAFC keeps it at the
  unit's first PRECISION and rescales it without rounding; jbcc rounds it
  at the PRECISION in force.
- FIELD and GROUP with a multi-byte delimiter and a count above one: TAFC's
  results follow no consistent rule; jbcc matches the whole delimiter.
- `REUSE` of a power, as in `A * REUSE(2 ^ 3)`, does not broadcast in TAFC;
  jbcc broadcasts it like any other scalar.
- TAFC prints the result of a division by zero as `0.0nan` or `0.0inf` for
  some divisor types; jbcc gives 0.
- Spaced comparison chains: TAFC reads `2 < 3 > 0` as the extraction
  `2<3>` with an implicit format and prints 0; jbcc compares
  (`tests/tafc/comparison-chains.b`).
- Before 1970: TAFC drops fractional seconds in MAKETIMESTAMP and
  truncates negative timestamps toward zero, so `LOCALDATE(-1)` is
  1 January 1970; jbcc gives 31 December 1967 + 731 days as the calendar
  says. Dates past 2038 overflow in TAFC's CHANGETIMESTAMP; jbcc's do not.
- Year 10000 and up: TAFC prints `OCONV(2933629, 'D')` as `01 JAN 0000`;
  jbcc reports a range error. `ICONV('2023103', 'DG')` is 32767 in TAFC;
  jbcc reads YYYYDDD.
- `@TTY` without a terminal: TAFC gives `''` for a plain run; jbcc gives
  `phantom`, which T24 tests for a background job (`tests/tafc/at-tty.b`).
- A date code that takes the rest of a chain, followed by other codes, as
  in `OCONV(19024, 'D':@VM:'MCL')`: TAFC gives `1`, reading the codes as
  date options; jbcc gives the value back.
- `STATUS()` read in the same statement as a conversion, as in
  `CRT OCONV(X, 'D'), STATUS()`: TAFC appears to read it before the
  conversion runs; jbcc reads it after.
- EXECUTE without a shell: TAFC runs `echo a; echo b` as `echo` with the
  arguments `a;`, `echo` and `b`, taking `;`, `|` and quotes literally;
  jbcc runs the command with `/bin/sh -c` (`tests/tafc/execute-capturing.b`).
- Byte 0: INPUT and KEYIN report it as an error. TAFC's OSBWRITE of byte 0
  writes extra bytes; jbcc writes the bytes given. TAFC itself mishandles it in three places, which jbcc does not copy:
  LOCATE finds no value that holds byte 0, SORT scrambles such values, and
  CONVERT to byte 0 gives `''` (`tests/snippets/nul-locate-sort.b`).

## T24 corpora: outside translation

All four corpora translate; see R13-CORPUS.md and R19-CORPUS.md.

- Package-aware linkage: each R19 unit is checked on its own, with
  prototypes for the members it calls.
- T24 table operations at runtime: their calls are checked, not run.
- The `.tut` unit tests with their `.d` records.
- 6 R19 units include generated inserts whose `.domain` class is not in
  the dump (`--t24-exclude-missing-domains`).
