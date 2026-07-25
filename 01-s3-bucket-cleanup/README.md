# 1. Automated S3 Bucket Cleanup (Objects Older Than 30 Days)

**Objective:** Automate deletion of stale objects in an S3 bucket using Lambda + Boto3.

## Architecture

```
Manual trigger / EventBridge --> Lambda (Python 3.12, Boto3) --> S3 (list + delete objects)
```

## Steps to Achieve

### 1. S3 Setup

1. Go to **S3 console → Create bucket**.
   - Bucket name: e.g. `tanishq-bucket-20260725`.
   - Region: pick one close to you, keep it consistent with your Lambda region.
   - Leave "Block all public access" checked (default) — this bucket doesn't need public access.
2. Upload several test files (`aws s3 cp` or drag-and-drop in console) — mix of a few files.
3. **Simulating "old" objects:** S3 doesn't let you fake `LastModified`, so for testing:
   - Temporarily lower the age threshold in the Lambda code from `30 days` to e.g. `AGE_THRESHOLD_MINUTES = 2`.
   - Upload a batch of files, wait a couple of minutes, then upload a fresh batch — the first batch is now "older" relative to the threshold.
   - Once you've confirmed deletion logic works, **set the threshold back to 30 days** for the final submission.

### 2. Lambda IAM Role

Create a role (**S3CleanupRole**) with trust policy for `lambda.amazonaws.com`, and attach:

**AWS managed policy:** `AWSLambdaBasicExecutionRole` (CloudWatch Logs)

**Inline policy** (scoped to your bucket only):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::tanishq-bucket-20260725"
    },
    {
      "Sid": "DeleteObjects",
      "Effect": "Allow",
      "Action": "s3:DeleteObject",
      "Resource": "arn:aws:s3:::tanishq-bucket-20260725/*"
    }
  ]
}
```

### 3. Lambda Function

1. Create a Lambda function: runtime **Python 3.12**, attach the role from step 2.
2. Configure permissions to set execution role name as **S3CleanupRole** (that we created earlier), refer **screenshot #4**
3. Set environment variables (**refer screenshot#3**):
   - `BUCKET_NAME` = your bucket name
   - `AGE_THRESHOLD_DAYS` = `30` (for testing we used timedelta(minutes=AGE_THRESHOLD_MINUTES))
4. Paste the code from [`lambda/s3_cleanup.py`](lambda/s3_cleanup.py). It:
   1. Uses `paginator = s3.get_paginator("list_objects_v2")` and iterates **all pages** — never assumes a single page of results.
   2. Compares each object's `LastModified` (already timezone-aware / UTC from Boto3) against `datetime.now(timezone.utc) - timedelta(days=AGE_THRESHOLD_DAYS)`.
   3. Batches keys older than the threshold and deletes them with `delete_objects` (up to 1000 keys per call, chunked if more).
   4. Prints the key and last-modified date of every deleted object to CloudWatch Logs.
5. Set **Timeout** to at least 30–60 seconds if the bucket has many objects

### 4. Testing

1. Use the Lambda console **Test** button with an empty test event (`{}`) — this function doesn't need event data.
2. Check the **CloudWatch Logs** output (or the returned execution result) for the list of deleted keys.
3. Go to the S3 console and confirm only the newer files remain.
4. Re-run the test — it should now report "no objects older than threshold" since stale files are already gone.
5. Once verified, edit the code to restore `AGE_THRESHOLD_DAYS = 30` for the final version.

### 6. Screenshot Sequence

| Stage               | Screenshot    |
| ------------------- | ------------- |
| Before              | Screenshot #5 |
| Execution of Lambda | Screenshot #6 |
| After               | Screenshot #7 |

7. Log events saved in cloudwatch

### 5. (Optional) Automate with EventBridge

To run this on a schedule instead of manually:

1. **EventBridge → Rules → Create rule** → Schedule → e.g. `rate(1 day)`.
2. Target: this Lambda function.
3. Save — EventBridge will now invoke the cleanup daily.

## Discussion Point: Lambda vs. S3 Lifecycle Rules

In production, **S3 Lifecycle Rules** handle expiration of objects older than N days natively, with zero code and no compute cost. You'd reach for a **Lambda-based approach instead** when the deletion logic is like:

- Conditional logic based on object tags/metadata combined with business rules (e.g. delete only if a companion "processed" flag exists elsewhere).
- Naming-pattern-based rules (e.g. delete `tmp-*` objects after 30 days but keep `archive-*` indefinitely) that Lifecycle Rules' prefix/tag filters can't fully express.
- Cross-service actions tied to the deletion (e.g. notify another team via SNS, log the deletion to some database, or trigger a downstream cleanup in a different account/service) — Lifecycle Rules can only expire/transition objects, they can't orchestrate other actions.
