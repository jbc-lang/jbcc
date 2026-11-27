# Changelog

## Unreleased

### Added

- `--emulation prime|jbase` (and `emulation=` in `jbcc.browser.translate`).
  The default is prime, the emulation T24 runs under.
- The `LOCATE(key, array{, f{, v}}; pos{; order})` function form.
- `tools/tafc_crosscheck/` and the `tafc-guide`, `tafc-probe` and
  `tafc-recorded` recipes compare jbcc with TAFC PB201214 in Docker;
  `tests/tafc/` holds probes with TAFC's recorded output.

### Changed

- Under prime emulation, which is now the default:
  - the CONVERT function takes `CONVERT(from, to, text)`;
  - `LOCATE x IN A<f>` searches fields from field f, `A<f,v>` the values of
    field f from v, and `A<f,v,s>` the subvalues of value v from s;
  - `BY 'AR'` and `'DR'` compare numbers numerically and other values
    right-justified;
  - MATCH patterns accept `...`, lower-case codes and `n-m` ranges, and `C`
    is literal text.
  The previous behaviour is available with `--emulation jbase`.
- LOCATE drops a trailing zero coordinate, and a start past the end is
  the position returned for a miss, as TAFC does.
- MATCHFIELD uses the prime pattern codes in both emulations.
- Arithmetic follows TAFC's number model: exact decimals at PRECISION,
  which defaults to 4; operands round half away from zero, `*` and `/`
  truncate, and integers have no size limit (no overflow errors).
  Comparisons and truth tests round the same way, and prime ignores spaces
  and tabs around numbers.
- The first PRECISION statement in a unit applies from its first line, and
  each subroutine and function runs at its own PRECISION.
- Math functions round their result to PRECISION; FADD, FSUB, FMUL and FDIV
  print ten significant digits; DROUND defaults to four places.
- ADDS, SUBS, MULS, DIVS, ABSS and NEGS treat empty and missing elements as
  0 under prime, and warn and continue for nonnumeric elements and zero
  divisors. REUSE of a dynamic array has no effect instead of an error.
- BITAND, BITOR, BITXOR and BITNOT return unsigned 32-bit values and count
  empty or nonnumeric operands as 0.
- Errors that TAFC reports and continues past now warn on stderr and
  continue: division by zero (0), a nonnumeric arithmetic operand (0) and
  a runtime read of an unassigned variable (an empty string, which it then
  holds). An empty conversion mask returns the value unchanged.
- Under prime, COMMON variables and COMMON matrix elements start at 0.
- OSREAD turns line feeds into field marks; a program can reopen a file it
  already has open through OPENSEQ or OSOPEN.
- CHAR takes its argument modulo 256; FMT's `&x` sets the fill character.
- TIMEDIFF returns timestamp2 minus timestamp1 and supports masks 2 to 7
  (calendar months and years).
- CacheStats CACHE_SIZE counts items, the purge limit counts items, and
  CacheClear removes the bucket.
- The masked decimal conversions MD, MR and ML for OCONV, ICONV and FMT,
  with the Z, comma, $, minus, C, D, E, P and T options.
- ICONV reads dates as TAFC does (month names, US and European numeric
  forms, YYYYDDD), rolls over impossible days with STATUS 3 and returns ''
  with STATUS 1 for other bad input; times may overflow. An unknown OCONV
  or ICONV mask warns and returns '' with STATUS 1 instead of stopping.
- OCONV truncates fractional day counts, returns text unchanged for a date
  mask, lets times pass 24 hours, and supports MTH.
- MCPN and MCNP; pattern masks with decimal places such as R2(##.##); MX
  decoding stops at the first non-hex pair.
- The guide statements OUT, GROUPSTORE, INPUTNULL, LOCK, UNLOCK, PROCREAD,
  PROCWRITE, RQM, PAUSE, WAKE, IN, CHAIN, ENTER, PRINTERR, READL, READVL,
  MATWRITEU, DELETEU, SELECTV, SSELECTV, SELECTN and SSELECTN, the TRANS
  and XLATE functions, the @DAY, @MONTH, @YEAR, @UID, @EOF, @LEVEL, @DATA,
  @CODEPAGE, @LOCALE, @USER.THREAD and @CALLSTACK variables, and SYSTEM keys
  1, 2, 3, 7, 12, 35 to 40 and 1017, as TAFC PB201214 runs them.
- `@(-n)` writes TAFC's vt100 sequences: `@(-1)` is `ESC[H ESC[J`, and the
  codes up to -20 cover blink, reverse, underline, the printer and cursor
  moves; `@(n)` moves to a column.
- `tests/test_tafc_probes.py` runs the TAFC probes in `just test`.
- The SYSTEM keys T24 reads (11, 1019, 1021, and the keys TAFC reports as
  0 or empty), and `ASSIGN value TO SYSTEM(n)` for any key, which SYSTEM
  then returns.
- INDEX finds an empty needle at 1; CHANGE and EREPLACE leave the text
  unchanged for an empty search string; FIELD and GROUP read occurrences
  and counts below 1 as 1; ISCNTRL is false for the system marks; MCP shows
  byte 255 as `_`.

## 0.7.0 (2026-11-27)

### Added

- Numeric `FMT` masks: scaling, `Z`, `,`, the credit indicators `C`, `D`,
  `E`, `M` and `N`, `$` and `&x`, as in `FMT(X, 'R2,C&*$#15')`.
- The `G` group conversion for `OCONV` and `FMT`.
- `FMT` accepts `OCONV`'s `D` and `MT` masks, and `OCONV` accepts `FMT`'s
  format masks, as the guide's tables describe.

## 0.6.0 (2026-11-27)

### Added

- The `MC` conversions for `FMT` and `OCONV`: `MCA`, `MC/A`, `MCN`,
  `MC/N`, `MCB`, `MC/B`, `MCC;s1;s2`, `MCL`, `MCU`, `MCT`, `MCDX`, `MCXD`
  and `MCP` with a replacement character.
- `FMT` pattern masks: `L(...)`, `R(...)` and bare `#` patterns.

### Changed

- `MCP` turns non-printable bytes other than the three system marks into
  `.`, as the guide's `OCONV` table and example show.

## 0.5.0 (2026-11-27)

### Added

- The in-memory cache from `JBC.h`: `CachePut`, `CacheGet`, `CacheExists`,
  `CacheDelete`, `CacheClear`, `CacheClearAll`, `CacheKeyList`,
  `CacheBucketList`, `CacheStats`, `CacheClearStats`, `CacheSetOption` and
  `CacheGetOption`. A `DEFC` with the header's signature runs jbcc's
  runtime cache, also in the browser, and the built-in `JBC.h` declares
  them.
- Functions from the guide that the T24 corpora never call: `TAN`, `ASIN`,
  `ACOS`, `ATAN`, `FADD`, `FMUL`, `FDIV`, `FCMP`, `SADD`, `SSUB`, `SCMP`,
  `BITSET`, `BITRESET`, `BITCHANGE`, `BITCHECK`, `BITLOAD`, `ISCNTRL`,
  `ISGRAPH`, `ISPRINT`, `ISPUNCT`, `ISXDIGIT`, `ANDS`, `ORS`, `MODS`,
  `IFS`, `SEQS`, `CHARS`, `STRS`, `LENSDP`, `SOUNDEX`, `REGEXP` and
  `CHANGETIMESTAMP`, plus `DELENV`, `DIR`, `GETUSERNAME` and
  `GETUSERGROUP` outside the browser.
- The `MX` mask for `FMT`, `OCONV` and `ICONV` (bytes as hexadecimal),
  and `DG` for `ICONV` and `OCONV` (`YYYYMMDD`).

### Changed

- The built-in `JBC.h` note on stderr says "definitions" instead of
  "constants", since the header now declares functions.

## 0.4.0 (2026-11-27)

### Added

- Translate every catalogued production unit of the componentised T24
  R19 corpus to strict C99: 39,669 of 39,675, with 6 excluded because
  their generated inserts have no `.domain` class in the dump.
- Functions: `ISUPPER`, `ISLOWER`, `ISSPACE`, `NOTS`, `LENS`, `FSUB`,
  `GETCWD`, `MAKETIMESTAMP`, `LOCALDATE`, `LOCALTIME` and `TIMEDIFF`
  (masks 0 and 1).
- Statements: `MSLEEP` and `CLEARCOMMON`.
- `@TIMEZONE`, and `@COMPANYNO` as a writable session value that starts
  empty (provisional).
- The `MCP` mask for `FMT` and `OCONV` shows field, value and subvalue
  marks as `^`, `]` and `\`.
- `DYNTOXMLEXT`, `DATELOCALETOGREGORIAN` and `DATEGREGORIANTOLOCALE`
  parse and report a missing backend when reached.
- A built-in `JBC.h` with the constants the guide's examples use, used
  when no `JBC.h` is on the include paths, with a note on stderr;
  `--no-builtin-includes` turns it off.
- `ASSIGNED` and `UNASSIGNED` accept an R19 component call.
- The corpus checker reads R19 component declarations in full (hook
  interfaces, `published` members, methods without a body, matrix
  property rank, duplicate definitions) and adds the T24 testing flags
  `--t24-stub-members`, `--t24-stub-void-results`, `--t24-relax-access`,
  `--t24-exclude-test-framework` and `--t24-exclude-missing-domains`.
  The README section "T24 corpus flags" describes each one.

### Changed

- `jbcc --help` and `tools/check_corpus.py --help` group their options
  and describe each one in a block, with examples.
- A stray `END` after the final `END` is ignored with a warning, and a
  name inside its own `EQUATE` expansion stays a plain name, as the
  reference compiler does.
- `--defer-unassigned-reads` also covers the target of `CONVERT` and
  `CHANGE`.

## 0.3.0 (2026-11-26)

### Added

- Translate every source unit in the T24 R13 corpus, as well as R10 and
  R07, to strict C99.
- `DELETESEQ`, `CHDIR`, `ISALNUM`, `BITAND` and `BITNOT`.
- `READXML`, `READXMLU` and `VALIDATE_PRODUCT_LICENSE` parse and report
  a missing backend when reached.
- `ASSIGNED` and `UNASSIGNED` accept a dynamic-array extraction.
- A routine can `DIM` a scalar COMMON member; units that dimension it
  share its elements.
- The corpus checker applies source fixes to R13 and can exclude
  non-Temenos routines with `--t24-exclude-local-routines`.

### Changed

- The corpus documentation takes the PB201214 headers from the
  `jbc-extract` checkout through `just tafc-headers`.

## 0.2.1 (2026-11-25)

### Changed

- Link to the online jBC Playground from the PyPI description.

## 0.2.0 (2026-11-25)

### Added

- Include the browser translation API in the PyPI package. It supports
  multi-file projects and host-provided include resolution, and emits C
  for a WASI toolchain.

## 0.1.0 (2026-11-25)

### Added

- Published the first jbcc release on [PyPI](https://pypi.org/project/jbcc/0.1.0/).
  The wheel and source distribution include the C runtime and expose the
  `jbcc` command through `uvx jbcc`.
