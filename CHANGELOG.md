# Changelog

## Unreleased

### Added

- The `MX` mask for `FMT`, `OCONV` and `ICONV` (bytes as hexadecimal),
  and `DG` for `ICONV` and `OCONV` (`YYYYMMDD`).

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
