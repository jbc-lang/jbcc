# GCP deployment archive

The [standalone playground](https://github.com/jbc-lang/jbc-playground) is
hosted on GitHub Pages at `https://online.jbc-lang.org/`. The sections below
record the former Cloud Run and Firebase deployment in **jBC Online** (`jbc-online`).
The original deployment checklist is in [ONLINE-COMPILER.md](ONLINE-COMPILER.md).

## Retirement

On 2026-11-25 the browser-only playground replaced the Cloud Run editor.
During that migration the Analytics frame moved from Firebase Hosting
to GitHub Pages. The frame has since been retired as part of the
[standalone repository cutover](PLAYGROUND-REPO.md). The
browser test compiled and ran two projects, reloaded a named save, and
observed a cookieless GA4 page view with HTTP 204 while blocking Firebase
and Cloud Run requests. The Squarespace CNAME still points to
`jbc-lang.github.io`.

The final `jbc-online` inventory included the Cloud Run services
`compiler` and `compiler-worker`, the Firestore database and Artifact
Registry repository both named `jbc-playground`, Firebase Authentication,
and Hosting sites `jbc-online` and `jbc-online-metrics`. The Firebase
custom domain binding belonged to the old site. There were no Cloud
Storage buckets or BigQuery datasets and no cloud saves to migrate.

The General billing account had a dedicated £1 Cloud Run spend cap
for `jbc-online`, with alerts at 50%, 80%, and 100%. The £0.50 overall
alerts-only policy covers all projects and services, with thresholds
at 50%, 90%, and 100%. Only the dedicated cap was removed. A before
and after Budget API comparison verified that all four other policies
on the account were unchanged.

```sh
gcloud billing budgets list --billing-account="$JBCC_BILLING_ACCOUNT" \
  --billing-project=jbc-online --account="$JBCC_ACCOUNT"
gcloud billing budgets delete 193c5d12-262c-43ba-9173-f0eabe9debf7 \
  --billing-account="$JBCC_BILLING_ACCOUNT" --billing-project=jbc-online \
  --account="$JBCC_ACCOUNT"
gcloud projects delete jbc-online --account="$JBCC_ACCOUNT"
gcloud projects describe jbc-online --account="$JBCC_ACCOUNT" \
  --format='value(lifecycleState)'
gcloud billing projects describe jbc-online --account="$JBCC_ACCOUNT" \
  --format='value(billingEnabled)'
```

Google Cloud reported `DELETE_REQUESTED` and billing disabled. Google
Cloud schedules permanent deletion after its 30-day recovery period.
Project shutdown covers Firebase Hosting, Firebase Authentication, and
the other project-owned resources. The Firebase Hosting API reported
that the project had been deleted. The old public endpoints still
responded in the first minutes after shutdown. The live playground
passed its browser checks again after shutdown.

The [live Analytics configuration](ANALYTICS-TAGS.md) continues to use
the same GA4 stream. The old GitHub OAuth
application is registered separately in GitHub.
[Google Cloud project shutdown](https://docs.cloud.google.com/resource-manager/docs/delete-restore-projects) ·
[Cloud Billing spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

## Historical deployment inventory

- The existing billing account has an all-projects, all-services alert
  that covers `jbc-online`.
- The `jbc-online` project has its own £1 monthly Cloud Run spend cap.
  The Budget API reports it as **Configured**.
- Squarespace hosts DNS for `jbc-lang.org`. The `online` CNAME points
  to `jbc-lang.github.io`.

Set `JBCC_ACCOUNT` to the intended Google Cloud account. Use London
(`europe-west2`) for Cloud Run, Artifact Registry, and Firestore.
[Firestore locations](https://docs.cloud.google.com/firestore/native/docs/locations).
[Firebase Hosting rewrites to Cloud Run](https://firebase.google.com/docs/hosting/cloud-run).

```sh
gcloud auth list
gcloud billing accounts list --account="$JBCC_ACCOUNT"
dig +short jbc-lang.org NS
dig +short online.jbc-lang.org CNAME
dig +short online.jbc-lang.org A
```

## Create the project and set its budgets

Complete the [local playground milestone](ONLINE-COMPILER.md#1-build-and-test-the-playground-locally)
before running the provisioning commands.

`jbc-online` was created and linked to billing on 2026-11-25. These
commands record the setup. Set `JBCC_BILLING_ACCOUNT` to the intended
account ID. Google Cloud project IDs are globally unique.
[Project IDs](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects).

```sh
JBCC_PROJECT=jbc-online
JBCC_PROJECT_DISPLAY_NAME="jBC Online"

gcloud projects create "$JBCC_PROJECT" --name="$JBCC_PROJECT_DISPLAY_NAME" \
  --account="$JBCC_ACCOUNT" --no-enable-cloud-apis

gcloud billing projects link "$JBCC_PROJECT" \
  --billing-account="$JBCC_BILLING_ACCOUNT" --account="$JBCC_ACCOUNT"

gcp() {
  gcloud --project="$JBCC_PROJECT" --account="$JBCC_ACCOUNT" "$@"
}

gcp projects describe "$JBCC_PROJECT" --format='table(projectId,name,lifecycleState)'
gcp billing projects describe "$JBCC_PROJECT"
gcp services enable billingbudgets.googleapis.com
gcp billing budgets list --billing-account="$JBCC_BILLING_ACCOUNT" \
  --billing-project="$JBCC_PROJECT"
```

The existing alerts-only budget covers all projects and services on the
account. It alerts the default billing recipients at 50%, 90%, and 100%
of its £0.50 budget. The intended account holds the Billing Account
Administrator role and owns `jbc-online`.

The dedicated **jBC Online Cloud Run spend cap** covers Cloud Run usage
for both planned playground services. The cap posts notifications to
billing administrators and project owners at 50%, 80%, and 100%.
Firestore, Artifact Registry, and other services fall under the
account-wide alert. Spend cap enforcement can lag usage.
[Cloud Billing spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
[Budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).

The cap was created with `POST /v1/billingAccounts/{account_id}/budgets`
at `billingbudgets.googleapis.com` using the `x-goog-user-project` value
`jbc-online`. Use the numeric project number in the project filter.
Check for a matching cap before creating one. Verify **Configured** in
Billing → Budgets and caps or check `spendCap.outputState` with the
Budget API.
[Create a budget](https://docs.cloud.google.com/billing/docs/reference/budget/rest/v1/billingAccounts.budgets/create).

```json
{
  "displayName": "jBC Online Cloud Run spend cap",
  "budgetFilter": {
    "projects": ["projects/{project_number}"],
    "services": ["services/152E-C115-5142"],
    "calendarPeriod": "MONTH",
    "creditTypesTreatment": "EXCLUDE_ALL_CREDITS"
  },
  "amount": {"specifiedAmount": {"currencyCode": "GBP", "units": "1"}},
  "thresholdRules": [
    {"thresholdPercent": 0.5, "spendBasis": "CURRENT_SPEND"},
    {"thresholdPercent": 0.8, "spendBasis": "CURRENT_SPEND"},
    {"thresholdPercent": 1, "spendBasis": "CURRENT_SPEND"}
  ],
  "notificationsRule": {"enableProjectLevelRecipients": true},
  "spendCap": {"inputState": "CONFIGURED"}
}
```

## Enable APIs and provision service identities

The APIs, empty Docker repository, runtime service accounts, and
Firestore database below were provisioned in `jbc-online`. Firestore is
in Native mode with deletion protection enabled. The web service account
has database-scoped access. The worker has no direct project role.

```sh
JBCC_REGION=europe-west2
gcp services enable run.googleapis.com artifactregistry.googleapis.com \
  compute.googleapis.com firestore.googleapis.com firebase.googleapis.com \
  identitytoolkit.googleapis.com
gcp artifacts repositories create jbc-playground \
  --repository-format=docker --location="$JBCC_REGION"
gcp iam service-accounts create compiler-web
gcp iam service-accounts create compiler-worker
JBCC_WEB_SA="compiler-web@$JBCC_PROJECT.iam.gserviceaccount.com"
JBCC_WORKER_SA="compiler-worker@$JBCC_PROJECT.iam.gserviceaccount.com"
```

Grant the deployment identity Artifact Registry write access on the
repository, Cloud Run deployment access, and Service Account User on
the runtime identities. Use an unprivileged identity for the compiler
worker. Keep OAuth credentials in Firebase's provider configuration.

```sh
gcp firestore databases create --database=jbc-playground \
  --location="$JBCC_REGION" --type=firestore-native --delete-protection
gcp projects add-iam-policy-binding "$JBCC_PROJECT" \
  --member="serviceAccount:$JBCC_WEB_SA" --role=roles/datastore.user \
  --condition="expression=resource.name==\"projects/$JBCC_PROJECT/databases/jbc-playground\",title=JbcPlaygroundDatabase"
```

Firebase was linked and the web app **jBC Online** was created with
`projects.addFirebase` and `projects.webApps.create` in the Firebase
Management API. The web app config was verified with
`projects.webApps.getConfig`.
[Firebase Management API](https://firebase.google.com/docs/reference/firebase-management/rest/v1beta1/projects).
[Firestore database IAM](https://docs.cloud.google.com/firestore/docs/manage-databases).

Firebase Authentication was initialized with **Get started** in the
Firebase console and verified as standard Firebase Authentication.
The `jbc-lang` organization owns the GitHub OAuth app **jBC Online**.
It uses homepage `https://online.jbc-lang.org/` and the exact redirect
`https://jbc-online.firebaseapp.com/__/auth/handler`. The GitHub provider
was configured with `projects.defaultSupportedIdpConfigs.create`, and
`online.jbc-lang.org` was added through `projects.updateConfig` with the
`authorizedDomains` field mask. The OAuth secret is stored in Firebase's
provider configuration. A Firebase-generated GitHub authorization URL
confirmed that no repository scopes were requested.
[Firebase GitHub provider](https://firebase.google.com/docs/auth/web/github-auth).
[Identity Platform configuration API](https://docs.cloud.google.com/identity-platform/docs/reference/rest/v2/projects/updateConfig).

The Go API checks Firebase ID tokens and the numeric GitHub account
allowlist before compiling or accessing saves. It uses the Firebase UID
for Firestore document ownership and build quotas. Each account can have
one build in flight and six build starts in a rolling minute. Saved
projects at `users/{uid}/projects/{id}` use revisions to detect conflicts.
The project picker lists document IDs from the signed-in user's
collection through `GET /api/v1/projects`.

## Publish Docker images and deploy Cloud Run

Both Cloud Run services ran in `europe-west2`. The initial pilot
allowlist contained `begoon`. The services used request-based billing
with zero minimum and two maximum instances per service.

| Service | Final revision | Build commit | Image digest |
| --- | --- | --- | --- |
| `compiler` | `compiler-00007-b8w` | `84448da` | `sha256:0841254fc6f9476a137072e910bea310908bfce27879d24f83b2297406501883` |
| `compiler-worker` | `compiler-worker-00001-lcj` | `e2b548e` | `sha256:5aacef622639080285a4956eed86f1a49a307e6ecf8d1fa8d878dd17ea858d79` |

The web update added **Export** for cloud saves. The worker continued
serving its existing revision. Firebase listed `jbc-online.web.app` as an
authorized sign-in domain during the migration window.

```sh
gcp run services update compiler --region="$JBCC_REGION" \
  --image=europe-west2-docker.pkg.dev/jbc-online/jbc-playground/compiler@sha256:0841254fc6f9476a137072e910bea310908bfce27879d24f83b2297406501883
```

Build Linux AMD64 images from the repository root. Record their digests
and toolchain versions.

```sh
JBCC_REGISTRY="$JBCC_REGION-docker.pkg.dev"
JBCC_IMAGE_ROOT="$JBCC_REGISTRY/$JBCC_PROJECT/jbc-playground"
JBCC_TAG=$(git rev-parse HEAD)
gcloud auth print-access-token --account="$JBCC_ACCOUNT" \
  | docker login -u oauth2accesstoken --password-stdin "$JBCC_REGISTRY"
docker buildx build --platform linux/amd64 --push \
  -f playground/Dockerfile.web -t "$JBCC_IMAGE_ROOT/compiler:$JBCC_TAG" .
docker buildx build --platform linux/amd64 --push \
  -f playground/Dockerfile.worker -t "$JBCC_IMAGE_ROOT/compiler-worker:$JBCC_TAG" .
gcp artifacts docker images describe "$JBCC_IMAGE_ROOT/compiler:$JBCC_TAG"
gcp artifacts docker images describe "$JBCC_IMAGE_ROOT/compiler-worker:$JBCC_TAG"
```

Set `JBCC_WEB_IMAGE` and `JBCC_WORKER_IMAGE` to the full
`@sha256:...` references. The worker uses the dedicated
`playground-worker` VPC and the `10.42.0.0/26` subnet, with all IPv4
egress denied by its network tag.
[Artifact Registry images](https://docs.cloud.google.com/artifact-registry/docs/docker/pushing-and-pulling).
[Cloud Run Direct VPC egress](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc).

```sh
JBCC_WORKER_CIDR=10.42.0.0/26
gcp compute networks create playground-worker --subnet-mode=custom
gcp compute networks subnets create playground-worker \
  --network=playground-worker --region="$JBCC_REGION" \
  --range="$JBCC_WORKER_CIDR" --stack-type=IPV4_ONLY
gcp compute firewall-rules create playground-worker-deny-egress \
  --network=playground-worker --direction=EGRESS --action=DENY \
  --rules=all --destination-ranges=0.0.0.0/0 --target-tags=playground-worker

gcp run deploy compiler-worker --region="$JBCC_REGION" \
  --image="$JBCC_WORKER_IMAGE" --service-account="$JBCC_WORKER_SA" \
  --no-allow-unauthenticated --cpu-throttling --min=0 --max=2 \
  --cpu=1 --memory=1Gi --concurrency=1 --timeout=25s \
  --network=playground-worker \
  --subnet=playground-worker --network-tags=playground-worker \
  --vpc-egress=all-traffic
gcp run services add-iam-policy-binding compiler-worker \
  --region="$JBCC_REGION" --member="serviceAccount:$JBCC_WEB_SA" \
  --role=roles/run.invoker

JBCC_WORKER_URL=$(gcp run services describe compiler-worker \
  --region="$JBCC_REGION" --format='value(status.url)')
```

Prepare an environment YAML file at `JBCC_COMPILER_ENV`. Copy the Firebase
web app's public configuration from Firebase project settings. Use
`gh api users/GITHUB_LOGIN --jq .id` to resolve each approved account to
its numeric ID. Quote the comma-separated list in the YAML file.

```yaml
JBCC_MODE: "production"
JBCC_BUILDS_ENABLED: "false"
JBCC_PUBLIC_ORIGIN: "https://online.jbc-lang.org"
JBCC_WORKER_URL: "PRIVATE_CLOUD_RUN_SERVICE_ORIGIN"
JBCC_FIREBASE_API_KEY: "FIREBASE_WEB_API_KEY"
JBCC_FIREBASE_AUTH_DOMAIN: "jbc-online.firebaseapp.com"
JBCC_FIREBASE_PROJECT: "jbc-online"
JBCC_FIREBASE_APP_ID: "FIREBASE_WEB_APP_ID"
JBCC_FIRESTORE_DATABASE: "jbc-playground"
JBCC_ALLOWED_GITHUB_IDS: "APPROVED_NUMERIC_GITHUB_IDS"
JBCC_ANALYTICS_ORIGIN: "https://jbc-online-metrics.web.app"
```

Replace `PRIVATE_CLOUD_RUN_SERVICE_ORIGIN` with `JBCC_WORKER_URL` from
the worker deployment. The web service uses its Cloud Run identity to
obtain the worker's identity token.

```sh
gcp run deploy compiler --region="$JBCC_REGION" \
  --image="$JBCC_WEB_IMAGE" --service-account="$JBCC_WEB_SA" \
  --allow-unauthenticated --cpu-throttling --min=0 --max=2 \
  --cpu=1 --memory=512Mi --timeout=30s --env-vars-file="$JBCC_COMPILER_ENV"
```

The API enforces the allowlist and quotas on the custom domain and the default
service URL. It uses a Cloud Run identity token to call the worker.
[Service-to-service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## Firebase Hosting and Analytics

Firebase Hosting served `https://jbc-online.web.app/` through a
catch-all rewrite to Cloud Run service `compiler` in `europe-west2`.
The main Hosting release is `sites/jbc-online/releases/1795609337836000`.
The Hosting API created a version with this rewrite and the static
`/tag-check.html` page, finalized it with `versions.patch`, and published
it with `releases.create`. The browser-only site also serves a
[/tag-check.html](https://online.jbc-lang.org/tag-check.html) page for the
Google tag installation check. It denies storage and advertising consent
and blocks collection through its content security policy. The static
build computes the SHA-256 hash of the inline initializer.

```json
{"config":{"rewrites":[{"glob":"**","run":{"serviceId":"compiler","region":"europe-west2"}}]}}
```

The original Firebase custom domain mapping was added with
`projects.sites.customDomains.create`. The former Squarespace record and
the current CNAME use a four-hour TTL.
[Custom domain setup](https://firebase.google.com/docs/hosting/custom-domain).

| Host | Type | Active target | Former target |
| --- | --- | --- | --- |
| `online` | CNAME | `jbc-lang.github.io` | `jbc-online.web.app` |

The Firebase Hosting site `jbc-online-metrics` served the isolated
Analytics frame before the move to GitHub Pages. Its final release was
`sites/jbc-online-metrics/releases/1795609330873000`. To publish the
frame, create a Hosting version, call `versions.populateFiles` with
SHA-256 hashes of the gzip-compressed files, upload required hashes,
finalize the version, and create a release. The response CSP permits
the Google tag and collection endpoints and allows framing by
`online.jbc-lang.org` and `jbc-online.web.app`.
[Firebase Hosting deploy API](https://firebase.google.com/docs/hosting/api-deploy).

See [ANALYTICS-TAGS.md](ANALYTICS-TAGS.md) for the active GitHub Pages
configuration and tag verification.

If deploying through an external HTTPS load balancer for Cloud Armor
instead, restrict Go service ingress to the load balancer.
[Cloud Run ingress](https://docs.cloud.google.com/run/docs/securing/ingress).

## Verify, pause, and roll back

```sh
gcp run services list --region="$JBCC_REGION"
gcp run services describe compiler --region="$JBCC_REGION"
gcp run services describe compiler-worker --region="$JBCC_REGION"
dig +short online.jbc-lang.org
curl --fail --silent --show-error https://jbc-online.web.app/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' "$JBCC_WORKER_URL/compile" \
  -H 'Content-Type: application/json' --data '{}'
```

An unauthenticated worker compile returned HTTP 403. The public compile
API returned HTTP 401 without a Firebase session and HTTP 413 for an
oversized request. The approved GitHub account ran Hello and the
three-file Status lookup example, then saved and loaded a project. The
hosted editor jumped to an unsupported-operation diagnostic, stopped a
test run, and reported the shared build quota when exceeded.

Cloud Run logs showed 7.0 seconds for the first worker compile and
1.55–1.58 seconds for two subsequent builds. The highest sampled mean
memory utilization during the smoke tests was 8.3% of 512 MiB for the web
service and 11.1% of 1 GiB for the worker. Cloud Billing still reported
the £1 monthly Cloud Run cap as **Configured**.

Confirm that the unauthenticated worker request is denied. Verify sign-in,
save and reload, excluded accounts, the multi-file browser example, and
rate limiting. Confirm billing attribution and the cap scope in the
Console. The build switch returns HTTP 503 from the compile endpoint
while paused. The editor and health endpoint remain available.

```sh
gcp run services update compiler --region="$JBCC_REGION" \
  --update-env-vars=JBCC_BUILDS_ENABLED=true

gcp run services update compiler --region="$JBCC_REGION" \
  --update-env-vars=JBCC_BUILDS_ENABLED=false

# Set JBCC_PREVIOUS_REVISION to the last verified API revision.
gcp run revisions list --service=compiler --region="$JBCC_REGION"
gcp run services update-traffic compiler --region="$JBCC_REGION" \
  --to-revisions="$JBCC_PREVIOUS_REVISION=100"
```

Verify the effective build setting after a rollback. Inspect request
metrics and cost reports by service. [Cloud Run rollback](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration).
