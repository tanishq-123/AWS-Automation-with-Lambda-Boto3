# AWS Automation with Lambda & Boto3

A set of hands-on AWS automation assignments built with **Python 3.12 + Boto3**, deployed as **Lambda functions**, and triggered via manual invocation or **Amazon EventBridge** schedules/rules. Each assignment lives in its own folder with a self-contained README covering setup, IAM policy, code, testing evidence (screenshots + CloudWatch logs), and a short discussion of the "native AWS service" alternative.

## Repo Structure

```
AWS-Automation-with-Lambda-Boto3/
├── 01-s3-bucket-cleanup/              # Delete S3 objects older than 30 days
│   ├── README.md
│   └── lambda/
│       └── s3_cleanup.py
├── 02-ebs-snapshot-lifecycle/         # Create + retire EBS snapshots
│   ├── README.md
│   ├── lambda/
│   │   └── ebs_snapshot_lifecycle.py
│   └── screenshots/                   # Screenshot__1.png ... Screenshot__11.png
├── 03-ec2-auto-tagging/                # Auto-tag EC2 instances on launch (+ CloudTrail Owner bonus)
│   ├── README.md
│   ├── inline-policy.json
│   ├── lambda/
│   │   └── ec2_auto_tag.py
│   ├── screenshots/                   # Screenshot__1.png ... Screenshot__13.png
│   └── logs/
│       ├── cloudwatchlogs.log         # base tagging path
│       └── cloudwatchlogs-bonus.log   # CloudTrail Owner-tag path
├── 04-daily-cost-alert/                # Cost Explorer + SNS budget alert
│   ├── README.md
│   ├── inline-policy.json
│   ├── lambda/
│   │   └── cost_alert.py
│   ├── screenshots/                   # Screenshot__1.png ... Screenshot__8.png
│   └── logs/
│       └── cloudwatchlog.log
└── README.md                          # you are here
```

> Note: `01-s3-bucket-cleanup` currently references its screenshots and CloudWatch Logs inline by number/description (e.g. "Screenshot #4") rather than as embedded images in a `screenshots/` subfolder like assignments 2–4. If you want consistent evidence presentation across all four, move that assignment's screenshots into a `01-s3-bucket-cleanup/screenshots/` folder and update its README to embed them the same way as the others.

## Assignments

| #   | Assignment                                                             | AWS Services                                      | Trigger                                        |
| --- | ---------------------------------------------------------------------- | ------------------------------------------------- | ---------------------------------------------- |
| 1   | [Automated S3 Bucket Cleanup](01-s3-bucket-cleanup/README.md)          | S3, Lambda, IAM                                   | Manual / EventBridge (optional, daily)         |
| 2   | [EBS Snapshot Creation & Cleanup](02-ebs-snapshot-lifecycle/README.md) | EC2 (EBS), Lambda, IAM, EventBridge Scheduler     | EventBridge Scheduler (weekly cron)            |
| 3   | [Auto-Tagging EC2 Instances on Launch](03-ec2-auto-tagging/README.md)  | EC2, Lambda, EventBridge, CloudTrail              | EventBridge (event pattern on `running` state) |
| 4   | [Daily AWS Cost Alert](04-daily-cost-alert/README.md)                  | Cost Explorer, SNS, Lambda, EventBridge Scheduler | EventBridge Scheduler (daily cron)             |

## Prerequisites (common to all assignments)

- An AWS account with console + CLI access (AWS CLI v2 configured with `aws configure`).
- Python 3.12+ locally if you want to test scripts outside Lambda.
- Basic familiarity with IAM roles/policies, since every assignment uses a **least-privilege inline policy** scoped to the specific resource where AWS supports resource-level scoping (S3 bucket ARN, SNS topic ARN); where an API is account-wide by design (Cost Explorer, most EC2 tagging/snapshot actions), the policy uses `Resource: "*"` and scoping is instead enforced in code (tag filters, `OwnerIds=["self"]`, etc.).
- Boto3 is already available in the Lambda Python 3.12 managed runtime — no layer needed for these assignments.

## General workflow used across assignments

1. Create the IAM role for Lambda (trust policy = `lambda.amazonaws.com`) and attach the inline policy described in that assignment's README, plus the AWS-managed `AWSLambdaBasicExecutionRole` (for CloudWatch Logs).
2. Create the Lambda function (Python 3.12 runtime, paste/upload the code from `lambda/`).
3. Set any required environment variables (bucket name, volume ID, topic ARN, threshold, delay seconds, etc.) under **Configuration → Environment variables** instead of hardcoding them.
4. Test with a manual invocation (**Test** tab in the Lambda console) before wiring up EventBridge.
5. Attach an EventBridge rule (event pattern) or EventBridge Scheduler (cron/rate) where the assignment calls for automation. For controlled test runs, a **one-off schedule** is a convenient way to trigger the Lambda once at a specific time without waiting for the real recurring cadence — just remember to switch to a **recurring schedule** for the final submitted configuration.
6. Verify results in the relevant console (S3, EC2/Snapshots, CloudWatch Logs, email inbox for SNS) and capture screenshots/log exports as evidence.

## Notes

- All code uses the **Boto3 paginator** pattern for list operations — never assumes a single page of results.
- All timestamp comparisons are **timezone-aware** (UTC) to avoid `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Assignment 3's Lambda applies tags in **two phases**: base tags (`LaunchDate`, `Environment`, `Name`) are written immediately on invocation, while the bonus `Owner` tag (resolved via a CloudTrail lookup, with a configurable delay to offset CloudTrail's indexing lag) is applied in a second, separate `create_tags` call. This avoids making the "always-on" tags wait on the "best-effort" bonus lookup.
- Each README includes a short **discussion point** comparing the Lambda-based approach to the equivalent native/managed AWS feature (S3 Lifecycle Rules, AWS Data Lifecycle Manager, AWS Budgets), per the assignment brief — plus, for Assignment 3, an additional note on why a purely synchronous "sleep-then-lookup" pattern is a reasonable demo/interview answer but not a production-grade design.
