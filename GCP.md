# GCP deployment runbook

The [implementation checklist](ONLINE-COMPILER.md) uses the dedicated
`jBC Online` Google Cloud project (ID `jbc-online`), linked to the
existing billing account.
Cloud Run service `compiler` serves the editor and API at
`https://online.jbc-lang.org/`. Service `compiler-worker` runs jbcc and
Emscripten and accepts calls from the Go service identity.

## Inventory already verified

- The intended billing account has an account-wide alert. The `jBC Online`
  project needs its own Cloud Run spend cap.
- Squarespace hosts DNS for `jbc-lang.org`. No A or CNAME record was
  found for `online.jbc-lang.org`.

Use the intended personal Google Cloud account. Set `JBCC_ACCOUNT` to
that account and `JBCC_REGION` to the selected Cloud Run and Artifact
Registry region. Choose the Firestore
region before creating the database.

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

Set `JBCC_BILLING_ACCOUNT` to the intended account ID from the billing
accounts listed above. Google Cloud project IDs are globally unique.
[Project IDs](https://docs.cloud.google.com/resource-manager/docs/creating-managing-projects).

```sh
JBCC_PROJECT=jbc-online
JBCC_PROJECT_DISPLAY_NAME="jBC Online"

gcloud projects create "$JBCC_PROJECT" --name="$JBCC_PROJECT_DISPLAY_NAME" \
  --account="$JBCC_ACCOUNT"

gcloud billing projects link "$JBCC_PROJECT" \
  --billing-account="$JBCC_BILLING_ACCOUNT" --account="$JBCC_ACCOUNT"

gcp() {
  gcloud --project="$JBCC_PROJECT" --account="$JBCC_ACCOUNT" "$@"
}

gcp billing projects describe "$JBCC_PROJECT"
```

1. In **Billing → Budgets and caps**, verify the account-wide alert covers
   the `jBC Online` project and reaches the intended recipients.
2. Create a monthly **Spend cap enforcement** budget scoped to
   `jbc-online` and **Cloud Run**. Choose the amount for the pilot and
   verify the cap shows **Configured**. This caps both playground services.
3. Confirm alert coverage for Firestore, Hosting or the load balancer,
   Artifact Registry, logs, and network spend. Add a separate
   all-services project alert if earlier notices are needed.

Spend cap enforcement can lag usage.
[Cloud Billing spend caps](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).
[Budget alerts](https://docs.cloud.google.com/billing/docs/how-to/budgets).

If the Budget API is enabled and the account has budget read access, verify
the scopes from the CLI as well.

```sh
gcp billing budgets list --billing-account="$JBCC_BILLING_ACCOUNT" \
  --billing-project="$JBCC_PROJECT"
```

## Enable APIs and provision service identities

```sh
gcp services enable run.googleapis.com artifactregistry.googleapis.com \
  compute.googleapis.com firestore.googleapis.com
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

In Firebase, add the dedicated Cloud project and register a web app.
Register a GitHub OAuth app and use the callback Firebase supplies.
Enable the GitHub provider and authorize `online.jbc-lang.org`. The
Go API verifies Firebase ID tokens and checks the allowlist of invited
GitHub account IDs before compiling or serving saved projects. Request
no repository scopes. [Firebase GitHub provider](https://firebase.google.com/docs/auth/web/github-auth).
[Firestore database IAM](https://docs.cloud.google.com/firestore/docs/manage-databases).

## Publish Docker images and deploy Cloud Run

Once the planned Dockerfiles exist, build Linux AMD64 images from the
repository root. Record their digests and toolchain versions.

```sh
JBCC_REGISTRY="$JBCC_REGION-docker.pkg.dev"
JBCC_IMAGE_ROOT="$JBCC_REGISTRY/$JBCC_PROJECT/jbc-playground"
JBCC_TAG=$(git rev-parse HEAD)
gcloud auth configure-docker "$JBCC_REGISTRY" --account="$JBCC_ACCOUNT"
docker buildx build --platform linux/amd64 --push \
  -f playground/Dockerfile.web -t "$JBCC_IMAGE_ROOT/compiler:$JBCC_TAG" .
docker buildx build --platform linux/amd64 --push \
  -f playground/Dockerfile.worker -t "$JBCC_IMAGE_ROOT/compiler-worker:$JBCC_TAG" .
gcp artifacts docker images describe "$JBCC_IMAGE_ROOT/compiler:$JBCC_TAG"
gcp artifacts docker images describe "$JBCC_IMAGE_ROOT/compiler-worker:$JBCC_TAG"
```

Set `JBCC_WEB_IMAGE` and `JBCC_WORKER_IMAGE` to the full
`@sha256:...` references. Set `JBCC_WORKER_CIDR` to an available
IPv4 `/26` subnet range. Route worker egress through its dedicated VPC and
verify the egress restriction in the deployed worker.
[Artifact Registry images](https://docs.cloud.google.com/artifact-registry/docs/docker/pushing-and-pulling).
[Cloud Run Direct VPC egress](https://docs.cloud.google.com/run/docs/configuring/vpc-direct-vpc).

```sh
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
  --concurrency=1 --timeout=25s --network=playground-worker \
  --subnet=playground-worker --network-tags=playground-worker \
  --vpc-egress=all-traffic
gcp run services add-iam-policy-binding compiler-worker \
  --region="$JBCC_REGION" --member="serviceAccount:$JBCC_WEB_SA" \
  --role=roles/run.invoker

JBCC_WORKER_URL=$(gcp run services describe compiler-worker \
  --region="$JBCC_REGION" --format='value(status.url)')
gcp run deploy compiler --region="$JBCC_REGION" \
  --image="$JBCC_WEB_IMAGE" --service-account="$JBCC_WEB_SA" \
  --allow-unauthenticated --cpu-throttling --min=0 --max=2 \
  --timeout=30s \
  --set-env-vars="JBCC_BUILDS_ENABLED=false,JBCC_COMPILER_URL=$JBCC_WORKER_URL,JBCC_FIRESTORE_DATABASE=jbc-playground"
```

Choose worker CPU and memory from the local build measurements. The API
enforces the allowlist and quotas on the custom domain and the default
service URL. It uses a Cloud Run identity token to call the worker.
[Service-to-service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service).

## Connect the domain and Analytics

1. Create a Firebase Hosting site in the dedicated project and configure
   its catch-all rewrite to Cloud Run service `compiler` in
   `JBCC_REGION`. Deploy from the directory with `firebase.json`.

   ```sh
   firebase deploy --only hosting --project "$JBCC_PROJECT"
   ```

2. Add `online.jbc-lang.org` to Hosting. Apply the exact DNS records
   supplied by its wizard in Squarespace and wait for managed TLS.
   Verify that the mapping supports a CNAME if that record type is
   required. Check the Firebase authorized domain and OAuth callback.
   [Hosting rewrites](https://firebase.google.com/docs/hosting/cloud-run).
   [Custom domain setup](https://firebase.google.com/docs/hosting/custom-domain).
3. Configure a GA4 web data stream for the playground. Set its measurement
   ID in the webpage configuration and verify a page view in Realtime.
   Limit analytics to site usage and keep source code, filenames,
   compiler output, and account identifiers out of event payloads.
   [GA4 setup](https://support.google.com/analytics/answer/14183469).

If deploying through an external HTTPS load balancer for Cloud Armor
instead, restrict Go service ingress to the load balancer.
[Cloud Run ingress](https://docs.cloud.google.com/run/docs/securing/ingress).

## Verify, pause, and roll back

```sh
gcp run services list --region="$JBCC_REGION"
gcp run services describe compiler --region="$JBCC_REGION"
gcp run services describe compiler-worker --region="$JBCC_REGION"
dig +short online.jbc-lang.org
curl --fail --silent --show-error https://online.jbc-lang.org/healthz
curl -s -o /dev/null -w '%{http_code}\n' "$JBCC_WORKER_URL/healthz"
```

Confirm that the unauthenticated worker request is denied. Verify sign-in,
save and reload, excluded accounts, the multi-file browser example, and
rate limiting. Confirm billing attribution and the cap scope in the
Console. Use the application build switch once it has been implemented.

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
