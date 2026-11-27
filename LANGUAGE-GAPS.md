# Language gaps

What jbcc does not do yet, or does only provisionally. Each item names
where it shows up. The README describes what is implemented.

## Not implemented

- `MCPN` and `MCNP` conversions: the guide's description of the hex
  escaping is too vague to implement safely; they report an unsupported
  mask.
- `STATUS()` after a conversion with an invalid mask: jBASE sets
  `STATUS()` and goes on, as the guide's STATUS example shows; jbcc stops
  with an unsupported-mask error.
- `TIMEDIFF` masks 2 to 7 (months and years): the guide does not say from
  which calendar date months count; they report an error when reached.
- Fractional day counts in date masks: some R19 code passes
  `(seconds - now)/86400 + 732` to `OCONV(..., "DG")`; jbcc reports an
  error when reached, where jBASE probably truncates.
- A pattern mask with a decimal precision, such as `R2(##.##)`: the guide
  never combines them; jbcc reports an unsupported mask.

## Needs a backend jbcc does not have

These parse and compile, and report the missing backend when reached.

- XML: `DYNTOXML`, `DYNTOXMLEXT`, `XMLTODYN`, `XMLTOXML`, `READXML` and
  `READXMLU`.
- Calendar conversion: `DATELOCALETOGREGORIAN` and
  `DATEGREGORIANTOLOCALE`.
- `ENCRYPT` and `DECRYPT` methods other than ROT13.
- Licensing, snapshots, the debugger and C functions declared with
  `DEFC`: `VALIDATE_PRODUCT_LICENSE`, `JBASECOREDUMP`, `DEBUG`, and `DEFC`
  calls other than the `JBC.h` cache functions.
- Named time zones in the playground: its WASI runtime has no zone
  database, so only an empty zone, `UTC` and `GMT` work there.

## Provisional, waiting for evidence

Each is documented in the README as a guess.

- `@TIMEZONE` reads `JBASE_TIMEZONE`, then `TZ`.
- `@COMPANYNO` starts empty.
- `UNASSIGNED` of an R19 component call counts its result as assigned.
- `BITNOT` returns an unsigned result.
- A COMMON member that a routine `DIM`s shares its elements between units
  that dimension it; a scalar use elsewhere keeps a separate value.
- `TIMEDIFF` gives each field the sign of the difference.
- `MCP` turns every byte outside ASCII 32 to 126 into `.`, other than the
  three system marks; the guide's example shows it only for the text mark.

## T24 corpora: outside translation

All four corpora translate; see R13-CORPUS.md and R19-CORPUS.md.

- Package-aware linkage: each R19 unit is checked on its own, with
  prototypes for the members it calls.
- T24 table operations at runtime: their calls are checked, not run.
- The `.tut` unit tests with their `.d` records.
- 6 R19 units include generated inserts whose `.domain` class is not in
  the dump (`--t24-exclude-missing-domains`).
