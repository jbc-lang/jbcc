# Changelog

## Unreleased

### Added

- `NOTS`, `LENS`, `FSUB` and `GETCWD`.
- `ISUPPER`, `ISLOWER` and `ISSPACE`.
- `MSLEEP` and `CLEARCOMMON`.
- `MAKETIMESTAMP`, `LOCALDATE`, `LOCALTIME`, `TIMEDIFF` (masks 0 and 1)
  and `@TIMEZONE`.
- `ASSIGNED` and `UNASSIGNED` accept an R19 component call.
- A stray `END` after the final `END` is ignored with a warning.

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
