"""
Daily AWS Cost Alert using Cost Explorer API + SNS.

Environment variables:
    SNS_TOPIC_ARN        - ARN of the SNS topic to publish alerts to
    COST_THRESHOLD_USD   - (optional) alert threshold in USD, default 50
"""

import os
from datetime import date

import boto3

ce = boto3.client("ce")
sns = boto3.client("sns")

SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
COST_THRESHOLD_USD = float(os.environ.get("COST_THRESHOLD_USD", "50"))


def lambda_handler(event, context):
    today = date.today()
    start_of_month = today.replace(day=1).isoformat()
    end_date = today.isoformat()

    # Cost Explorer requires Start < End; if today is the 1st, query yesterday-to-today.
    if start_of_month == end_date:
        response = ce.get_cost_and_usage(
            TimePeriod={"Start": end_date, "End": end_date},
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
    else:
        response = ce.get_cost_and_usage(
            TimePeriod={"Start": start_of_month, "End": end_date},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )

    results = response.get("ResultsByTime", [])
    amount = 0.0
    unit = "USD"
    if results:
        cost_data = results[0]["Total"]["UnblendedCost"]
        amount = float(cost_data["Amount"])
        unit = cost_data["Unit"]

    print(f"Month-to-date spend ({start_of_month} to {end_date}): {amount:.2f} {unit}")

    alert_sent = False
    if amount > COST_THRESHOLD_USD:
        message = (
            f"AWS spend alert: month-to-date cost is {amount:.2f} {unit}, "
            f"which exceeds your threshold of {COST_THRESHOLD_USD:.2f} {unit}.\n\n"
            f"Period: {start_of_month} to {end_date}"
        )
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"AWS Cost Alert: ${amount:.2f} MTD (threshold ${COST_THRESHOLD_USD:.2f})",
            Message=message,
        )
        alert_sent = True
        print("Threshold exceeded - SNS alert published.")
    else:
        print("Spend is within threshold - no alert sent.")

    return {
        "month_to_date_spend": amount,
        "currency": unit,
        "threshold": COST_THRESHOLD_USD,
        "alert_sent": alert_sent,
    }
