# Browser-only jBC playground

Keep the current multi-file editor at `https://online.jbc-lang.org/`.
Run **jBC → C → WebAssembly → browser runner** on the visitor’s device.
Keep named projects in browser storage and support files for backup and
transfer. The public playground will work without an account.

## What the prototype established

- [x] Run the existing Python translator in Pyodide. Chrome translated
  six programs, including Status lookup with a shared include and a
  linked subroutine.
- [x] Build and run jbcc-generated C with Wasm-hosted Clang/LLD on a
  static server without cross-origin isolation. Five examples matched
  native output and status. Rule 110 needed the wasi-libc long-double
  formatting library. The stdin fixture exposed a dependency on POSIX
  terminal APIs that needs a WASI implementation.

The tested Pyodide and Clang assets total about 31 MiB when gzip-compressed.
The initial download is acceptable. Load it on first **Run**, show progress,
and reuse the downloaded assets and initialized toolchain.

## 1. Build and test the static playground locally

- [x] Produce a static build served by a plain local HTTP server. Pin
  Pyodide, Clang/LLD, the WASI sysroot, and the runner. Record versions,
  checksums, and redistribution notices. Use the tested YoWASP Clang
  package as the baseline and verify its update path after the upstream
  move to Codeberg. [Pyodide workers](https://pyodide.org/en/stable/usage/webworker.html) ·
  [YoWASP Clang](https://codeberg.org/YoWASP/clang)
- [x] Load the compiler in a worker and stage each build in its own
  virtual workspace. Reuse the browser target policy and include
  resolver. Preserve case-sensitive paths, nested includes, linked
  routines, and source-located diagnostics.
- [x] Compile C99 with the WASI C library, including long-double
  formatting. Add a prefilled stdin path that avoids POSIX terminal
  APIs. Verify input, EOF, stderr and exit status against native fixtures.
- [x] Run generated Wasm in a separate, disposable worker inside a
  sandboxed iframe. Give it only the WASI imports needed for the
  playground, including standard streams and the supported clock and
  random functions. Keep project storage, browser APIs, and the network
  outside the runner. Verify **Stop** during loading, compilation, and
  execution, and keep limits on source expansion, runtime, memory, and
  output.
- [x] Run the playground suite against the static build. Check Hello,
  Fibonacci, Factorial, Rule 110, Status lookup, syntax errors,
  unsupported operations, and stdin. Check cold and warm runs on
  Chromium, Firefox, and WebKit, including iPhone emulation. After
  loading the toolchain, run a new program with the network disconnected.

Run `just playground-static` and open <http://127.0.0.1:18766/> for the
local build. The [playground README](playground/README.md) has test commands.

## 2. Store projects locally and export existing cloud saves

- [x] Keep the existing browser draft key and use IndexedDB for named
  projects. Reuse the **Projects** picker. Selecting a name fills the
  input, **Load** confirms before replacing the draft, and **Save**
  stores the name and project. Debounce draft and named autosaves.
  Show storage failures and conflicting edits in the editor.
- [x] Define a versioned JSON file format and implement **Export** and
  **Import**. Round-trip the project name, source paths and contents,
  main file, linked routines, and prefilled stdin where present. Validate
  imports before applying them and ask before overwriting a saved name
  or replacing the current draft.
- [x] Add the same **Export** format to the hosted editor so signed-in
  users can download their Firestore saves. Verify the export against
  the local hosted stack. Explain browser storage and backups in help.
- [ ] Publish the export feature on the live hosted editor, check the
  signed-in export and import across browser profiles, and give pilot
  users a date by which to export before cutover.
- [x] Remove OAuth, quota, and cloud project requests from the static
  build. Update the help dialog and local development instructions.
  Verify that a fresh visitor can use the examples, run code, and
  save and load a project without signing in.

## 3. Choose the host and switch the domain

**Start with GitHub Pages.** The public `jbc-lang/jbcc` repository has
Pages disabled today. The separate `jbc-lang/jbc-language` repository
already serves `jbc-lang.org`. GitHub Pages supports a repository-specific
custom subdomain and HTTPS. Its published site limit is 1 GB and its
soft bandwidth limit is 100 GB per month. The tested assets fit within
the site limit, and the compiler download will be the main bandwidth cost.
[GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) ·
[Custom domains](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)

A check of Derle’s published compiler on GitHub Pages returned HTTP 200,
`Content-Type: application/wasm`, and gzip encoding. Verify these on
our own deployment too. [Derle’s published Clang Wasm](https://senolgulgonul.github.io/derle/toolchain/clang.wasm)

**Use static Vercel hosting if the browser tests show we need custom
response headers.** Pages is suitable if the runner can keep its isolation
with an iframe sandbox and a static CSP. A CSP meta tag can restrict
connections, but `frame-ancestors` and the CSP `sandbox` directive need
response headers. Vercel can set these and COOP/COEP per path. If using
Vercel, test the deployment method and plan limits for the pinned assets.
The raw compiler and Python payloads already exceed the documented
100 MB Hobby CLI upload limit.
[CSP delivery rules](https://www.w3.org/TR/CSP3/#meta-element) ·
[Vercel headers](https://vercel.com/docs/project-configuration/vercel-json#headers) ·
[Vercel limits](https://vercel.com/docs/limits#static-file-uploads)

- [ ] Build and publish a GitHub Actions Pages artifact from the
  playground sources, with versioned toolchain paths. Test the default
  repository URL and its path prefix before assigning the custom domain.
  Check asset MIME types, compression and cache reuse. Run the sandbox
  tests with Pages’ actual headers, including attempts by the program
  runner to access browser storage or fetch over the network. Switch
  to the Vercel preview if the checks require header control.
  [GitHub Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [ ] Check first load and execution on a physical mobile device before
  changing DNS.
- [ ] Move the existing cookieless Analytics frame to a separate static
  origin before retiring Firebase Hosting. Verify that one page view is
  recorded for the canonical playground URL and that the tag stays
  isolated from the editor. Update the tag-check page and runbook as
  needed.
- [ ] Verify the domain with the chosen host. For Pages, configure
  `online.jbc-lang.org` on the `jbcc` repository and change only the
  Squarespace `online` CNAME from `jbc-online.web.app` to
  `jbc-lang.github.io`. For Vercel, use the CNAME shown in its domain
  settings. Keep the existing hostname so drafts from the live site
  remain accessible. Verify DNS, HTTPS, browser runs, and storage after
  cutover. Finish the export window before switching DNS, or provide a
  tested legacy export URL that can still sign in and load cloud saves.
  Keep the Firebase mapping and prior revision available for rollback
  until cutover checks pass.
  [GitHub domain verification](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages) ·
  [Vercel custom domains](https://vercel.com/docs/domains/working-with-domains/add-a-domain)

## 4. Decommission the GCP deployment

- [ ] Reconcile the live inventory and record the exact commands,
  console actions, and outcomes in [GCP.md](GCP.md). Confirm the static
  site is stable, the export window has closed, and the required cloud
  saves were exported before deleting Firestore data.
- [ ] Remove the old Firebase Hosting custom domain mapping and retire
  the playground and metrics Hosting sites. Disable Firebase GitHub
  sign-in and retire the dedicated **jBC Online** GitHub OAuth app
  after migration.
- [ ] Retire Cloud Run services `compiler` and `compiler-worker` in
  `europe-west2`, then remove the `jbc-playground` Artifact Registry
  repository, worker VPC/subnet/firewall, and dedicated service accounts
  and IAM bindings. After the data retention decision, remove the
  `jbc-playground` Firestore database and its build-quota records.
  Remove the dedicated playground spend cap and retain the shared
  billing account and account-wide alert.
- [ ] Verify that the static site has no dependency on `jbc-online`
  and confirm which project resources remain. Shut down the dedicated
  GCP project only after checking the inventory and receiving approval
  for deletion. Recheck public DNS, HTTPS, Analytics, and billing after
  cleanup. [Firestore database management](https://docs.cloud.google.com/firestore/native/docs/manage-databases) ·
  [Google Cloud project shutdown](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects#shutting_down_projects)
