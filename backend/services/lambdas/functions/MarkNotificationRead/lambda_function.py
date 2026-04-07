import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key

from utils import success, error
from utils.auth import get_caller_info

from model import MarkNotificationReadItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        caller_user_id, _groups = get_caller_info(event)

        path_params = event.get("pathParameters") or {}
        notification_id = path_params.get("notification_id")
        if not notification_id:
            return error("notification_id is required", 400)

        # Query for notifications belonging to this user
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{caller_user_id}")
            & Key("SK").begins_with("NOTIFICATION#"),
        )
        items = response.get("Items", [])

        # Handle pagination in case of many notifications
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"USER#{caller_user_id}")
                & Key("SK").begins_with("NOTIFICATION#"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Find the item whose SK contains the notification_id
        matched_item = None
        for item in items:
            if notification_id in item["SK"]:
                matched_item = item
                break

        if not matched_item:
            return error("Notification not found", 404)

        # Update IsRead to true
        table.update_item(
            Key={"PK": matched_item["PK"], "SK": matched_item["SK"]},
            UpdateExpression="SET IsRead = :val",
            ExpressionAttributeValues={":val": True},
        )

        # Extract notification_id from SK
        sk_parts = matched_item["SK"].split("#")
        extracted_id = sk_parts[-1]

        result = MarkNotificationReadItem(
            notification_id=extracted_id,
            notification_type=matched_item["NotificationType"],
            title=matched_item["Title"],
            message=matched_item["Message"],
            reference_id=matched_item["ReferenceID"],
            reference_type=matched_item["ReferenceType"],
            is_read=True,
            created_at=matched_item["CreatedAt"],
        )

        return success(result.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        caller_user_id, _groups = get_caller_info(event)

        path_params = event.get("pathParameters") or {}
        notification_id = path_params.get("notification_id")
        if not notification_id:
            return error("notification_id is required", 400)

        # Query for notifications belonging to this user
        response = table.query(
            KeyConditionExpression=Key("PK").eq(f"USER#{caller_user_id}")
            & Key("SK").begins_with("NOTIFICATION#"),
        )
        items = response.get("Items", [])

        # Handle pagination in case of many notifications
        while "LastEvaluatedKey" in response:
            response = table.query(
                KeyConditionExpression=Key("PK").eq(f"USER#{caller_user_id}")
                & Key("SK").begins_with("NOTIFICATION#"),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))

        # Find the item whose SK contains the notification_id
        matched_item = None
        for item in items:
            if notification_id in item["SK"]:
                matched_item = item
                break

        if not matched_item:
            return error("Notification not found", 404)

        # Only decrement counter if transitioning from unread to read
        was_unread = not matched_item.get("IsRead", False)

        # Update IsRead to true
        table.update_item(
            Key={"PK": matched_item["PK"], "SK": matched_item["SK"]},
            UpdateExpression="SET IsRead = :val",
            ExpressionAttributeValues={":val": True},
        )

        # Decrement UnreadNotificationCount on the user record
        if was_unread:
            try:
                table.update_item(
                    Key={"PK": f"USER#{caller_user_id}", "SK": "METADATA"},
                    UpdateExpression="ADD #unc :neg",
                    ExpressionAttributeNames={"#unc": "UnreadNotificationCount"},
                    ExpressionAttributeValues={":neg": -1},
                )
            except Exception:
                logger.exception("Failed to decrement UnreadNotificationCount")

        # Extract notification_id from SK
        sk_parts = matched_item["SK"].split("#")
        extracted_id = sk_parts[-1]

        result = MarkNotificationReadItem(
            notification_id=extracted_id,
            notification_type=matched_item["NotificationType"],
            title=matched_item["Title"],
            message=matched_item["Message"],
            reference_id=matched_item["ReferenceID"],
            reference_type=matched_item["ReferenceType"],
            is_read=True,
            created_at=matched_item["CreatedAt"],
        )

        return success(result.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
