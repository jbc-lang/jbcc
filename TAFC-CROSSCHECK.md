# TAFC cross-check plan

This plan comes from running the guide's code blocks and targeted probes
through jbcc 0.7.0 (`dc0e07e`) and through the reference runtime, TAFC
PB201214 (change level 106034), under `JBCEMULATE=prime`. It lists what
the reference run showed and the work that follows from it. Tick an item
when it lands, and record the probe that supports each rule in the test
that checks it ("observed reference run", as AGENTS.md asks).

The 2026-11-27 round classified the 1006 unique guide code blocks as
follows: 216 same output, 84 different output, 114 rejected only by jbcc,
47 failing at run time only in jbcc, and 545 not compilable by TAFC
(syntax templates, fragments, subroutines).

## Reference runtime

- Tarball: `../jbc-internals/TAFC_PB201214_LINUX_ELF_AS6_106034-unbound.tar.gz`,
  which runs without the licensed-user limit.
- Docker: `../jbc-internals/docker/` holds the `Dockerfile` and the
  `tafc-docker-run.sh` runner (image `jbc-internals-tafc-runner:local`;
  debian bookworm, gcc, libncurses5, CentOS 7 `libcrypto.so.10`). It runs
  one `program.b` per container, and its README explains how to rebuild
  the image. Rebuild it with:

  ```sh
  docker build --platform linux/amd64 --tag jbc-internals-tafc-runner:local ../jbc-internals/docker
  ```

- The batch cross-check needs more than that runner gives:
  - `JBC.h`: compile with `jcompile -I$JBCRELEASEDIR/include prog.b`.
    `jcompile` accepts a `.b` file directly.
  - jBASE files (`CREATE-FILE`, `COUNT`, `LIST`): `libTAFCjcf.so` needs
    `libssl.so.10`, but only for remote sockets. A stub library is
    enough. Build it inside the container:

    ```sh
    printf 'void abort(void);\nint SSL_get_error(void){abort();return 0;}\nint SSL_clear(void){abort();return 0;}\nint SSL_shutdown(void){abort();return 0;}\n' > ssl.c
    cc -shared -fPIC -Wl,-soname,libssl.so.10 -o /compat/libssl.so.10 ssl.c
    ```

    Then add `/compat` to `LD_LIBRARY_PATH` and set `JEDIFILEPATH` to the
    program's own working directory.
  - EXECUTE of shell commands calls `/bin/ksh`: `ln -s /bin/bash /bin/ksh`.
  - Set `TERM=vt100` (`@(-n)` and `SYSTEM(7)` depend on it) and use
    stdin `/dev/null` unless a probe needs input. `IN` reads stdin, not
    the DATA stack.
  - Run at most two TAFC programs in parallel per container. More than
    that sometimes fails with "Unable to Create Licensing semaphore" or
    "shared memory revision" errors.
  - `EMU=jbase` (set `JBCEMULATE=jbase`) separates emulation-dependent
    results from real differences.
- TAFC prints runtime warnings (`Divide by zero !!`,
  `Invalid or uninitialised variable -- NULL USED`,
  `Non-numeric value -- ZERO USED`) on stdout with a `Line n , Source X`
  line, and then continues.

## 0. Harness in the repository

- [x] `tools/tafc_crosscheck/container.sh` runs inside the
      jbc-internals image. It unpacks the tarball once, adds the stub
      `libssl`, `ksh` and the include path, gives each program its own
      `JEDIFILEPATH`, and retries a program that fails during jBASE
      start-up. `tools/tafc_crosscheck/crosscheck.py` mounts the probes
      and the tarball, builds the image if it is missing, and builds the
      same probes with `jbcc --exe`.
- [x] The comparer writes `report.json` and `report.txt` under
      `.cache/tafc/`. It ignores CR, trailing spaces and blank edge
      lines, and marks a difference as volatile when the source reads
      the clock, the process or random numbers.
- [x] `just tafc-guide` extracts the guide blocks with
      `../jbc-language/check_examples.py` (building the site under
      `.cache`), runs both compilers and classifies the results.
- [x] `just tafc-probe [--record] PATHS` runs probes side by side and
      can save TAFC's stdout.
- [x] `tests/tafc/` has 34 probes with `NAME.tafc.stdout`, one or more
      for each item below. Each probe names its emulation and plan
      section. `just tafc-recorded` compares jbcc with them without
      Docker. A probe runs under its file name, as TAFC's warnings show
      it. These probes are not part of `just test`: move each one, or
      its assertions, into `tests/snippets/` when jbcc matches it.

## Emulation

`JBCEMULATE` selects a bundle of switches from
`$JBCRELEASEDIR/config/Config_EMULATE`; `Config_EMULATE.txt` describes
them. `prime` starts from `jbase` and changes about 40 switches. T24
runs under prime. The description file says that switches apply at
compile time unless marked `[Runtime]`. Compiling a probe under one
emulation and running it under the other showed:

| Feature | Decided by |
|---|---|
| `CONVERT(a, b, c)` argument order | compile emulation |
| `LOCATE x IN A<f>`, fields or values (`use_uv_locate`, not marked `[Runtime]`) | run emulation |
| MATCH patterns (`ext_pattern_match`) | run emulation |
| `COUNT` of overlapping matches | run emulation |
| Default `PRECISION 4` and truncation | neither |

Other `[Runtime]` switches in prime include `named_common = zero`,
`unnamed_common = zero`, `allow_unassigned_assignment`,
`multiple_cmd_execution`, `skip_spaces_and_tabs` and
`iconv_nonnumeric_return_null`.

Decision (2026-11-27): jbcc fixes the emulation when it translates. The
default is prime, and an `--emulation` option selects another bundle.
The generated program does not read `JBCEMULATE`. Each switch is
decided in one place, whether TAFC applies it at compile time or at
run time.

## 1. Prime emulation: CONVERT, LOCATE, MATCH

jbcc follows jBASE emulation for these three, but T24 runs under prime.
TAFC gives different results in the two emulations.

- [x] Add `--emulation {prime,jbase}` (default prime), and make it
      reachable from the browser translator as well. Keep a list of the
      switches each emulation sets, named as in `Config_EMULATE`.

- [x] `CONVERT(from, to, text)`: under prime the function form takes the
      text **last**, so `CONVERT('ab', 'xy', 'aabbc')` returns `xxyyc`.
      All 214 calls in R13 and R19 use this order, for example
      `CONVERT(VM,SM,R.NEW(..))`. The statement form
      `CONVERT a TO b IN x` is the same in both emulations. A repeated
      source byte uses its first mapping (already right).
- [x] `LOCATE x IN A<f>` with one coordinate searches **fields**
      starting at field f. `LOCATE x IN A<f,v>` searches values of field
      f starting at v. The corpus has about 6,300 (R13) and 7,800 (R19)
      one-coordinate forms. Check the result position and the THEN/ELSE
      branch.
- [x] The `BY` orders in prime, observed by inserting at the returned
      position:
  - `AL`: byte order.
  - `AR` and `AN`: numeric order when both values are numeric. Otherwise
    `AR` compares right-justified (`b2` before `b10`) and `AN` compares
    bytes (`b10` before `b2`).
  - `DL`, `DR` and `DN`: the same orders reversed.
  - An empty value sorts first.
- [x] Support the `LOCATE(x, A{, f{, v}}; pos{; order})` function form,
      which TAFC accepts.
- [x] MATCH patterns under prime: `"JOHN..."` and `"'JOHN'..."` give 1,
      `"5C"` gives 0 (`C` is not a code), and `"...'17A'..."` gives 1
      for a quoted literal. Recheck the guide's MATCHES block against
      prime.
- [x] Document the emulation and the option in the README.
- [ ] Move the existing prime-based rules (NUM, COUNT, MATPARSE) behind
      the emulation, after probing them under jbase.

Found while doing this section:

- Prime LOCATE: the last coordinate is the start at the level below the
  others (`<f,v,s>` searches subvalues of value v from s). A separate
  `, start` applies only without coordinates. Both emulations drop
  trailing zero coordinates (`<2,0>` is `<2>`), and a miss with a start
  past the end returns the start. The function form takes the same
  coordinates. Probes: `tests/tafc/locate-forms-*.b`.
- `AR`/`DR` under prime: numbers numerically, two non-numbers
  right-justified, a mixed pair byte by byte. jbase right-justifies
  every pair.
- MATCH: prime has `...`, lower-case codes, `n-m` ranges and no `C`;
  jbase has `C`, upper case only and no ranges or `...`. MATCHFIELD uses
  the prime codes under both emulations. Under jbase, TAFC once applied
  prime rules to a MATCHES after several MATCHFIELD calls, and the same
  MATCHES after a single MATCHFIELD call did not; this was not followed
  up. Probes: `tests/tafc/match-codes-*.b`.
- Existing tests used the jbase CONVERT order. 91 calls in 32 test
  sources were rewritten to prime order; `locate`, `matches` and
  `spaced-array-read` expectations now follow TAFC prime.
- New, for section 4: `CRT 2 < 3 > 0, 2 < 3 >= 0` prints `0 0` in TAFC
  and `1 1` in jbcc (`tests/snippets/spaced-array-read.b`, line 8, with
  `OUT` renamed, because TAFC reserves it).

## 2. Numeric model at PRECISION

TAFC uses fixed-point decimal arithmetic. Probes: `10/3`, `COS(1)`,
`0.00004+0.00004`, `0.5555*0.5555`, `X=2/3; X*3`, `'0.33333'='0.3333'`.

- [x] The default PRECISION is 4: `10/3` gives `3.3333`, `COS(1)` gives
      `0.9998`, `SQRT(2)` gives `1.4142`.
- [x] Round each operand half-up in decimal to PRECISION places before
      arithmetic, not in binary: `0.06245*1` gives `0.0625`,
      `0.00004+0.00004` gives `0`, `-0.00005+0` gives `-0.0001`,
      `1-0.99999` gives `0`.
- [x] Truncate the results of `*`, `/` and the scientific functions to
      PRECISION: `2/3` gives `0.6666`, `0.5555*0.5555` gives `0.3085`,
      `0.0005*0.5` gives `0.0002`, and `1/3*1000000` gives `333300`.
      The truncated text is the stored value: `X=2/3; X*3` gives
      `1.9998`.
- [x] Comparisons and truth tests use the rounded values:
      `'0.33333' = '0.3333'` is 1, `IF '0.00004'` is false and
      `'1.00005' > 1` is 1.
- [x] `INT` does not round its operand (`INT(0.99999)` is 0).
      `ABS(-0.00005)` gives `0.0001`.
- [x] Integers have unlimited size: `99999999999999999999+1` and
      `1234567890123456789*10` are exact, with no overflow error.
- [x] `PRECISION` is set at compile time by position in the source. The
      first `PRECISION` statement also covers the code before it, even
      inside `IF 0 THEN`. A later one applies from its line onwards, and
      a GOSUB body uses the precision in force where it is written.
- [ ] `SADD`, `SSUB` and `SMUL` keep 14 fractional places:
      `SADD(4.33333333333333333,1.8)` gives `6.13333333333333`, and
      `SMUL(0.0000000000000475,3.61)` gives `0.00000000000017`. Check
      against jbcc's current 16 places for SMUL.
- [x] Update the README's arithmetic section and the PRECISION, DIV,
      DROUND, EXP, LN, SQRT and PWR paragraphs, and recheck
      `tests/snippets` outputs that relied on 15 places.

### TAFC's number model (disassembly of libTAFCfrmwrk.so)

From the `../jbc-internals/asm` disassembly, checked with probes. P is
the precision in force.

- PRECISION: the first `PRECISION` statement in a unit emits no code. It
  becomes the unit's static default (`JBASE_DEFAULT_PRECISION`,
  `PRECMULT`). Later ones compile to `SET_PRECISION_VI(n)`. Each CALLed
  unit runs at its own default (4 without PRECISION), and the caller's
  precision is restored on return (observed with BASIC/CATALOG).
- VAR forms: int64, a double holding the value × 10^P with its own
  precision byte, a string, or a BIGINT (decimal digits and a scale).
  Values with more than 15 integer digits, or with a scaled magnitude of
  2^51 or more, use BIGINT math.
- String to number (`JRunDGetNumeric`):
  - Under prime, leading and trailing spaces and tabs are skipped.
  - The syntax is an optional sign, digits, an optional point and
    digits. There is no exponent, and anything else warns
    `Non-numeric value -- ZERO USED` and uses 0.
  - `''`, `'-'`, `'.'`, `'.5'`, `'5.'` and `'+5'` are numeric.
  - Digits beyond P round half-up on the magnitude, so away from zero.
- `+` and `-` are exact on the rounded operands. `*` and `/` truncate
  the exact result toward zero to P. Int op int is exact (overflow moves
  to BIGINT), and int/int at P 0 is C integer division.
- Math functions (COS, SQRT, EXP, LN, PWR and the rest) compute in double
  and round the result half away from zero to P (`JRunDRoundValue`), so
  `EXP(1)` is 2.7183 while `2/3` is 0.6666. Trig functions use degrees.
  `SQRT(x<=0)` is 0.
- Number to string: strip trailing zeros, no `-0`, `0.` before a
  fraction, BIGINT with all its digits. NaN and Inf print as `0.0nan` and
  `0.0inf`, which is the division-by-zero quirk in section 3.
- Comparison (`JLibDCOMPARE_IBBI`): when both sides are numeric,
  compare at P after rounding, so `'0.33333' = '0.3333'` and `' 1' = 1`.
  A side that is non-numeric, or a string that parses to 0 without
  containing a `0` (`''`, `'-'`), compares as a string. BIGINT values
  compare exactly.
- Not modelled: mixed precision. A double computed at one precision and
  used at another is rescaled without rounding, and formatting a value
  turns it back into a string that is parsed again later.

Done for section 2 (2026-11-27), with the tests re-baselined against TAFC:

- Exact decimal arithmetic in the runtime (`struct exact`): operand
  rounding, `+`/`-` exact, `*`/`/` truncated, no integer overflow.
  `limit_places` now rounds, so comparisons, truth tests, ABS, NEG, MOD and
  SUM round at P too.
- The first PRECISION in a unit is its default; each unit sets its own
  precision on entry (4 without PRECISION) and restores the caller's.
- Math functions round at P (`format_decimal`). FADD, FSUB, FMUL and FDIV
  print ten significant digits, as TAFC's raw doubles do. DROUND without
  places uses 4.
- Not modelled: mixed precision (a literal under a lower later PRECISION,
  `tests/snippets/precision.b`), and whether TIMESTAMP rounds or
  truncates (jbcc rounds, unverified).
- Also done here: under prime, ADDS, SUBS, MULS, DIVS, ABSS and NEGS
  count empty and missing elements as 0, and warn and continue for a
  nonnumeric element or a zero divisor (part of section 3). REUSE of a
  dynamic array has no effect (TAFC), in arithmetic, EQS, LES and SPLICE.
  Prime truth tests ignore blanks (`NOT(' ')` is 1).

## 3. Errors that continue

- [x] Division by zero (`/`, `DIV`, and each element of `DIVS`) prints
      the warning, gives 0 and continues. TAFC prints the result of `/`
      as `0.0nan` when the divisor is an integer variable, and as
      `0.0inf` when it is the string `'0'`. A decimal divisor, an empty
      one, or one already used in a concatenation gives `0`. This
      formatting quirk is not worth copying: give 0. In `DIVS`, a missing element of
      the second array counts as 0. `MOD(7,0)` and `REM(7,0)` return 7.
- [x] Reading an unassigned variable warns, uses `''` and continues.
      After that read `ASSIGNED()` returns 1. jbcc rejects an undeclared
      variable at compile time; decide whether to keep that rejection.
- [x] A non-numeric operand in arithmetic warns, uses 0 and continues.
- [x] COMMON variables (named and blank) start at `0` and count as
      assigned. This replaces the provisional "unassigned" rule in
      LANGUAGE-GAPS.
- [x] Decide the warning text and stream. TAFC writes the warnings to
      stdout; jbcc could use stderr, but tests should match the text.

Done for section 3 (2026-11-27):

- Warnings go to stderr as `file:line:column: warning: ...`, with TAFC's
  wording (`Non-numeric value -- ZERO USED`, `unassigned variable 'X' --
  NULL USED`, `division by zero`). The harness drops TAFC's stdout
  warning lines before comparing.
- jbcc keeps rejecting a read it can prove unassigned at compile time; it
  catches typos, and T24 scans already pass `--defer-unassigned-reads`.
  A read that reaches run time follows TAFC: warn, assign `''`, continue,
  so `ASSIGNED` is then 1.
- Numeric text: `''`, `'-'`, `'+'`, `'.'` are 0 without a warning;
  `'+5'`, `'5.'`, `'.5'` are numbers; `'1E3'` and `'1]2'` warn
  (`tests/tafc/nonnumeric-operands.b`).
- COMMON scalars and matrix elements start at 0 under prime
  (`tests/tafc/common-matrix-initial.b`).
- Found on the way: an empty FMT, OCONV or ICONV mask returns the value
  unchanged (ICONV also sets STATUS 1 in TAFC; jbcc's conversion STATUS is
  section 5).

## 4. Fixes in implemented functions

- [x] `OSREAD` converts LF to `@FM`, keeps CR and drops one trailing LF.
      For example `a LF b CR LF c` reads as `61 FE 62 0D FE 63`.
      `WRITESEQ` writes marks unchanged plus LF, and `READSEQ` strips the
      LF.
- [ ] Support embedded NUL: `LEN(CHAR(0):'A')` is 2 and
      `SEQ(CHAR(0))` is 0. The guide's SEEK and CHECKSUM blocks depend on
      it.
- [x] `CHAR(n)` takes n modulo 256: `CHAR(256)` is `00`, `CHAR(300)` is
      `,` and `CHAR(-1)` is `FF`.
- [x] `BITOR`, `BITAND` and `BITXOR` return unsigned 32-bit values:
      `BITOR(-1,0)` and `BITXOR(-1,0)` give 4294967295. `BITNOT`
      unsigned is confirmed; move it out of "provisional".
- [x] `FIELD` and `GROUP`: a position of 0 or below means 1, a count of 0
      means 1, and an empty delimiter returns the whole string.
- [x] `FIELD` and `GROUP` with a multi-byte delimiter: one field splits
      on the whole delimiter (`FIELD('123:-456',':-',2)` gives `456`).
      With a count above 1, TAFC starts one byte after the delimiter:
      `FIELD('123:-456:-789',':-',2,2)` gives `-456:-789` and
      `FIELD('ab12ab34ab','ab',2,2)` gives `b12ab34`. Reproduce this and
      document it as a reference quirk.
      Not reproduced: more probes (`FIELD('a--b----c--','--',2,2)` is
      `-b`, `FIELD(S,'--',4,9)` is `---c--`, and the delimited
      assignment forms) follow no consistent rule, so jbcc keeps
      whole-delimiter matching and LANGUAGE-GAPS lists the difference.
- [x] `INDEX(s, '', n)` returns 1, matches do not overlap
      (`INDEX('aaa','aa',2)` is 0) and a fractional occurrence truncates.
- [x] `COUNT('abc','')` is 3, `COUNT('aaa','aa')` is 1 and
      `DCOUNT('aaa','aa')` is 2.
- [x] `EREPLACE(s, '', r)` returns s unchanged.
      `EREPLACE('AAA','A','B',2)` gives `BBA`, and with start 2 (or
      occurrence 0, start 2) it gives `ABB`.
- [x] `ISCNTRL`, `ISPRINT` and the other character tests return 0 for
      the system marks and for bytes above 127. `ISCNTRL(@FM)` is 0,
      `ISCNTRL(CR:LF)` is 1 and `ISPRINT(CHAR(200))` is 0.
- [x] `MCP` turns `CHAR(255)` into `_`, and every other byte outside 32
      to 126 except FE, FD and FC into `.`. `MCPx` uses x for all of
      them.
- [x] FMT and OCONV masks: `&x` sets x as the fill character.
      `R2,&$#15` gives `$$$$$123,456.78`, `R2,C&*$#15` gives
      `**$123,456.78CR` and `R2,&0#15` gives `00000123,456.78`. The
      guide's comments show blanks, which is wrong.
- [x] `TIMEDIFF(ts1, ts2, mask)` returns ts2 − ts1, so every field has
      the sign of ts2 − ts1. The guide's prose says the opposite. Close
      the provisional sign item.
- [x] `CacheStats(bucket, CACHE_SIZE)` gives 2 for two small items; jbcc
      gives 12 (bytes). Probe more sizes to see what it counts.
- [ ] `@(-1)` is `ESC[H ESC[J` under vt100; jbcc gives `ESC[2J ESC[H`.
- [ ] `@TTY` is empty without a terminal; jbcc gives `phantom`.
- [x] Leave the 32-bit overflow alone: TAFC's 100-year `CHANGETIMESTAMP`
      gives 1990 and 1987 dates, and jbcc's dates are right. Note it in
      the README.

Done for section 4 (2026-11-27):

- OSREAD maps LF to `@FM`. TAFC also lets a program open a file it already
  has open (OSOPEN after OPENSEQ, two OPENSEQs); jbcc's `flock` locks now
  allow that within one process and still report another process's lock.
- CHAR modulo 256 (`CHAR(1.5)` is CHAR(1)); a result of 0 still needs NUL
  support, which waits for a value-model change (strings are
  NUL-terminated), as do `LEN(CHAR(0):'A')` and NUL bytes from files.
- FMT `&x` fill; TIMEDIFF sign and masks 2-7, counting from timestamp1
  (TAFC gives `-1^-30` one way and `1^29` the other).
- CacheStats CACHE_SIZE counts items, the purge limit counts items, and
  CacheClear drops the bucket (`tests/snippets/cache.b` now matches TAFC).
- Not copied, listed in LANGUAGE-GAPS: spaced comparison chains (TAFC
  reads `2 < 3 > 0` as an extraction plus implicit format), pre-1970
  timestamp truncation, and the 2038 overflow.
- Still open: `@(-1)` and the `@(-n)` table (with section 6), `@TTY`
  (`''` in TAFC without a terminal, `phantom` in jbcc), and the
  `fmt-numeric-g` lines where TAFC prints `345,600.00` for a scaled mask
  and `Error in Range Test.` for range masks.

## 5. Settled LANGUAGE-GAPS items

- [x] `MCPN{x}`: each byte outside 32 to 126 becomes x followed by two
      hex digits, with `.` as the default x (`a.FEb.01.C8_`). x itself is
      not escaped, so the conversion is lossy. `MCNP{x}` reverses it, and
      a short trailing `x4` gives `CHAR(4)`.
- [x] Invalid conversion mask: print `Unknown conversion code.`, return
      `''` and set STATUS to 1, for OCONV and ICONV.
  - `OCONV('abc','D')` returns `abc` with STATUS 1.
  - `ICONV('31 FEB 2020','D')` rolls over to 2 March 2020 (19055) with
    STATUS 3.
  - `ICONV('12:99','MT')` gives 49140 with STATUS 3.
  - `ICONV('abc','MD2')` gives `''` with STATUS 1.
  - `OCONV('abc','MD2')` gives `abc` with STATUS 0.
- [x] `TIMEDIFF` masks 2 to 7: count months from the earlier timestamp
      and clamp to the end of the month (31 Jan + 1 month is 29 Feb
      2020). From 31 Jan 2020 00:00 to 1 Mar 2021 01:00 the masks give:

      | Mask | Result |
      |---|---|
      | 2 | `13^1^1^0^0^0` |
      | 3 | `13^0^1^1^…` |
      | 4 | `1^29^1^…` |
      | 5 | `1^4^1^1^…` |
      | 6 | `1^1^1^1^…` |
      | 7 | `1^1^0^1^1^…` |

      From 31 Jan 2020 02:00 to 2 Mar 2020 00:00, mask 2 gives
      `1^1^22^…`.
- [x] Fractional day counts in `D` and `DG` truncate toward zero:
      732.75 is 01 JAN 1970, -0.5 is day 0, and -732.75 is day -732.
- [x] A pattern mask with decimals formats the number first and then
      fills the `#` positions from the right:
  - `R2(##.##)` on 12.345 gives `2..35`.
  - `R2(#####)` gives `12.35`.
  - `R2(###-###)` on 1234.5 gives `234-.50`.
  - `L2(##.###)` gives `12..35`.
- [x] Move to "confirmed":
  - `@TIMEZONE` reads `JBASE_TIMEZONE`, then `TZ`.
  - `MOD(-7,3)` is -1 and `MOD(7,-3)` is 1.
  - CONVERT uses the first mapping for a repeated source byte.
- [x] Update LANGUAGE-GAPS.md and the README paragraphs for each item.

Done for section 5 (2026-11-27):

- MCPN/MCNP, invalid masks with STATUS 1, fractional days, pattern masks
  with decimals and TIMEDIFF masks 2-7 (done in section 4).
- Found on the way and done: MD, MR and ML conversions, which jbcc lacked
  and the corpus uses about 1,460 times (`'MD2'` alone over 500); TAFC's
  ICONV date forms (`tests/tafc/iconv-dates.b`); OCONV times past 24
  hours, negative counts and MTH; MX decoding up to the first bad pair.
- Open: STATUS after OCONV, ICONVS and OCONVS, which TAFC sets to 1 in
  most cases without a rule found; chained ICONVS masks; year 10000.

## 6. New statements and functions (guide only, not in the corpus)

None of these appears as a statement or call in the four corpora; all
of them translate.

Simple:

- [x] `OUT n`: writes `CHAR(n MOD 256)` with no newline (`OUT 321` writes
      `A`, `OUT -1` writes FF). A non-numeric value warns.
- [x] `GROUPSTORE from IN to USING start, replace{, delim}`. The guide's
      example reproduces exactly. replace 0 inserts and any nonzero value
      replaces one group with the whole of `from`. A start past the end
      pads with delimiters (`a-b-c--Z`), start 0 means 1, and the
      delimiter defaults to `@FM`.
- [x] `RQM` is the same as `SLEEP`.
- [x] `INPUTNULL c` affects only `INPUT @`; plain `INPUT` keeps `&` and
      `_` as typed. `INPUTNULL ''` restores `_`.
- [x] `LOCK n` / `UNLOCK {n}` for a single process: LOCK always takes
      THEN, and the same process can lock again.
- [x] `PROCREAD v`: ELSE outside jCL. `PROCWRITE`: no effect.
- [x] `PAUSE {n}` waits up to n seconds. `WAKE port` (also for the own
      `@USERNO`) cancels the next PAUSE.
- [x] `IN var {FOR ds} THEN/ELSE` reads one raw byte from stdin (`x`
      gives 120) and ignores the DATA stack. The timeout is in tenths of
      a second, and EOF without FOR is a fatal STDIN error.

`@` variables:

- [x] `@DAY` is the day of the month, `@MONTH` the month, and `@YEAR`
      the **two-digit** year.
- [x] `@UID` is the user id, `@LEVEL` is 0, `@DATA` is `''` and `@EOF` is
      `CHAR(4)`.
- [x] `@CODEPAGE`, `@LOCALE`, `@USER.THREAD` and `@CALLSTACK` are `''`
      (`@CALLSTACK` in a main program).

`SYSTEM(n)` (jbcc supports 0, 14, 17, 18, 19, 24 and 1036):

- [x] Terminal and locale:

      | Key | TAFC value |
      |---|---|
      | 2 | 80 (width) |
      | 3 | 24 (depth) |
      | 7 | `TERM` |
      | 35 | `C` (language) |
      | 37 | `,` (thousands separator) |
      | 38 | `.` (decimal separator) |
      | 39 | `$` (currency) |

- [x] Clock and program:

      | Key | TAFC value |
      |---|---|
      | 12 | milliseconds since midnight |
      | 40 | program name |
      | 41 | release, `201214.0` |
      | 1000 and 1001 | program path |
      | 1011 and 1012 | release directories |
      | 1017 | `UNIX` |
      | 1027 | PROC directory |

- [x] Decide each remaining key from the full table (`SYSTEM(1..60)` and
      `SYSTEM(1000..1060)` in one probe). Keep "unsupported" for keys
      that describe licensing or shared memory.

Terminal codes:

- [x] `@(-n)` from the vt100 terminfo table:

      | Code | Bytes |
      |---|---|
      | -5 | `ESC[5m` |
      | -6, -8, -14, -16 | `ESC[m SI` |
      | -9 | BS |
      | -10 | `ESC[A` |
      | -13 | `ESC[7m` |
      | -15 | `ESC[4m` |
      | -17 | `ESC[5i` |
      | -18 | `ESC[4i` |
      | -19 | `ESC[C` |
      | -20 | LF |

      Also `@(5)` is `CR ESC[5C` and `@(c,r)` is `ESC[r+1;c+1H`.

Files and processes:

- [x] `TRANS` and `XLATE(file, key, field, code)`:
  - X returns `''`.
  - C returns the key for a missing record or an empty field.
  - V prints error 202 and returns `''` with STATUS 0.
  - Field -1 returns the whole record with its marks unchanged.
  - A single field comes back with its marks lowered (VM→SM, SM→TM).
  - A multivalued key returns one result per value.
  - An unknown file prints `201W` and then fails as NOT_FILE_VAR.
- [x] `READL` and `READVL` take a shared lock (`RECORDLOCKED` is 1).
      `MATWRITEU` keeps the lock. After `DELETEU` the record is gone and
      shows as unlocked.
- [x] `SSELECTV f TO var` puts the sorted keys in var. `SSELECTN`
      crashes TAFC, so follow the guide for it.
- [x] `CHAIN 'prog (I'` runs prog without returning and passes COMMON.
      The child's `SENTENCE()` includes `(I`. Without `(I`, COMMON starts
      at 0. A `CHAIN` to a command that is not a jBC program returned to
      the caller in TAFC; probe this again before copying it.
- [x] `ENTER name` and `ENTER @var` run name from PATH and never return.
- [ ] `EXECUTE … PASSDATA x RTNDATA y` with `COLLECTDATA` and `RTNDATA`
      in a jBC child passes data both ways (the parent got
      `back]world`). This needs jbcc to run jBC children.
- [x] `PRINTERR code:@FM:args` prints the jbcmessages text
      (` ** Error [ 201 ] ** ` then `Unable to open file X`). An unknown
      id prints `!!! Error message X not found !!!`. Start with the
      message ids jbcc already raises.

Done for section 6 (2026-11-27): every item above except PASSDATA,
COLLECTDATA and RTNDATA, which need jbcc to run separately built jBC
programs as EXECUTE children, and SYSTEM(41), TAFC's release number, which
jbcc does not imitate. Notes:

- IN reads standard input, not the DATA queue (TAFC ignores DATA for IN).
- RECORDLOCKED gives 1 for a READL lock, as the guide's table says.
- TRANS lowers every mark one level, field marks included, for field -1.
- CHAIN to a command that is not a jBC program returned in TAFC; jbcc
  always ends the program, as the guide says.
- `tests/test_tafc_probes.py` makes the 45 probes part of `just test`;
  42 match TAFC and 3 are known differences.

## 7. Not to implement, or needs a backend

- Needs a backend: `CALLJ`, `CALLdotNET`, `JQL*`, `OPENINDEX`/`READPREV`,
  `OPENSER`/`GETX`/`SEND`/`SENDX`, `WRITEXML`, `Logger`, `SPOOLER`,
  `JBASETHREAD*`, `UDTEXECUTE`, `OBJEXCALLBACK`, `DEFCE`.
- Not in PB201214: `BITTEST` (the guide calls it "reserved"; TAFC parses
  it as an undimensioned array), a `BITSET` statement, `@HEADER.BREAK`,
  `@FOOTER.BREAK` and `@TERMTYPE` ("Unknown @ system constant").
- [x] Make jbcc reject these the same way, or report them as unsupported
      with the reason. Already the case: BITTEST is an unknown function, a
      BITSET statement and `@HEADER.BREAK`/`@FOOTER.BREAK` are unsupported,
      and the backend-bound statements name the missing backend. jbcc keeps
      `@TERMTYPE` (the guide documents it; it reads `TERM`).

## 8. Investigate later

- [x] Playground: decide whether the jbc-playground needs a UI control
      for the emulation mode (prime or jbase), or whether prime alone is
      enough. It depends on how many guide examples differ between the
      two; `EMU=jbase` runs of the guide show that list.

  Finding (2026-11-27): of the 382 guide blocks TAFC ran under both
  emulations, 35 give different output once clock-dependent blocks and
  TAFC's warning text are set aside. Most come from error handling: under
  jbase a division by zero or a runtime error enters TAFC's debugger and
  ends the program, where prime warns and continues. The others are the
  switches section 1 covers (CONVERT order, LOCATE, MATCH, COUNT) and
  command output. The guide is written for prime, as T24 runs, so the
  playground needs no emulation control now; jbcc's `--emulation jbase` and
  `translate(..., emulation='jbase')` are there if one is wanted later.
  Done with it: under jbase, jbcc now stops on a division by zero.

## 9. Guide fixes (jbc-language)

- [x] FMT and OCONV `&x` comments: the fill character is x.
- [x] TIMEDIFF prose: the result is Timestamp2 − Timestamp1.
- [x] LOCALDATE and LOCALTIME 100-year examples: say that TAFC
      PB201214 overflows them.
- [x] CONVERT, LOCATE and MATCH: say which form T24 uses under prime.

Done in jbc-lang/jbc-language#34 (2026-11-27), together with the ISCNTRL
example (a field mark is not a control character) and the OCONV example
that repeats the FMT `&x` mask. The CONVERT chapter already shows both
argument orders; the LOCATE chapter now says what `IN A<f>` searches under
each emulation.

## 10. Re-run

- [ ] After each group lands, rerun `just tafc-guide` and
      `just tafc-recorded`, and record the counts here.
  - Harness baseline (2026-11-27, jbcc 0.7.0): 222 same, 84 differ (20
    of them volatile), 114 jbcc-rejects, 41 jbcc-fails, 545
    tafc-rejects. `tests/tafc`: 2 of 34 match.
  - After section 1 (emulation, CONVERT, LOCATE, MATCH): 224 same, 82
    differ (19 volatile), 114 jbcc-rejects, 41 jbcc-fails; the `ifs` and
    `matches` blocks moved to same, none moved away. `tests/tafc`: 11 of
    39 match.
  - After section 2 and part of section 4 (number model, bit functions,
    INDEX, EREPLACE, ISCNTRL, MCP, FIELD positions): 228 same, 78 differ
    (19 volatile), 114 jbcc-rejects, 41 jbcc-fails; cos, tan, ereplace
    and iscntrl moved to same, none moved away. `tests/tafc`: 20 of 39.
  - After sections 3 to 6: 259 same, 85 differ (21 volatile), 86
    jbcc-rejects, 31 jbcc-fails; 35 blocks moved to same (CHAIN, ENTER,
    GROUPSTORE, OUT, LOCK, PROCREAD, PRINTERR, @-variables, COMMON,
    division by zero and others), none moved away. `tests/tafc`: 42 of 45,
    and the other 3 are known differences.
  - The earlier scratch run, without start-up retries, had 216 same and
    47 jbcc-fails; the difference was TAFC start-up failures.

## 11. Byte 0 in strings (design note)

jbcc values are NUL-terminated C strings, so `CHAR(0)`, `CHAR(256)`, NUL
bytes from files and MX/MCNP results with 00 cannot be held; TAFC's can.
Scale (2026-11-27): jbc.c has 9,095 lines, 315 exported functions, about
300 calls to C string functions and 810 `const char *` uses, and the
compiler writes every constant as a C string literal. Options:

1. A value type with a length (pointer and size) through the runtime and
   the generated code. Complete, but it touches every function.
2. A length kept in the allocation header (`struct jbc_buffer`) and a
   `jbc_length(value)` that reads it for heap values and falls back to
   `strlen` for literals and slices. Smaller, but every place that takes a
   slice or uses a C string function has to be audited.
3. A reserved internal byte for NUL, translated at input and output.
   Smallest, but it breaks LEN, SEQ and byte comparisons on that byte.

Recommendation: option 1, on its own branch, after the TAFC probes and the
guide cross-check are green, so a regression shows at once. T24 code shows
no NUL bytes in strings, so this is for completeness, not the corpus.

- [ ] Byte 0 in strings, as above.
