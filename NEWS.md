# News

## 2026-11-27 · Checked against TAFC

[jbcc 0.8.0](https://pypi.org/project/jbcc/0.8.0/) is checked against a
real TAFC PB201214 runtime and follows it: 268 of the guide's examples now
print what TAFC prints. It adds `--emulation prime|jbase` (prime by
default, as T24 runs), byte 0 in strings, the MD masks, EXECUTE's
PASSDATA and PASSLIST, Base64 in ENCRYPT, and the guide statements T24
does not use. Arithmetic now follows TAFC's PRECISION 4 decimal model, and
errors TAFC continues past now warn and continue. The
[changelog](https://github.com/jbc-lang/jbcc/blob/main/CHANGELOG.md) lists
every change, and
[MISSING-BACKENDS.md](https://github.com/jbc-lang/jbcc/blob/main/MISSING-BACKENDS.md)
what still needs a backend.

## 2026-11-27 · Numeric FMT masks

[jbcc 0.7.0](https://pypi.org/project/jbcc/0.7.0/) completes the guide's
`FMT` masks: thousands separators, currency, credit indicators, scaling
and `Z`, as in `FMT(X, 'R2,C&*$#15')`. It adds the `G` group conversion,
and `FMT` and `OCONV` now accept each other's masks, as the guide's
tables describe. [LANGUAGE-GAPS.md](https://github.com/jbc-lang/jbcc/blob/main/LANGUAGE-GAPS.md)
lists what jbcc does not do yet.

## 2026-11-27 · MC conversions and FMT patterns

[jbcc 0.6.0](https://pypi.org/project/jbcc/0.6.0/) adds the `MC`
conversions of the guide's `OCONV` table to `FMT` and `OCONV` (`MCA`,
`MCN`, `MCL`, `MCU`, `MCT`, `MCC`, `MCDX`, `MCXD` and others) and `FMT`
pattern masks such as `R((###) ###-###)`. `MCP` now prints non-printable
bytes as `.`, as the guide shows, while field, value and subvalue marks
still print as `^`, `]` and `\`.

## 2026-11-27 · Guide functions and the JBC.h cache

[jbcc 0.5.0](https://pypi.org/project/jbcc/0.5.0/) implements 36 functions
that the guide describes but T24 never calls, such as `SOUNDEX`, `REGEXP`,
`IFS`, `CHANGETIMESTAMP`, `SADD` and the `BIT*` table, and the in-memory
cache that `JBC.h` declares. The guide's examples for them run as written,
including in the playground. It also adds the `MX` and `DG` masks.

## 2026-11-27 · T24 R19 corpus

[jbcc 0.4.0](https://pypi.org/project/jbcc/0.4.0/) translates the
componentised T24 R19 corpus to strict C99: 39,669 of its 39,675
production units, with component calls checked against the catalogued
declarations. It adds date and time zone functions, `MSLEEP`,
`CLEARCOMMON`, the `MCP` mask and a built-in `JBC.h` for the guide's
examples. R13, R10 and R07 still translate in full.

## 2026-11-26 · T24 R13 corpus

[jbcc 0.3.0](https://pypi.org/project/jbcc/0.3.0/) translates all 19,536
source units of the T24 R13 corpus to strict C99, alongside every unit of
R10 and R07. It adds `DELETESEQ`, `CHDIR`, `ISALNUM`, `BITAND` and
`BITNOT`, among other constructs the R13 sources use.

## 2026-11-25 · Playground link on PyPI

[jbcc 0.2.1](https://pypi.org/project/jbcc/0.2.1/) links to the
[jBC Playground](https://online.jbc-lang.org/) from its PyPI description.

## 2026-11-25 · Browser translation API

[jbcc 0.2.0](https://pypi.org/project/jbcc/0.2.0/) packages the
[Python API](README.md#browser-translation-api) for compiling jBC
projects in Pyodide. The native CLI is available through `uvx jbcc`.

## 2026-11-25 · jbcc is on PyPI

[jbcc 0.1.0](https://pypi.org/project/jbcc/0.1.0/) is available on PyPI. Run
a local jBC program from any directory with uv and a C99 compiler.

```sh
uvx jbcc --run hello.b
```
