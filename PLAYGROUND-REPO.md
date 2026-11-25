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
  diagnostics, include resolution
  and limits, and access to the packaged C runtime. Keep the JSON request
  adapter and playground-specific policies in the playground repo.
- [x] Build a release candidate wheel and test the browser adapter against
  the installed package in Pyodide. Include a single-file program, a
  linked routine with a shared include, and a source-located diagnostic.
- [ ] Publish the tested `jbcc` release to PyPI. The current `0.1.0` wheel
  includes `jbc.c` but predates the browser translation support on `main`.
  Verify the uploaded wheel through both the native CLI and Pyodide.
  [jbcc on PyPI](https://pypi.org/project/jbcc/) ·
  [Pyodide package loading](https://pyodide.org/en/stable/usage/loading-packages.html)

## 2. Build the standalone playground

- [ ] Create `jbc-lang/jbc-playground`. Move the editor, Python adapter,
  browser workers, Wasm toolchain configuration, examples, Playwright
  tests, and applicable licenses and notices. Give the repo its own local
  build and test commands. Keep compiler test fixtures with `jbcc`.
- [ ] Pin the PyPI version and wheel SHA-256. Have the build download and
  verify the wheel, then copy it into the static artifact. Load it from
  that artifact on the first **Run**. Use the same pin when browser tests
  compare results against the native CLI.
- [ ] Preserve localStorage keys, IndexedDB database and schema, and the
  project JSON format. Keep existing browser limits, editor behavior, and
  runtime isolation through the move.
- [ ] Enable the Pages workflow and verify the site at its default
  `github.io` URL, including asset paths under the repository prefix.
  Run the full browser suite. Verify the cold first run and confirm that
  opening the editor still fetches no Wasm.

## 3. Put the Google tag in the served HTML

- [ ] Embed the direct Google tag (`gtag.js`) for the existing playground
  stream `G-NCPVZT08XG` in the production `index.html`. Enable it only in
  the production build. The production page will use a single tag and
  remove the old Tag Manager iframe and its loader.
- [ ] Keep the cookieless page view. Set denied Analytics and advertising
  consent defaults before measurement, suppress automatic page views,
  and send one explicit page view with the canonical playground URL.
  Keep user-provided data collection disabled.
- [ ] Review the tag configuration and verify that its requests carry
  no project contents, filenames, names, input, or output. The direct
  Google script runs in the editor's page and has access to its DOM and
  same-origin browser storage. This change removes the iframe's
  isolation for Analytics. Keep the Wasm runner sandbox in place.
- [ ] Test the rendered production HTML before cutover. Verify that GA4
  accepts one cookieless page view for `https://online.jbc-lang.org/`,
  that no Analytics cookies appear, and that there are no requests to
  `playground-metrics`. Verify default preview and local builds omit
  Analytics.
  [Google tag setup](https://developers.google.com/tag-platform/gtagjs) ·
  [Google consent defaults](https://developers.google.com/tag-platform/security/guides/consent)

## 4. Transfer the domain and retire the old deployment

- [ ] Record the current working deployment and the rollback steps.
  Before the transfer, save a test project at the production URL in a
  dedicated browser profile for the storage continuity check.
- [ ] Remove the `online.jbc-lang.org` custom domain from `jbcc` Pages
  and immediately assign it to `jbc-playground` Pages. Keep the
  Squarespace CNAME targeting `jbc-lang.github.io`. Verify HTTPS and
  canonical routing. If cutover fails, reassign the domain to the old
  Pages deployment and verify it serves the previous site.
  [GitHub Pages custom domains](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
- [ ] On the live domain, compile and run single-file and multi-file
  examples, reopen the saved project in the same browser profile,
  exercise JSON import and export, and verify the GA4 page view again.
- [ ] Remove playground source and the Pages workflow from `jbcc` after
  the new deployment passes. Keep links to the live site and the new
  repo, and update the Analytics and deployment notes.
- [ ] Once the direct tag is verified and the old site is no longer in use,
  retire `jbc-lang/playground-metrics`. Keep the existing GA4 property and
  stream. Record the retired Tag Manager container in the tag inventory.
