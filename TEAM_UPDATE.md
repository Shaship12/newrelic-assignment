# Team Update - Slack message

Post in `#eng-deploys`:

---

**🚀 Deploying: URL Shortener service (new)**

**What & why:** Shipping a small internal URL-shortener API (`POST /urls` to create a short link, `GET /{code}` to redirect) — Lambda + API Gateway + DynamoDB, provisioned with Terraform. Built so we can use short, trackable links in outbound notifications instead of long raw URLs.

**Impact:**
- New service, no existing endpoints or traffic affected — nothing being replaced.
- No downtime expected; this is a net-new stack.
- ⚠️ `POST /urls` has **no auth yet** — don't point anything sensitive at it until auth lands (tracked as a fast-follow, see Risks below).

**Timeline:**
- Terraform plan reviewed + approved: today
- `dev`: deploying now
- `staging`: after ~2 days soak in dev with no errors
- `prod`: after staging validation, gated behind manual approval in the pipeline

**Links:**
- PR: `<add PR link here>`
- Runbook (deploy/rollback/troubleshooting steps): [`RUNBOOK.md`](./RUNBOOK.md)
- Architecture & design decisions: [`README.md`](./README.md)
- CI run (Terraform plan output): `<add Actions run link here>`
- Monitoring: CloudWatch Logs at `/aws/lambda/url-shortener-<env>` (dashboard link once one exists — tracked as a fast-follow)

**Risks / known gaps:**
- No auth on the create endpoint yet — internal/low-traffic only for now.
- No custom domain — links use the raw API Gateway URL until DNS/ACM is added.
- No alarms/paging wired up yet — logs only. Will add before this is customer-facing.

**Questions or issues:** ping me in this channel, or DM me directly. For a live incident once this is in `prod`, follow our normal on-call path (see `RUNBOOK.md` §8).

---

## Why this format

**Communicating to a mixed audience (engineers, PMs, support):** the first two lines (What & why, Impact) are written so a non-engineer gets the full picture without reading anything else — no Terraform jargon, no resource names, just "what changed and does it affect you." Everyone past that point is opting into more depth.

**Scannable, not paragraphs:** every section is a short bulleted list with a bolded label, so someone skimming on their phone gets the shape of the update in a few seconds — timeline, risks, and contact are each one glance away, not buried in prose.

**Depth on demand:** the Links section is the "for more detail" escape hatch — engineers who want the actual Terraform diff go to the PR/CI run, anyone debugging a live issue goes to the Runbook, anyone curious about *why* it's built this way goes to the README. Nobody has to read all three to get the update; they're there for whoever needs to go deeper.