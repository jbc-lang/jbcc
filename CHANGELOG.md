# Changelog

## Unreleased

### Added

- `--t24-stub-members` accepts any arguments for a listed set of R19
  component members in testing. A name inside its own `EQUATE` expansion
  stays a plain name, as in the reference, instead of an error.
- The corpus checker reads `published` members and methods without a
  body, and `--t24-stub-void-results` lets a method without a result be
  used as a value in testing. The README describes every T24 flag.
- A built-in `JBC.h` with the constants the guide's examples use, used
  when no `JBC.h` is on the include paths, with a note on stderr.
  `--no-builtin-includes` turns it off.
- The R19 corpus checker accepts a placeholder scalar for a matrix
  parameter and standard operations on tables a known component does not
  declare (with a warning), and `--t24-exclude-test-framework` excludes
  the `SE/SE_Test*` components. Duplicate component definitions merge
  as partial exports, dropping only members they declare differently.
- `NOTS`, `LENS`, `FSUB` and `GETCWD`.
- The R19 corpus checker reads hook `interface` declarations.
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
