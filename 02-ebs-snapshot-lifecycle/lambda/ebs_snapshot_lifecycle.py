"""
EBS Snapshot Creation and Cleanup.

Environment variables:
    VOLUME_ID        - EBS volume ID to snapshot (vol-xxxxxxxxxxxxxxxxx)
    RETENTION_DAYS   - (optional) delete tagged snapshots older than this, default 30
"""

import os
import boto3
from datetime import datetime, timedelta, timezone

ec2 = boto3.client("ec2")

VOLUME_ID = os.environ["VOLUME_ID"]
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))
TAG_KEY = "CreatedBy"
TAG_VALUE = "Lambda-Backup"


def lambda_handler(event, context):
    created_id = _create_snapshot()
    deleted_ids = _cleanup_old_snapshots()

    return {
        "created_snapshot_id": created_id,
        "deleted_snapshot_ids": deleted_ids,
    }


def _create_snapshot():
    now_iso = datetime.now(timezone.utc).isoformat()

    response = ec2.create_snapshot(
        VolumeId=VOLUME_ID,
        Description=f"Automated backup of {VOLUME_ID} via Lambda",
        TagSpecifications=[
            {
                "ResourceType": "snapshot",
                "Tags": [
                    {"Key": TAG_KEY, "Value": TAG_VALUE},
                    {"Key": "CreatedOn", "Value": now_iso},
                ],
            }
        ],
    )
    snapshot_id = response["SnapshotId"]
    print(f"Created snapshot {snapshot_id} for volume {VOLUME_ID}")
    return snapshot_id


def _cleanup_old_snapshots():
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    deleted_ids = []

    paginator = ec2.get_paginator("describe_snapshots")
    page_iterator = paginator.paginate(
        OwnerIds=["self"],
        Filters=[{"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]}],
    )

    for page in page_iterator:
        for snap in page.get("Snapshots", []):
            start_time = snap["StartTime"]  # tz-aware (UTC) via boto3
            if start_time < cutoff:
                snap_id = snap["SnapshotId"]
                try:
                    ec2.delete_snapshot(SnapshotId=snap_id)
                    deleted_ids.append(snap_id)
                    print(f"Deleted snapshot {snap_id} (created {start_time})")
                except Exception as exc:
                    print(f"  ! Failed to delete {snap_id}: {exc}")

    if not deleted_ids:
        print(f"No snapshots older than {RETENTION_DAYS} day(s) found.")

    return deleted_ids
