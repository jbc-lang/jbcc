# Online jBC compiler

This records the original Cloud Run pilot. The current playground is
the browser-only GitHub Pages build described in [WASM-PLAN.md](WASM-PLAN.md).

Build a multi-file playground at `https://online.jbc-lang.org/`. The Go
service `compiler` serves the editor and API on Cloud Run. A private
`compiler-worker` runs jbcc and Emscripten. The browser runs the resulting
WebAssembly. Deploy to `jBC Online` (project ID `jbc-online`) under the
existing billing account. See [GCP.md](GCP.md) for commands and console
actions.

The browser runtime supports a documented subset of jBC. Start with
non-interactive console programs, arithmetic, arrays, includes, and linked
routines. An operation that needs an unavailable host service should report
a diagnostic or a documented limitation. Examples include shell execution,
terminal devices, and jBASE or T24 backends.

## 1. Build and test the playground locally

Finish the browser-to-compiler flow on one machine before creating cloud
resources. The local stack runs the same Go API and compiler worker used
for deployment. Verified from a fresh checkout without Google Cloud
credentials. See the [local playground guide](playground/README.md) to run
the stack and its tests.

### Prove multi-file jBC to WebAssembly

- [x] Verify that the existing caller/subroutine pair shares an
  `$INSERT I_STATUS` file and translates to valid C99. The native program
  prints `open` and `closed`.
- [x] Build a local Linux Docker image with pinned jbcc and Emscripten
  versions. Compile `hello.b` and the three-file caller example through
  `jbcc → C → emcc → Wasm`. Compare browser stdout, stderr, and exit status
  with the native fixtures.
- [x] Introduce a browser target policy for supported runtime operations.
  Report unsupported operations with source locations when possible.
  Verify a program using one unavailable feature and document its result.
  Add compatibility tests as features become available.
- [x] Define project files by case-sensitive relative paths. Pick one main
  program and list additional units separately. Use jBC's `$INSERT` and
  `$INCLUDE` directives for include files and resolve names relative to
  the including file, then the project root.
- [x] Pass a workspace-restricted include resolver through jbcc's
  multi-file compile path. Test nested and shared includes, missing files,
  cycles, attempts to escape the project root, and repeated expansion.
  Preserve project-relative paths, lines and columns in diagnostics.
- [x] Generate an Emscripten module and run it in a worker in an isolated
  browser runner. Capture stdout and stderr, pass prefilled stdin, and
  make Stop terminate the worker. Verify that a running program cannot
  access the editor's credentials or storage. Add an execution timeout,
  output limit, and a WebAssembly memory limit.
  [Emscripten modularized output](https://emscripten.org/docs/compiling/Modularized-Output.html).

### Build the Go API and port the editor

- [x] Adapt the HTML, CSS, and TypeScript from `../asm8/docs`. Reuse the
  editor tabs, main-file selector, local drafts, examples, theme, and
  diagnostic navigation. Replace assembly output with Run, Stop,
  and a console. Let users choose auxiliary source units and include files.
- [x] Serve the bundled UI and versioned API on the same origin. Define
  `POST /api/v1/compile` with `entry`, `units`, and `files`. Return structured
  diagnostics and bounded JS/Wasm artifacts. Keep artifact downloads private
  to the requesting user, with short lifetimes if served separately.
- [x] Run the compiler worker behind the Go API with fixed tool arguments
  and a fresh workspace for each request. Keep the worker unreachable
  from the browser. Verify request isolation and cleanup.
- [x] Enforce request, include-expansion, time, and output limits before
  accepting untrusted builds. Reject unsafe paths and duplicate filenames.
  Cancel the compiler subprocesses and clean up the workspace on failure,
  cancellation, or timeout. Return `413` for oversized requests.
- [x] Provide one command to start the bundled editor, Go API, and
  compiler worker locally. Bind the published port to loopback. Allow
  builds without GitHub sign-in or per-user rate limiting in explicit
  local mode. Use browser storage for local drafts and keep request size,
  workspace, build timeout, and output limits active.
- [x] Test locally from a fresh checkout without cloud credentials. Open
  the editor, build and run `hello.b` and the three-file example, reload a
  draft, and verify output, source-linked diagnostics, rejected oversized
  requests, cancellation, and recovery on the next build.

Initial build limits to verify locally and tune during the pilot:

| Limit | Starting value |
| --- | --- |
| Files per project | 32 |
| UTF-8 source per file / project | 64 KiB / 256 KiB |
| HTTP request body | 512 KiB |
| Expanded include depth / source | 16 levels / 1 MiB |
| Build time / artifacts | 15 seconds / 4 MiB |

## 2. Set up the jBC Online project and cost controls

- [x] Verify in the Cloud Billing console that the intended billing
  account has an account-wide alert.
- [x] Choose `jBC Online` as the display name and `jbc-online` as the
  project ID.
- [x] Verify that `gcloud` is installed and the intended Google Cloud
  account can authenticate.
- [x] Create `jbc-online` with display name `jBC Online` and verify the
  project is active.
- [x] Link `jbc-online` to the existing billing account and verify the
  link.
- [x] Configure a £1 monthly Cloud Run spend cap scoped to `jbc-online`.
  Verify its **Configured** state and the intended owner's and billing
  administrator's eligibility for notifications.
- [x] Verify the existing all-projects, all-services alert covers
  `jbc-online`, including Firestore, Hosting or the load balancer,
  Artifact Registry, logs, and network charges.
- [x] Record the Cloud Run pilot settings in [GCP.md](GCP.md). Use
  request-based billing, zero minimum instances, and at most two
  instances per service.
- [x] Add and verify locally that `JBCC_BUILDS_ENABLED=false` pauses
  new builds while the editor and health endpoint stay available.
- [x] Verify the deployed pause switch, project billing link, and
  Cloud Run spend cap. Spend cap enforcement can lag usage.
  [Spend cap scope](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
  [Cloud Run scaling limits](https://docs.cloud.google.com/run/docs/configuring/max-instances).

## 3. Add invite-only GitHub sign-in, rate limits, and Firestore saves

- [x] Enable the service APIs and provision the Docker repository, web
  and worker service accounts, and the Firestore database in
  `europe-west2`.
- [x] Link Firebase to the project and register the `jBC Online` web app.
- [x] Initialize Firebase Authentication and configure the GitHub
  provider with the OAuth app owned by `jbc-lang`. Request no repository
  scopes and keep GitHub access tokens out of playground storage.
  [Firebase GitHub sign-in](https://firebase.google.com/docs/auth/web/github-auth).
- [x] Require Firebase ID tokens and an approved GitHub account ID before
  compiling or accessing cloud saves. Use the verified Firebase UID for
  ownership and rate limits. Verify that uninvited identities cannot
  reach the compiler. Anonymous users can edit local drafts.
  [Verify Firebase ID tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens).
- [x] Save private projects at `users/{uid}/projects/{id}`. Enforce
  ownership and size limits. Verify with two Firestore clients that
  stale revisions raise conflicts and each user has private storage.
  [Firestore storage limits](https://firebase.google.com/docs/firestore/quotas).
- [x] Enforce one in-flight build and six build starts per rolling minute
  per user. Return `429` with `Retry-After`. Verify shared leases and
  rate limits with two clients against the London Firestore database.
- [x] Test locally that production requires authentication and rate
  limits and that Cloud Run rejects local mode.
- [x] Verify an invited GitHub sign-in and cloud saves end to end at
  the deployed HTTPS origin.
- [ ] Verify a signed-in, uninvited GitHub account end to end on the
  deployed site. The API test already verifies denial.

## 4. Deploy and verify the pilot

- [x] Publish AMD64 Docker images to Artifact Registry and deploy both
  services by digest in London. Verify that the worker requires Cloud
  Run IAM and has an active egress-deny rule on its dedicated VPC.
  [Cloud Run container isolation](https://docs.cloud.google.com/run/docs/container-contract).
- [x] Connect `online.jbc-lang.org` to Firebase Hosting through the
  Squarespace CNAME. Confirm HTTPS and the Cloud Run rewrite.
  [Firebase custom domains](https://firebase.google.com/docs/hosting/custom-domain).
- [x] Load the supplied `GTM-5QTPTVWF` container automatically in a frame
  on a separate origin. Verify that GA4 accepts a cookieless `page_view`.
- [x] Publish a top-level `/tag-check.html` page for the Google tag
  installation check.
- [ ] Confirm the resulting event in GA4 Realtime.
- [x] Verify live sign-in, the multi-file browser example, cloud save and
  load, anonymous build rejection, and oversized request rejection.
- [x] Verify diagnostic navigation, the Stop button, and build quota
  rejection through the hosted editor.
- [x] Record observed build times and memory use. Open builds to the
  initial GitHub allowlist after the deployment checks.
