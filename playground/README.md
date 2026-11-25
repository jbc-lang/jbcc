# Local jBC playground

Run `just playground` from the repository root and open
<http://127.0.0.1:18766/>. This builds `dist/playground` with Bun and serves
it with Python's static HTTP server. **Run** loads the compiler on demand.
The worker uses Pyodide for jbcc and Clang/LLD for the generated C, and a
separate sandboxed worker runs the Wasm. The browser saves the working
draft in localStorage. Use **Project name** and **Save** to keep a named
project in IndexedDB. **Projects** lists the names, and **Load** opens the
chosen save after confirmation. Edits to a saved or loaded project
autosave after a short pause. If another tab updates the same name, the
editor keeps its working draft and reports a conflict. Save under a
different name to keep both versions.

Use **Export** to download the open project as a versioned JSON file.
**Import** can open it in another browser profile. Exports contain the project name, files, **Main**,
linked routines, selected tab, and prefilled stdin.
Browser session values use a virtual working directory of `/`, zero for
the process and port numbers, and an empty OS login.

The lockfile records the npm integrity hashes for Pyodide 314.0.8,
YoWASP Clang 21.1.4-3 (including the WASI sysroot), and browser_wasi_shim
0.4.2. The build copies the package toolchain assets into versioned
paths. See the [Pyodide license](https://github.com/pyodide/pyodide/blob/main/LICENSE),
[YoWASP package license and upstream sources](https://codeberg.org/YoWASP/clang),
[LLVM license](https://llvm.org/LICENSE.txt),
[wasi-libc license](https://github.com/WebAssembly/wasi-libc/blob/main/LICENSE),
and the [WASI shim license](https://github.com/bjorn3/browser_wasi_shim/blob/main/LICENSE-MIT).

Run the browser suite against this build with
`JBCC_PLAYWRIGHT_CHANNEL=chrome bunx playwright test`
from `playground/`. For Playwright's Firefox or WebKit, install the engines
with `bunx playwright install firefox webkit` and set
`JBCC_PLAYWRIGHT_BROWSER` to `firefox` or `webkit` in place of the channel.

## Writing and running programs

The editor starts with `hello.b`. Choose **Status lookup (3 files)** to
try a program and a subroutine that share an include. Pick the main file
with **Main**. For each separately compiled subroutine or function,
select its tab and check **Link as routine**. Include files are expanded
by `$INSERT` or `$INCLUDE` and can stay unchecked. An include searches
relative to its source file, then relative to the project root. Paths
are case-sensitive. Drafts and the theme are saved in the browser.

**Run** compiles the project and executes the Wasm in an isolated browser
worker if compilation succeeds. Fill **Standard input**
before running a program that reads with `INPUT`. **Stop** cancels a
build or terminates a running program. The runner allows five seconds,
64 MiB of Wasm memory, and 64 KiB of combined console output.
The **?** button opens help for files, routines, limits, and browser projects.

This version targets console programs. The compiler reports source
locations for unsupported operations such as shell commands, sequential
files and devices, terminal cursor and keyboard controls, timed input,
native C calls, and printer output. Live keystrokes, jBASE file
backends, and T24 services are unavailable. Standard input is a
prefilled byte stream that ends when consumed.
