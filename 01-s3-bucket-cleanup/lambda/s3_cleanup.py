"""
S3 Bucket Cleanup - deletes objects older than AGE_THRESHOLD_DAYS.

Environment variables:
    BUCKET_NAME          - target S3 bucket name
    AGE_THRESHOLD_DAYS   - (optional) age threshold in days, default 30
                            for testing, temporarily set this low (e.g. 0)
                            or add AGE_THRESHOLD_MINUTES for finer control.
"""

import os
import boto3
from datetime import datetime, timedelta, timezone

s3 = boto3.client("s3")

BUCKET_NAME = os.environ["BUCKET_NAME"]
AGE_THRESHOLD_DAYS = int(os.environ.get("AGE_THRESHOLD_DAYS", "30"))


def lambda_handler(event, context):
    cutoff = datetime.now(timezone.utc) - timedelta(days=AGE_THRESHOLD_DAYS)

    paginator = s3.get_paginator("list_objects_v2")
    deleted_keys = []
    keys_to_delete = []

    #List objects in the bucket (use the paginator — never assume one page of results).
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get("Contents", []):
            last_modified = obj["LastModified"]
            #Compare each object's LastModified (timezone-aware) with the current UTC time.
            if last_modified < cutoff: 
                keys_to_delete.append({"Key": obj["Key"]})

                if len(keys_to_delete) == 1000:
                    _delete_batch(keys_to_delete, deleted_keys)
                    keys_to_delete = []

    if keys_to_delete:
        _delete_batch(keys_to_delete, deleted_keys)

    print(f"Deleted {len(deleted_keys)} object(s) older than {AGE_THRESHOLD_DAYS} day(s):")
    for key in deleted_keys:
        print(f"  - {key}")

    return {
        "bucket": BUCKET_NAME,
        "threshold_days": AGE_THRESHOLD_DAYS,
        "deleted_count": len(deleted_keys),
        "deleted_keys": deleted_keys,
    }

#Delete objects from S3 using boto3
def _delete_batch(keys_to_delete, deleted_keys):
    response = s3.delete_objects(
        Bucket=BUCKET_NAME,
        Delete={"Objects": keys_to_delete, "Quiet": False},
    )
    for deleted in response.get("Deleted", []):
        deleted_keys.append(deleted["Key"])
    for error in response.get("Errors", []):
        print(f"  ! Failed to delete {error['Key']}: {error['Message']}")
