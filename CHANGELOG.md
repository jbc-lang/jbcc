# Changelog

## Unreleased

### Added

- T24 unit tests (`*.tut`) translate: `TESTCASE name` heads a program, and
  `UTF.method(...)` calls take scalars by reference and whole matrices.
  `tools/check_corpus.py --t24-tests` scans them (TUT.md).
- A UTF runtime: `UTF.runTest` calls the target routine with the test's
  parameters, and the assertions decide the test's verdict, printed as the
  last stderr line and given as the exit status.
- `tools/run_tuts.py` (`just tut`) builds each R19 unit test with its
  target, runs it and writes a JSON report.
- UTF stubs: routines a unit test's target calls answer from the test's
  `addStub` definitions, and data-access routines (`F.READ`, `CACHE.READ`,
  component table reads and writes) from its `setRecord` records. R19
  component property accessors are generated from the component
  definitions. Stubs cover conditions, recorded EASYQA calls, stopping
  calls, fixed dates and times, and routine names for component methods.
  Of the stubs that match a call, the most specific answers, then the
  newest; `reset` clears the stubs and the records. The records are
  in-memory files, so a target's own `OPEN`, `READ` and `WRITE` statements
  see them, and a DEFC function the runtime lacks answers from the stubs.
  18,199 of the 26,307 tests pass.

### Changed

- Dynamic-array indices and matrix subscripts follow TAFC PB201214: text
  that is not a number is 0 in an index, a fraction truncates, `X<0>`
  reads `''` and assigned prepends, a later 0 means the whole element,
  and a matrix read takes a negative subscript as 1.
- `ABS('')` is 0, and `ABS` of text that is not a number returns it
  unchanged, as in TAFC.
- MATBUILD without an end leaves out trailing empty elements, as in TAFC.
- `DIM X(0)` and `DIM X('')` give 10 elements, and FOR takes an empty bound
  as 0 and an empty step as no iteration, as in TAFC.

- String literals longer than C99's 4,095-byte limit are emitted in
  pieces joined at run time.

## 0.8.1 (2026-11-27)

### Changed

- The browser (WASI) runtime no longer links the PASSDATA, RTNDATA and
  select-list exchange files. COLLECTDATA gives '' and RTNDATA is discarded
  there, as without an EXECUTE caller. 0.8.0 programs failed to load in
  the playground, whose sandbox does not grant the file calls that fopen
  imports.

## 0.8.0 (2026-11-27)

This release checks jbcc against a real TAFC PB201214 runtime and follows
it: 268 of the guide's examples now give TAFC's output, and
`tests/tafc/` holds 65 probes with TAFC's recorded output. Several
results change as a consequence; see Changed.

### Added

- `--emulation prime|jbase` (and `emulation=` in `jbcc.browser.translate`).
  The default is prime, the emulation T24 runs under.
- Strings can hold byte 0, as TAFC's can (NUL-BYTES.md): `CHAR(0)` and
  `CHAR(256)` work, and string, dynamic array and search functions, output,
  files, records, INPUT, KEYIN, DATA and EXECUTE data keep the byte.
- The masked decimal conversions MD, MR and ML for OCONV, ICONV and FMT,
  with the Z, comma, $, minus, C, D, E, P and T options.
- `EXECUTE ... PASSDATA expression RTNDATA variable` with the `COLLECTDATA`
  and `RTNDATA` statements, and `PASSLIST`. EXECUTE shares the default
  select list with the jbcc program it runs, as TAFC does.
- ENCRYPT and DECRYPT implement JBASE_CRYPT_XOR11 and JBASE_CRYPT_BASE64,
  and the Base64 mask bit.
- The guide statements OUT, GROUPSTORE, INPUTNULL, LOCK, UNLOCK, PROCREAD,
  PROCWRITE, RQM, PAUSE, WAKE, IN, CHAIN, ENTER, PRINTERR, READL, READVL,
  MATWRITEU, DELETEU, SELECTV, SSELECTV, SELECTN and SSELECTN; the TRANS
  and XLATE functions; the @DAY, @MONTH, @YEAR, @UID, @EOF, @LEVEL, @DATA,
  @CODEPAGE, @LOCALE, @USER.THREAD and @CALLSTACK variables.
- SYSTEM keys 1, 2, 3, 7, 12, 35 to 40 and 1017, and the keys T24 reads
  (11, 1019, 1021, and those TAFC reports as 0 or empty). `ASSIGN value TO
  SYSTEM(n)` keeps the value for any key.
- The `LOCATE(key, array{, f{, v}}; pos{; order})` function form.
- MCPN and MCNP; pattern masks with decimal places such as `R2(##.##)`;
  the MTH time mask.
- `@(-n)` codes up to -20 with TAFC's vt100 sequences, and `@(n)`.
- `tools/tafc_crosscheck/`, the `tafc-guide`, `tafc-probe` and
  `tafc-recorded` recipes, and `tests/test_tafc_probes.py`, which runs the
  TAFC probes in `just test`.
- MISSING-BACKENDS.md lists the features that need a service jbcc does not
  have.

### Changed

- Arithmetic follows TAFC's number model: exact decimals at PRECISION,
  which defaults to 4; operands round half away from zero, `*` and `/`
  truncate, and integers have no size limit. Comparisons and truth tests
  round the same way. The first PRECISION in a unit applies from its first
  line, and each subroutine runs at its own. Math functions round to
  PRECISION; FADD, FSUB, FMUL and FDIV print ten significant digits;
  DROUND defaults to four places; SADD, SSUB, SMUL and SDIV keep 14 places.
- Errors that TAFC reports and continues past now warn on stderr and
  continue: division by zero (0), a nonnumeric operand (0), an unassigned
  read (an empty string), an unknown conversion mask ('' with STATUS 1).
  Under `--emulation jbase`, a division by zero stops the program.
- Under prime emulation: CONVERT takes `CONVERT(from, to, text)`; LOCATE's
  last coordinate is the start; `BY 'AR'` and `'DR'` compare numbers
  numerically; MATCH patterns accept `...`, lower-case codes and ranges;
  empty and missing elements count as 0 in ADDS and the other element
  operations; COMMON starts at 0; NUM skips blanks around a number and
  rejects a lone sign or point. Under jbase, COUNT, COUNTS and DCOUNT count
  overlapping matches.
- Conversions: codes separated by value marks run in turn; STATUS() after
  each mask family is as TAFC sets it; ICONVS and OCONVS keep every
  element; OCONV's L and R codes are length and range tests, not FMT
  masks; ICONV reads TAFC's date forms and rolls over impossible days with
  STATUS 3; OCONV truncates fractional days and lets times pass 24 hours.
- CAPTURING drops one final newline; INPUT writes its prompt only when
  standard input is a terminal; OSREAD turns line feeds into field marks
  and keeps byte 0; READSEQ ends a line at byte 0.
- MATPARSE: one trailing delimiter adds no empty field, SETTING is 0 when
  fields are left over, `USING ''` splits into bytes.
- CHAR takes its argument modulo 256; FMT's `&x` sets the fill character;
  TIMEDIFF returns timestamp2 minus timestamp1 with masks 2 to 7; BITAND,
  BITOR, BITXOR and BITNOT return unsigned 32-bit values; INDEX finds an
  empty needle at 1; FIELD and GROUP read counts below 1 as 1; MCP shows
  byte 255 as `_`.
- CacheStats CACHE_SIZE and the purge limit count items, and CacheClear
  removes the bucket.
- A program can reopen a file it already has open through OPENSEQ or
  OSOPEN; RTNLIST no longer stops the program.

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
