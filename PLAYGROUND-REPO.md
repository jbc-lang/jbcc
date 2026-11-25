# Move the jBC playground to its own repository

Move `online.jbc-lang.org` to `jbc-lang/jbc-playground`. Keep the
compiler, C runtime, native CLI, compiler tests, and PyPI packaging in
`jbc-lang/jbcc`. Release the playground and compiler independently.

## Publishing source

Set **Settings → Pages → Build and deployment → Source** to **GitHub Actions**
in `jbc-playground`. Keep the source and workflow on `main`. On a push to
`main`, build and test the playground, then deploy the generated
`dist/playground/` directory as a Pages artifact. Run the build and tests
on pull requests too.

Publishing from the root of `main` or from `main:/docs` would require
checking the built site and toolchain into the source branch. A dedicated
`gh-pages` branch could hold generated files, but adds a branch to manage
and a second publishing step. GitHub Actions fits the existing build and
keeps generated assets out of Git history.
[Pages publishing sources](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

## 1. Release the compiler dependency

- [x] Define and document the [Python interface](README.md#browser-translation-api)
  the playground needs. Cover multi-file translation, browser-target
  diagnostics, include resolution and limits, and access to the packaged C
  runtime. Keep the JSON request adapter and playground-specific policies
  in the playground repo.
- [x] Build a release candidate wheel and test the browser adapter against
  the installed package in Pyodide. Include a single-file program, a
  linked routine with a shared include, and a source-located diagnostic.
- [x] Publish the tested `jbcc` release to PyPI. Version `0.2.0` includes
  the browser translation API and the packaged C runtime. The uploaded
  wheel passed native CLI and Pyodide checks.
  [jbcc 0.2.0 on PyPI](https://pypi.org/project/jbcc/0.2.0/) ·
  [Pyodide package loading](https://pyodide.org/en/stable/usage/loading-packages.html)

## 2. Build the standalone playground

- [x] Move the editor, Python adapter, browser workers, toolchain,
  examples, browser tests, and notices to
  [jbc-lang/jbc-playground](https://github.com/jbc-lang/jbc-playground).
  The new repository has its own local build and test commands.
- [x] Pin the PyPI wheel for `jbcc 0.2.0` and verify its SHA-256 at build
  time. The browser loads the published asset on the first **Run**, and
  native test comparisons use the same wheel.
- [x] Preserve localStorage keys, the IndexedDB schema, and the project
  JSON format. The existing browser limits and Wasm runner sandbox are
  covered by the standalone browser suite.
- [x] Publish the [GitHub Pages preview](https://jbc-lang.github.io/jbc-playground/).
  All 32 browser tests passed locally and in Actions. On the live preview,
  single-file and multi-file runs, project import and export, and offline
  execution passed. The editor fetched neither Wasm nor the wheel until
  the first **Run**, and the wheel matched the pinned SHA-256.
  [Preview deployment](https://github.com/jbc-lang/jbc-playground/actions/runs/45670092625)

## 3. Put the Google tag in the served HTML

- [x] Embed `gtag.js` for playground stream `G-NCPVZT08XG` in the
  standalone production `index.html`. The Actions variable
  `JBCC_ENABLE_ANALYTICS=1` enables it for the main-branch artifact. The
  script checks the production origin. Local and preview builds omit
  the tag by default.
- [x] Set denied Analytics and advertising consent before sending one
  explicit page view for the canonical URL. Suppress the automatic page
  view and verify that user-provided data collection is disabled in the
  published Google tag configuration.
- [x] Verify the browser traffic with sample project names, filenames,
  source, input, and output. The direct tag runs in the editor's origin
  and can access its DOM and storage. The Wasm runner remains sandboxed.
  The tag skips URLs with query strings because GA4 Enhanced Measurement
  can collect search terms from them.
- [x] Test the production artifact at the canonical origin in a test
  browser before cutover. The test observed one cookieless page view
  with an HTTP 204 from GA4, zero cookies, and zero requests to
  `playground-metrics`. The preview remains Analytics-free.
  [Google tag setup](https://developers.google.com/tag-platform/gtagjs) ·
  [Google consent defaults](https://developers.google.com/tag-platform/security/guides/consent)

## 4. Transfer the domain and retire the old deployment

- [x] Save a multi-file project in a dedicated browser profile before
  cutover. Set `JBCC_ENABLE_ANALYTICS=1` in the new repository and verify
  the staged HTML and pinned wheel before assigning the domain.
  [Production deployment](https://github.com/jbc-lang/jbc-playground/actions/runs/45672286013)
- [x] Transfer the Pages custom domain from `jbcc` to
  `jbc-playground`. The Squarespace CNAME still points to
  `jbc-lang.github.io`. The new binding serves HTTPS and redirects HTTP.
  [GitHub Pages custom domains](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [x] Reopen the saved project in the same browser profile and run both
  Hello and the linked-routine example on the live domain. Export and
  reimport the project. Verify that GA4 accepts one cookieless page view
  from the direct tag for the canonical URL.
- [x] Remove the old playground sources and Pages workflow from `jbcc`
  and unpublish its Pages site. Link to the standalone repo and live site.
- [x] Unpublish the `playground-metrics` Pages site and archive its
  repository. Keep the existing GA4 property and stream and record the
  old Tag Manager container in [ANALYTICS-TAGS.md](ANALYTICS-TAGS.md).

### Rollback record

The [last jbcc deployment](https://github.com/jbc-lang/jbcc/actions/runs/45668656419)
was built from `20de795`. The [final jbcc checkout with the playground](https://github.com/jbc-lang/jbcc/tree/eb4221a)
also includes the migration notes. To restore that deployment after
cleanup, restore the playground sources and workflow from that checkout
and re-enable GitHub Actions for Pages in `jbcc`. Unarchive
`playground-metrics` and republish its `main` branch root if the
previous Analytics setup is needed.

Once the old artifact works at its default Pages URL, clear the custom
domain from `jbc-playground`, attach it to `jbcc`, and verify HTTPS and
a browser run. Both the transfer and rollback use the same DNS record.
