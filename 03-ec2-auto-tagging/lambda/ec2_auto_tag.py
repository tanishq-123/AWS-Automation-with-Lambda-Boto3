"""
Auto-tag EC2 instances on launch (triggered by EventBridge on the
"EC2 Instance State-change Notification" event, filtered to state=running).

Environment variables:
    ENVIRONMENT_TAG_VALUE           - (optional) value for the Environment tag, default "dev"
    NAME_TAG_PREFIX                 - (optional) prefix for the Name tag (Name = "<prefix>-<instance-id>"), default "auto-tagged"
    ENABLE_OWNER_LOOKUP             - (optional) "true" to enable the CloudTrail bonus lookup
    CLOUDTRAIL_LOOKUP_DELAY_SECONDS - (optional) seconds to wait before querying CloudTrail, default 60
"""

import os
import time
from datetime import date, datetime, timedelta, timezone

import boto3

ec2 = boto3.client("ec2")
cloudtrail = boto3.client("cloudtrail")

ENVIRONMENT_TAG_VALUE = os.environ.get("ENVIRONMENT_TAG_VALUE", "dev")
NAME_TAG_PREFIX = os.environ.get("NAME_TAG_PREFIX", "auto-tagged")
ENABLE_OWNER_LOOKUP = os.environ.get("ENABLE_OWNER_LOOKUP", "false").lower() == "true"
CLOUDTRAIL_LOOKUP_DELAY_SECONDS = int(os.environ.get("CLOUDTRAIL_LOOKUP_DELAY_SECONDS", "60"))


def lambda_handler(event, context):
    instance_id = event["detail"]["instance-id"]

    # Apply the base tags immediately - no reason to make these wait on the
    # CloudTrail lookup delay below.
    base_tags = [
        {"Key": "LaunchDate", "Value": date.today().isoformat()},
        {"Key": "Environment", "Value": ENVIRONMENT_TAG_VALUE},
        {"Key": "Name", "Value": f"{NAME_TAG_PREFIX}-{instance_id}"},
    ]
    ec2.create_tags(Resources=[instance_id], Tags=base_tags)
    print(f"Tagged instance {instance_id} immediately with: {base_tags}")

    all_tags_applied = list(base_tags)

    if ENABLE_OWNER_LOOKUP:
        owner = _lookup_owner(instance_id)
        owner_tag = {"Key": "Owner", "Value": owner or "unknown"}
        ec2.create_tags(Resources=[instance_id], Tags=[owner_tag])
        all_tags_applied.append(owner_tag)
        print(f"Tagged instance {instance_id} with Owner tag (after {CLOUDTRAIL_LOOKUP_DELAY_SECONDS}s delay): {owner_tag}")

    return {"instance_id": instance_id, "tags_applied": all_tags_applied}


def _lookup_owner(instance_id):
    """Bonus: correlate the launch with CloudTrail to find the calling IAM identity.

    CloudTrail typically takes a few minutes to index a new event, but a short
    delay before the first lookup attempt noticeably improves the hit rate for
    events that are close to being indexed. This is a best-effort mitigation,
    not a guarantee - CloudTrail lag can still exceed this in some cases.
    """
    try:
        print(f"Waiting {CLOUDTRAIL_LOOKUP_DELAY_SECONDS}s before querying CloudTrail to allow for indexing lag...")
        time.sleep(CLOUDTRAIL_LOOKUP_DELAY_SECONDS)

        start_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        response = cloudtrail.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "EventName", "AttributeValue": "RunInstances"}
            ],
            StartTime=start_time,
            MaxResults=20,
        )

        print(f"CloudTrail lookup_events returned {len(response.get('Events', []))} RunInstances event(s)")

        for event_record in response.get("Events", []):
            resource_names = [
                r.get("ResourceName") for r in event_record.get("Resources", [])
            ]
            matched = instance_id in resource_names or instance_id in event_record.get(
                "CloudTrailEvent", ""
            )
            if matched:
                username = event_record.get("Username")
                if username:
                    print(f"Resolved launching user for {instance_id}: {username}")
                    return username

        print(f"Could not resolve launching user for {instance_id} (CloudTrail lag or event not found)")
        return None

    except Exception as exc:
        print(f"  ! CloudTrail lookup failed: {exc}")
        return None