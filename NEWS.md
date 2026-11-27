# News

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
