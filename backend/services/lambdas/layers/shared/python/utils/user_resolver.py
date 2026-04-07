"""Batch-resolve user IDs to display names via DynamoDB USER# records."""

from typing import Optional

import boto3
from aws_lambda_powertools import Logger

logger = Logger()

dynamodb = boto3.resource("dynamodb")


def resolve_user_names(table, user_ids: set[str]) -> dict[str, str]:
    """Batch-fetch user fullnames for a set of user IDs.

    Args:
        table: DynamoDB Table resource for the assets table.
        user_ids: Set of Cognito sub (user ID) strings.

    Returns:
        Dict mapping user_id → Fullname. Missing users fall back to their ID.
    """
    if not user_ids:
        return {}

    result: dict[str, str] = {}

    # DynamoDB BatchGetItem supports max 100 keys per call
    id_list = list(user_ids)
    for i in range(0, len(id_list), 100):
        batch = id_list[i : i + 100]

        response = dynamodb.batch_get_item(
            RequestItems={
                table.name: {
                    "Keys": [{"PK": f"USER#{uid}", "SK": "METADATA"} for uid in batch],
                    "ProjectionExpression": "PK, Fullname",
                }
            }
        )

        for item in response.get("Responses", {}).get(table.name, []):
            uid = item["PK"].replace("USER#", "")
            result[uid] = item.get("Fullname", uid)

        # Handle unprocessed keys
        unprocessed = response.get("UnprocessedKeys", {}).get(table.name)
        while unprocessed:
            response = dynamodb.batch_get_item(RequestItems={table.name: unprocessed})
            for item in response.get("Responses", {}).get(table.name, []):
                uid = item["PK"].replace("USER#", "")
                result[uid] = item.get("Fullname", uid)
            unprocessed = response.get("UnprocessedKeys", {}).get(table.name)

    # Fall back to user ID for any IDs not found
    for uid in user_ids:
        if uid not in result:
            logger.warning(f"User not found for ID: {uid}, falling back to ID")
            result[uid] = uid

    return result


def collect_user_ids(*values: Optional[str]) -> set[str]:
    """Collect non-None user ID strings into a set."""
    return {v for v in values if v is not None}
