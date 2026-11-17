# AWS Doc Q&A (portfolio project)

Small document Q&A API over public AWS Well-Architected pages. BM25 keyword retrieval in pure
Python, extractive answers with citations, optional Amazon Bedrock summary (off by default).
Built to run on AWS Lambda + API Gateway. Full README (architecture, deploy, teardown, costs) comes later.

## Run locally

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q                      # API + BM25 tests
python eval/run_eval.py        # retrieval eval, Hit@3 (threshold: --min or EVAL_MIN_HIT_AT_3)
uvicorn app.main:app --reload  # needs: pip install uvicorn
```

## Corpus

`data/docs/*.txt` currently holds **short seed notes paraphrased by hand**, one per public page
(each file's `Source:` line names the page). To replace them with the real page text, run
`python scripts/fetch_corpus.py` from a machine with internet access, then re-run the eval.

## First deploy (by hand)

Two Terraform stacks, both with state in your S3 bucket (`-backend-config` keeps the bucket name out of git):

| Stack | Contains | Applied by |
|---|---|---|
| `infra/bootstrap` | GitHub OIDC provider, CI deploy role, Lambda permissions boundary, SNS alert topic + email, USD 5 budget | You, with admin credentials (rarely changes) |
| `infra/app` | Lambda, API Gateway HTTP API, Lambda execution role, log groups, latency metric filter, error alarm, dashboard | You the first time, then GitHub Actions |

CI can only create Lambda roles that carry the boundary from `infra/bootstrap`, so it cannot grant itself or the function more than "write own logs (+ optional Bedrock invoke)".

```bash
export TF_STATE_BUCKET=<your-state-bucket>

# 1. bootstrap (admin credentials)
cd infra/bootstrap
cp terraform.tfvars.example terraform.tfvars   # set github_repo, tf_state_bucket, alert_email
terraform init -backend-config="bucket=$TF_STATE_BUCKET"
terraform apply
terraform output deploy_role_arn               # -> GitHub variable AWS_DEPLOY_ROLE_ARN

# 2. build the Lambda package (Python 3.12 arm64 wheels; works from macOS too)
cd ../.. && python scripts/build_lambda.py

# 3. app
cd infra/app
terraform init -backend-config="bucket=$TF_STATE_BUCKET"
terraform apply
curl "$(terraform output -raw api_url)health"
curl -X POST "$(terraform output -raw api_url)search" -H 'content-type: application/json' -d '{"query":"least privilege"}'
```

Provider lock files are committed with hashes for Linux, macOS (Intel and Apple Silicon) and Windows.

## Monitoring

- **Logs**: one JSON line per request in `/aws/lambda/docqa-api` (`request_id`, `endpoint`, `status`, `latency_ms`, `result_count`, `error`); API access logs in `/aws/apigateway/docqa-api`. Both kept 14 days.
- **Metric filter**: `latency_ms` from those lines becomes the custom metric `DocQA/LatencyMs`.
- **Alarm** `docqa-errors`: Lambda errors + API Gateway 5xx >= 1 in 5 minutes, emails via the `docqa-alerts` SNS topic (and again when it recovers).
- **Dashboard** `docqa-overview`: errors, p95 latency (app and API Gateway), request counts. URL: `terraform output dashboard_url` in `infra/app`.
- **Budget** `docqa-monthly`: emails at 80% of USD 5 actual spend and at 100% forecast. It covers the whole account, not just this project.

The email address lives only in your local `infra/bootstrap/terraform.tfvars` (gitignored); CI never needs it.
After applying bootstrap, **click the link in the "AWS Notification - Subscription Confirmation" email**, or alarms will not reach you.

Test the alert path without breaking anything (CloudWatch resets the state at the next evaluation):

```bash
aws cloudwatch set-alarm-state --alarm-name docqa-errors --state-value ALARM --state-reason "manual test" --region ap-southeast-1
```

Useful Logs Insights query (log group `/aws/lambda/docqa-api`):

```
fields @timestamp, endpoint, status, latency_ms, result_count, error
| filter ispresent(latency_ms)
| stats count(*) as requests, pct(latency_ms, 95) as p95_ms, sum(status >= 500) as errors by endpoint
```
