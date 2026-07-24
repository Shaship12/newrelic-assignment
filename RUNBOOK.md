# Runbook - URL Shortener

Audience: whoever is deploying or on-call for this service, including
someone who did not write the code and is doing this at 2am.

## 1. Prerequisites

- Access to the AWS account for the target environment (dev/staging/prod)
- Terraform >= 1.5 installed (or use the GitHub Actions workflow instead
  of local Terraform - preferred for staging/prod)
- AWS CLI configured, OR (for CI) the GitHub repo has the OIDC role set
  up per environment (see "One-time AWS setup" below)
- Permissions needed: ability to assume the deploy role for the target
  environment (`iam:AssumeRole` on `url-shortener-<env>-deploy` or
  equivalent), and membership in the GitHub team allowed to approve `prod`
  environment deployments

## 2. One-time AWS setup (per AWS account, done once)

1. Create an IAM OIDC identity provider for GitHub Actions:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`
2. Create an IAM role per environment (e.g. `url-shortener-dev-deploy`)
   with a trust policy restricting `sub` to this repo + branch/environment,
   and attach a policy allowing the actions Terraform needs (Lambda,
   API Gateway v2, DynamoDB, IAM role/policy management scoped to this
   app's resource names, CloudWatch Logs).
3. Note the role ARN(s) - you'll need them for step 3 below.
4. In GitHub: **Settings -> Environments**, create `dev`, `staging`,
   `prod`. Add secret `AWS_ROLE_ARN` to each with that environment's role
   ARN. On `prod`, add a required reviewer.

This is a one-time setup per AWS account, not per deployment.

## 3. Deploying (normal path - via GitHub Actions)

1. Open **Actions -> Terraform Plan -> Run workflow** in GitHub.
2. Choose the environment (`dev`, `staging`, or `prod`).
3. Run it. For `prod`, the run will pause and wait for an approver
   (configured on the `prod` GitHub Environment).
4. Review the plan output in the job log (or, for PR-triggered runs, in
   the PR comment). Confirm it's only creating/changing what you expect.
5. This workflow only runs `terraform plan` - it does not apply. To
   actually create the infrastructure, run `terraform apply
   -var-file=environments/<env>.tfvars` locally with the same credentials
   (or extend the workflow with a manual-approval `apply` job - not
   included here, see README trade-offs).

## 4. Deploying locally (fallback, e.g. CI is down)

```bash
cd terraform
terraform init
terraform plan  -var-file=environments/dev.tfvars -out=tfplan
terraform apply tfplan
```

Repeat with `staging.tfvars` / `prod.tfvars` for those environments.
**Never run `apply` against `prod.tfvars` without a reviewed plan output.**

## 5. Verifying a deployment succeeded

1. Get the API endpoint from the Terraform output:
   ```bash
   terraform output api_endpoint
   ```
2. Create a short link:
   ```bash
   curl -s -X POST "$(terraform output -raw api_endpoint)/urls" \
     -H 'Content-Type: application/json' \
     -d '{"url": "https://example.com"}'
   ```
   Expect a `201` with a `short_code` and `short_url`.
3. Follow the redirect:
   ```bash
   curl -sI "$(terraform output -raw api_endpoint)/<short_code>"
   ```
   Expect a `302` with a `Location: https://example.com` header.
4. Check CloudWatch Logs at `/aws/lambda/url-shortener-<env>` for errors.
5. Check the Lambda function's "Monitor" tab in the AWS console for
   invocation/error/duration metrics.

## 6. Rollback

Infrastructure and code are deployed together via Terraform (the Lambda
zip is built from the current `app/lambda_function.py` on every apply).

- **To roll back to a previous version:** `git checkout` the previous
  commit (or `git revert` the bad commit), then re-run
  `terraform plan` / `apply` for the affected environment. Terraform will
  detect the changed `source_code_hash` and redeploy the old code.
- **Fast path if Lambda code is the only problem:** in the AWS Console,
  Lambda -> Versions - if you're publishing versions/aliases (not set up
  by default in this Terraform, see note below), you can point the alias
  back at the previous version instantly without a Terraform run. **Note:**
  this repo's Lambda resource does not currently publish versions/aliases -
  that's a good next step before this becomes the primary rollback path
  (see README "what I'd change for production").
- **If DynamoDB data is the problem:** point-in-time recovery is enabled
  in `prod` only - restore via AWS Console -> DynamoDB -> table -> Backups
  -> Restore to point in time. This creates a **new** table; you'd then
  need a follow-up change to point the Lambda's `TABLE_NAME` env var at it
  (or restore under the original name after deleting the broken table,
  with appropriate caution).

## 7. Common issues / troubleshooting

| Symptom | Likely cause | What to check |
|---|---|---|
| `terraform init` fails on provider download | No network / registry blocked | Check outbound network access to `registry.terraform.io` |
| `terraform plan` fails with `AccessDenied` / `sts:GetCallerIdentity` | Bad or expired credentials | Re-run `aws sts get-caller-identity`; for CI, check the OIDC trust policy `sub` condition matches the branch/environment triggering the run |
| API returns `403` from API Gateway before reaching Lambda | Route/stage misconfigured, or throttling limit hit | Check `aws_apigatewayv2_route` route keys match exactly (`POST /urls`, `GET /{code}`); check CloudWatch access logs at `/aws/apigateway/url-shortener-<env>` |
| API returns `500` | Lambda error (bad env var, IAM denial, unhandled exception) | Check `/aws/lambda/url-shortener-<env>` in CloudWatch Logs for the stack trace |
| `POST /urls` returns `201` but `GET /{code}` returns `404` immediately after | DynamoDB write didn't complete, or wrong table name in Lambda env var | Confirm `TABLE_NAME` env var on the Lambda matches `terraform output dynamodb_table_name` |
| GitHub Actions job fails at "Configure AWS credentials" | OIDC role trust policy doesn't match this repo, or `AWS_ROLE_ARN` secret missing/wrong | Check the environment's secret in GitHub Settings -> Environments; check the role's trust policy `sub` claim |
| `prod` plan never starts running | Waiting on required reviewer approval | Check the "Environments" tab on the workflow run for a pending approval |

## 8. Who to contact

- Primary: whoever owns this repo / is listed as CODEOWNERS
- For AWS account/IAM issues: your cloud/platform team
- For urgent production incidents: follow your team's normal on-call/incident process
