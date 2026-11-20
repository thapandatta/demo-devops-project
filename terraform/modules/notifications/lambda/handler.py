import json
import os
from decimal import Decimal

import boto3

sns = boto3.client("sns")
TOPIC_ARN = os.environ["TOPIC_ARN"]


def unwrap(attribute):
    """Convert one DynamoDB-typed value, such as {"S": "x"} or {"N": "5"}, to plain Python."""
    kind, value = next(iter(attribute.items()))
    if kind == "S":
        return value
    if kind == "N":
        number = Decimal(value)
        return int(number) if number == number.to_integral_value() else float(number)
    if kind == "BOOL":
        return value
    if kind == "NULL":
        return None
    if kind == "L":
        return [unwrap(v) for v in value]
    if kind == "M":
        return {k: unwrap(v) for k, v in value.items()}
    return value


def lambda_handler(event, context):
    sent = 0

    for record in event.get("Records", []):
        # Only brand-new rows. MODIFY (PUT/update) and REMOVE are ignored
        if record.get("eventName") != "INSERT":
            continue

        new_image = record["dynamodb"].get("NewImage", {})
        item = {key: unwrap(value) for key, value in new_image.items()}

        subject = f"New item created: {item.get('name', 'unknown')}"[:100]
        body = (
            "A new row was created in DynamoDB.\n\n"
            f"ID:       {item.get('id')}\n"
            f"Name:     {item.get('name')}\n"
            f"Cost:     {item.get('cost')}\n"
            f"Quantity: {item.get('quantity')}\n\n"
            "Full record:\n"
            f"{json.dumps(item, indent=2, default=str)}\n"
        )

        sns.publish(TopicArn=TOPIC_ARN, Subject=subject, Message=body)
        sent += 1

    print(f"Processed {len(event.get('Records', []))} record(s), sent {sent} email(s)")
    return {"sent": sent}