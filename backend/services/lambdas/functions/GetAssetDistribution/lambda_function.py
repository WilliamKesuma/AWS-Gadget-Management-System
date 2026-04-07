import os

import boto3
from aws_lambda_powertools import Logger, Tracer

from utils import error, get_item, success
from utils.auth import require_roles
from utils.enums import User_Role_Enum

from model import AssetDistributionItem, AssetDistributionResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

DASHBOARD_KEY = {"PK": "DASHBOARD_COUNTERS", "SK": "METADATA"}
MAX_CATEGORIES = 5


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_roles(event, [User_Role_Enum.IT_ADMIN, User_Role_Enum.MANAGEMENT])

        item = get_item(table, DASHBOARD_KEY)
        category_counts = item.get("CategoryCounts", {}) if item else {}

        # Sort descending by count
        sorted_cats = sorted(
            category_counts.items(), key=lambda x: int(x[1]), reverse=True
        )

        items = []
        if len(sorted_cats) <= MAX_CATEGORIES:
            items = [
                AssetDistributionItem(category=cat, count=int(cnt))
                for cat, cnt in sorted_cats
            ]
        else:
            # Top 4 + aggregate the rest as "Others"
            for cat, cnt in sorted_cats[:4]:
                items.append(AssetDistributionItem(category=cat, count=int(cnt)))
            others_count = sum(int(cnt) for _, cnt in sorted_cats[4:])
            items.append(AssetDistributionItem(category="Others", count=others_count))

        # Filter out zero-count categories
        items = [i for i in items if i.count > 0]

        response = AssetDistributionResponse(items=items)
        return success(response.model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
