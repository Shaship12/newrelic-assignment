# Team Update - Slack message

Post in `#eng-deploys` (or your team's equivalent channel):

---

**🚀 Deploying: URL Shortener service (new)**

**What:** Shipping a small internal URL-shortener API (`POST /urls`,
`GET /{code}`) - Lambda + API Gateway + DynamoDB, all via Terraform.
Why: [fill in the actual internal use case here, e.g. "so we can send
shorter links in SMS notifications"].

**Impact:**
- New service, no existing traffic/endpoints affected.
- No downtime - this is a net-new stack, nothing being replaced.
- Public write endpoint has **no auth yet** (see Risks below) - please
  don't rely on it for anything sensitive until that lands.

**Timeline:**
- Plan reviewed + approved: [date]
- Deploying to `dev`: [date/time]
- Deploying to `staging`: [date/time, pending dev soak]
- Deploying to `prod`: [date/time, pending staging validation + approval]

**Links:**
- PR: [link]
- Runbook: `RUNBOOK.md` in this repo
- Architecture / decisions: `README.md` in this repo
- CI run (Terraform plan): [Actions run link]
- Monitoring: CloudWatch Logs `/aws/lambda/url-shortener-<env>` (dashboard link once one exists)

**Risks / known gaps:**
- `POST /urls` is unauthenticated for now - anyone with the endpoint can
  create short links. Auth is on the follow-up list, not blocking this
  deploy since it's internal/low-traffic to start.
- No custom domain yet - links use the raw API Gateway URL.
- No alarms wired up yet (CloudWatch Logs only, no paging) - will add
  before this handles anything customer-facing.

**Questions / issues:** ping me here or DM @[your name]. For anything
urgent once it's live, follow the normal on-call path - see `RUNBOOK.md`
section 8.

---

*Note on format: this is intentionally short and scannable - engineers
can click into the PR/plan for detail, PMs/support get the "what and why"
in the first two lines without needing to read Terraform.*
