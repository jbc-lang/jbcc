# Online jBC compiler

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
  diagnostic navigation. Replace assembly output with Build, Run, Stop,
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
- [ ] Add and verify an operator switch that pauses new playground builds.
  Confirm billing attribution and cap coverage after deployment. Spend
  cap enforcement can lag usage.
  [Spend cap scope](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
  [Cloud Run scaling limits](https://docs.cloud.google.com/run/docs/configuring/max-instances).

## 3. Add invite-only GitHub sign-in, rate limits, and Firestore saves

- [ ] Enable Firestore and Firebase Authentication after confirming the
  database location in the dedicated project. Configure GitHub OAuth
  for sign-in only. Request no repository scopes and keep GitHub access tokens out of playground storage.
  [Firebase GitHub sign-in](https://firebase.google.com/docs/auth/web/github-auth).
- [ ] Verify Firebase ID tokens in the Go API. Admit only GitHub accounts on
  the pilot allowlist. Use stable provider account IDs for the allowlist,
  and the verified Firebase UID for project ownership and rate limits.
  Test that a signed-in GitHub user outside the allowlist cannot build or
  access cloud saves. Anonymous users can edit local drafts.
  [Verify Firebase ID tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens).
- [ ] Store private projects at `users/{uid}/projects/{id}`. Save paths,
  source text, entry file, units and a revision number. Enforce ownership
  and size limits on every API read or write. Show conflicts between tabs
  instead of silently overwriting a newer revision.
  [Firestore storage limits](https://firebase.google.com/docs/firestore/quotas).
- [ ] Enforce shared rate limits across API instances using the verified
  user ID. Start with one in-flight build and six builds per minute per
  user. Cap the worker at one request per instance and two instances.
  Return `429` with `Retry-After` when capacity or a user's quota is
  exhausted. Test repeated requests against multiple API instances.
- [ ] Test that the production configuration requires authentication and
  rate limits. Ensure the production service rejects local mode.

## 4. Deploy and verify the pilot

- [x] Verify DNS for `online.jbc-lang.org`. It has no A or CNAME record.
  The parent domain uses Squarespace DNS.
- [ ] Build Docker images for the Go service and private compiler worker.
  Publish them to Artifact Registry in the dedicated project and deploy by
  image digest. Use separate runtime identities for `compiler` and
  `compiler-worker`. Restrict worker egress and give the worker no access
  to OAuth credentials, Firestore, or saved projects.
  [Cloud Run container isolation](https://docs.cloud.google.com/run/docs/container-contract).
  [Artifact Registry image names](https://docs.cloud.google.com/artifact-registry/docs/docker/names).
- [ ] Attach `online.jbc-lang.org` to the Go service through a supported
  HTTPS front door, with Firebase Hosting as the first option. Follow
  its DNS wizard in Squarespace. Use a CNAME if the mapping supplies one.
  If a literal CNAME is required, verify the chosen mapping supports it
  before changing DNS. Add the OAuth callback and authorized domain.
  [Cloud Run custom-domain options](https://docs.cloud.google.com/run/docs/mapping-custom-domains).
- [ ] Add a Google Analytics 4 web tag to the playground page. Configure
  its data stream and verify page views in Realtime. Keep source code,
  filenames, compiler output, and account IDs out of analytics.
  [GA4 setup](https://support.google.com/analytics/answer/14183469).
- [ ] Verify HTTPS, invite-only access, the three-file browser example,
  project save and reload, and diagnostics pointing to the correct tab.
  Exercise quota, oversized input, cancellation, and unsupported runtime
  paths in the deployed environment.
- [ ] Record actual build time and resource usage. Confirm billing reports
  attribute the deployment to the dedicated project, alerts cover it,
  and the operator can pause builds independently. Open access to invited
  users after these checks pass.
