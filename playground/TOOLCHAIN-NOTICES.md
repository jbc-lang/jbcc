# Browser toolchain notices

The playground serves the following dependencies from the pinned packages
in [bun.lock](https://github.com/jbc-lang/jbcc/blob/main/playground/bun.lock).

- Pyodide 314.0.8 includes CPython and its standard library. See the
  [Pyodide sources and license](https://github.com/pyodide/pyodide/tree/314.0.8)
  and [Python license](https://docs.python.org/3/license.html).
- YoWASP Clang 21.1.4-3 packages LLVM, Clang, LLD, and the WASI sysroot.
  See the [published toolchain package](https://www.npmjs.com/package/@yowasp/clang/v/21.1.4-3),
  [YoWASP sources](https://codeberg.org/YoWASP/clang),
  [LLVM license](https://llvm.org/LICENSE.txt) and
  [wasi-libc license](https://github.com/WebAssembly/wasi-libc/blob/main/LICENSE).
- browser_wasi_shim 0.4.2 is distributed under the MIT license included
  alongside this notice. [WASI shim sources](https://github.com/bjorn3/browser_wasi_shim).
