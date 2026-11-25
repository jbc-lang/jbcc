# Local jBC playground

## Browser-only build

Run `just playground-static` from the repository root and open
<http://127.0.0.1:18766/>. This builds `dist/playground` with Bun and serves
it with Python's static HTTP server. **Run** loads the compiler on demand.
The worker uses Pyodide for jbcc and Clang/LLD for the generated C, and a
separate sandboxed worker runs the Wasm. The browser keeps the current
draft. Named local saves and Import/Export are tracked in
[WASM-PLAN.md](../WASM-PLAN.md).
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
`JBCC_PLAYGROUND_STATIC=1 JBCC_PLAYWRIGHT_CHANNEL=chrome bunx playwright test`
from `playground/`. For Playwright's Firefox or WebKit, install the engines
with `bunx playwright install firefox webkit` and set
`JBCC_PLAYWRIGHT_BROWSER` to `firefox` or `webkit` in place of the channel.

## Cloud Run stack

From the repository root, run `just playground` with Docker Compose
running and open <http://127.0.0.1:18765/>. Set `JBCC_PLAYGROUND_PORT` to
change the host port. With Docker Compose alone, run
`docker compose -f playground/compose.yaml up --build`. Stop it with
Ctrl+C.

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
The **?** button opens help for files, routines, hosted limits, and cloud
projects.

This version targets console programs. The compiler reports source
locations for unsupported operations such as shell commands, sequential
files and devices, terminal cursor and keyboard controls, timed input,
native C calls, and printer output. Live keystrokes, jBASE file
backends, and T24 services are unavailable. Standard input is a
prefilled byte stream that ends when consumed.

The Go API serves the static HTML, CSS, and Bun-bundled TypeScript on
loopback. It forwards builds to a worker on a private Docker network.
The worker invokes the checked-out jbcc Python sources and Emscripten
4.0.23. Local mode skips sign-in, cloud saves, and per-user rate
limiting. The build API accepts JSON with one `entry` path, a list of
linked `units`, and `files` as an array of `{path, source}` objects.
Successful builds return base64 JavaScript and Wasm with diagnostics.
Both services can run without Google Cloud credentials.

The local editor adapts the textarea, tab, draft, and theme patterns
from [asm8](https://github.com/begoon/asm8).

## Hosted access

In production the editor accepts GitHub sign-in through Firebase. The
API enforces the pilot allowlist, a shared six-starts-per-minute quota,
and one build at a time per account. Each invited account can save
private named projects. Open **Projects** and select a saved name to fill
the **Cloud project** field. Click **Load** to replace the current draft.
Load a newer revision before retrying a save
that reports a conflict. The [GCP runbook](../GCP.md) lists the hosting
configuration.

## Verify locally

Start the Docker stack, then run these commands from the repository
root. Browser tests also use Python and a local C compiler to compare
Wasm behavior with native jbcc output.

```sh
cd playground
bun install --frozen-lockfile
bunx playwright install chromium
bunx playwright test
go test ./...
```

Set `JBCC_PLAYWRIGHT_CHANNEL=chrome` to use an installed Google Chrome.
Set `JBCC_TEST_FIRESTORE_PROJECT` and `JBCC_TEST_FIRESTORE_DATABASE` to
enable the two-client Firestore integration test. It uses Application
Default Credentials or a short-lived `JBCC_TEST_FIRESTORE_TOKEN`, creates
temporary documents, and deletes them after the test.
