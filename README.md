# AWS Automation with Lambda & Boto3

A set of hands-on AWS automation assignments built with **Python 3.12 + Boto3**, deployed as **Lambda functions**, and triggered via manual invocation or **Amazon EventBridge** schedules/rules. Each assignment lives in its own folder with a self-contained README covering setup, IAM policy, code, testing, and a short discussion of the "native AWS service" alternative.

## Repo Structure

```
AWS-Automation-with-Lambda-Boto3/
├── 01-s3-bucket-cleanup/           # Delete S3 objects older than 30 days
│   ├── README.md
│   └── lambda/
│       └── s3_cleanup.py
├── 02-ebs-snapshot-lifecycle/      # Create + retire EBS snapshots
│   ├── README.md
│   └── lambda/
│       └── ebs_snapshot_lifecycle.py
├── 03-ec2-auto-tagging/            # Auto-tag EC2 instances on launch
│   ├── README.md
│   └── lambda/
│       └── ec2_auto_tag.py
├── 04-daily-cost-alert/            # Cost Explorer + SNS budget alert
│   ├── README.md
│   └── lambda/
│       └── cost_alert.py
└── README.md                       # you are here
```

## Assignments

| # | Assignment | AWS Services | Trigger |
|---|-----------|---------------|---------|
| 1 | [Automated S3 Bucket Cleanup](01-s3-bucket-cleanup/README.md) | S3, Lambda, IAM | Manual / EventBridge (optional) |
| 2 | [EBS Snapshot Creation & Cleanup](02-ebs-snapshot-lifecycle/README.md) | EC2 (EBS), Lambda, IAM, EventBridge | EventBridge (weekly) |
| 3 | [Auto-Tagging EC2 Instances on Launch](03-ec2-auto-tagging/README.md) | EC2, Lambda, EventBridge, CloudTrail | EventBridge (event pattern) |
| 4 | [Daily AWS Cost Alert](04-daily-cost-alert/README.md) | Cost Explorer, SNS, Lambda, EventBridge | EventBridge (daily) |

## Prerequisites (common to all assignments)

- An AWS account with console + CLI access (AWS CLI v2 configured with `aws configure`).
- Python 3.12+ locally if you want to test scripts outside Lambda.
- Basic familiarity with IAM roles/policies, since every assignment uses a **least-privilege inline policy** scoped to the specific resource, not `*`.
- Boto3 is already available in the Lambda Python 3.12 managed runtime — no layer needed for these assignments.

## General workflow used across assignments

1. Create the IAM role for Lambda (trust policy = `lambda.amazonaws.com`) and attach the inline policy described in that assignment's README, plus the AWS-managed `AWSLambdaBasicExecutionRole` (for CloudWatch Logs).
2. Create the Lambda function (Python 3.12 runtime, paste/upload the code from `lambda/`).
3. Set any required environment variables (bucket name, volume ID, topic ARN, threshold, etc.) under **Configuration → Environment variables** instead of hardcoding them.
4. Test with a manual invocation (**Test** tab in the Lambda console) before wiring up EventBridge.
5. Attach an EventBridge schedule or event pattern rule where the assignment calls for automation.
6. Verify results in the relevant console (S3, EC2/Snapshots, CloudWatch Logs, email inbox for SNS).

## Notes

- All code uses the **Boto3 paginator** pattern for list operations — never assumes a single page of results.
- All timestamp comparisons are **timezone-aware** (UTC) to avoid `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Each README includes a short **discussion point** comparing the Lambda-based approach to the equivalent native/managed AWS feature (S3 Lifecycle Rules, Data Lifecycle Manager, AWS Budgets), per the assignment brief.
