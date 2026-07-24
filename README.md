# URL Shortener - Terraform + GitHub Actions Take-Home

A minimal URL-shortening service deployed to AWS with Lambda, API Gateway
(HTTP API), and DynamoDB, provisioned with Terraform and planned through a
GitHub Actions pipeline.

## What's being deployed, and why

A URL shortener rather than "hello world" because it forced a few real
decisions worth talking about: persistent storage (DynamoDB), two distinct
routes with different semantics (create vs. redirect), IAM scoped to a
specific table, and a response type (HTTP 302) that isn't just
`return "hello"`. It's still small enough to build and explain in the
2-4 hour window.

- `POST /urls` `{"url": "https://..."}` -> creates a short code, returns `201`
- `GET /{code}` -> `302` redirect to the original URL, or `404` if unknown

## Architecture

```
Client
  |
  v
API Gateway (HTTP API)
  |  AWS_PROXY integration, payload format 2.0
  v
Lambda (Python 3.12)
  |  scoped IAM role: GetItem/PutItem on one table only
  v
DynamoDB table (short_code -> original_url)
```

**Why HTTP API instead of REST API (API Gateway v1):** cheaper, lower
latency, and this app needs nothing REST API offers that HTTP API doesn't
(no request validation models, no usage plans/API keys needed here).

**Why Lambda instead of a container on ECS/Fargate:** the workload is
small, bursty, and stateless - a container running 24/7 would mostly sit
idle. Lambda's pay-per-invocation model fits, and it removes a whole class
of ops work (patching, scaling policy, load balancer).

**Why DynamoDB instead of RDS:** the access pattern is a single-key
lookup/write - no joins, no relational structure. DynamoDB's on-demand
billing means zero cost at zero traffic, and there's no connection-pool
management to worry about from Lambda (a common pain point with RDS +
Lambda at scale).

**Why `PAY_PER_REQUEST` billing mode:** unpredictable, low-traffic
workload for a take-home/demo app - provisioned capacity would mean
guessing a number and either overpaying or throttling. Would revisit for
a workload with steady, predictable traffic.

**IAM:** one execution role per Lambda, one inline policy scoped to
`GetItem`/`PutItem` on exactly this table's ARN - no wildcards, no shared
role between environments.

**Environments:** dev/staging/prod are separate Terraform variable sets
(`environments/*.tfvars`), each producing independently-named resources
(`url-shortener-dev-urls` vs `url-shortener-prod-urls`, etc.) so
environments can't collide or be accidentally cross-applied.

## What we are NOT doing (trade-offs, given the 2-4 hour scope)

- **No remote state (S3 + DynamoDB lock).** Requires resources that would
  need to exist before Terraform runs, which doesn't fit "no AWS account
  needed." See `terraform/backend.tf` for the config we'd use for real,
  and why we'd key state per-environment rather than use workspaces.
- **No collision retry on short-code generation.** A 7-character base62
  code has ~3.5 trillion combinations, so collisions are rare, but a real
  version would catch a `ConditionalCheckFailedException` on `PutItem`
  (using a conditional write) and retry with a new code.
- **No custom domain / ACM certificate** - would add DNS and cert
  provisioning, out of scope here.
- **No WAF / rate limiting beyond basic API Gateway throttling.**
- **No automated `terraform apply`** - only `plan` runs in CI, by design
  per the assignment; applying is a manual, deliberate action.
- **No authentication** on `POST /urls` - anyone can create a short link.
  A real deployment would put an API key or Cognito authorizer in front
  of the create route (the redirect route should stay public).

## What I'd change for real production

1. Wire up remote state (S3 + native S3 locking, or DynamoDB lock table).
2. Add authentication on the write path, and WAF on the API Gateway stage.
3. Add collision-safe code generation (conditional write + retry).
4. Add alarms (CloudWatch alarms on Lambda errors/throttles, API Gateway
   5xx rate) wired to an SNS topic / on-call tool.
5. Move `role-to-assume` ARNs and account IDs out of tfvars/workflow and
   into GitHub Environment secrets per environment (see below - already
   partly done).
6. Add integration tests that hit a deployed dev stack after plan/apply.
7. Consider TTL on DynamoDB items if short links should expire.

## Repository layout

```
app/
  lambda_function.py       # the Lambda handler
terraform/
  providers.tf              # provider + version pins
  backend.tf                # remote state example (not active)
  variables.tf
  dynamodb.tf
  iam.tf
  lambda.tf
  api_gateway.tf
  outputs.tf
  environments/
    dev.tfvars
    staging.tfvars
    prod.tfvars
.github/workflows/
  terraform-plan.yml
README.md
RUNBOOK.md
TEAM_UPDATE.md
```

## How to use this

### Prerequisites
- Terraform >= 1.5
- AWS CLI configured (or an AWS account, per the assignment's setup
  instructions) - **not required to just run `terraform plan`** using
  the region default; you do need valid-looking credentials for the AWS
  provider to initialize, even for a plan, since it calls `sts:GetCallerIdentity`.
- Python 3.12 (only needed if you want to run/lint the Lambda code locally)

### Run a plan locally

```bash
cd terraform
terraform init
terraform plan -var-file=environments/dev.tfvars
```

### Run it in GitHub Actions

1. Push this repo to GitHub.
2. Set up an AWS IAM OIDC identity provider trusting
   `token.actions.githubusercontent.com`, and one IAM role per environment
   (or one role, scoped down, reused across environments) that the
   workflow can assume - see `RUNBOOK.md` for exact steps.
3. In the repo, create three **GitHub Environments**: `dev`, `staging`,
   `prod`. In each, add a secret `AWS_ROLE_ARN` with that environment's
   role ARN. For `prod`, add a required reviewer under environment
   protection rules - this is what gates prod plans behind manual approval.
4. Go to **Actions -> Terraform Plan -> Run workflow**, pick an
   environment, and run it. Or open a PR that touches `terraform/**` or
   `app/**` - it will auto-plan against `dev` and comment the output on
   the PR.

### Why OIDC instead of long-lived `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`
The assignment's setup notes mention IAM user keys as an option; this repo
uses GitHub's OIDC federation with `aws-actions/configure-aws-credentials`
instead, because it means **no long-lived AWS credentials stored in
GitHub at all** - the workflow requests a short-lived token per run. It's
more setup up front but is the current AWS/GitHub-recommended pattern and
avoids the ongoing "who has these keys, when do they rotate" problem
static secrets create.
