import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key

from utils import error, success
from utils.auth import require_group
from utils.enums import Approval_Type_Enum, User_Role_Enum
from utils.user_resolver import resolve_user_names, collect_user_ids

from model import ApprovalHubItem, ApprovalHubResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)

MAX_ITEMS = 3


def _fetch_pending_asset_creations() -> list[dict]:
    """Fetch assets in ASSET_PENDING_APPROVAL status."""
    response = table.query(
        IndexName="StatusIndex",
        KeyConditionExpression=Key("StatusIndexPK").eq("STATUS#ASSET_PENDING_APPROVAL"),
        ScanIndexForward=False,
        Limit=MAX_ITEMS,
    )
    items = []
    for item in response.get("Items", []):
        asset_id = item["PK"].replace("ASSET#", "")
        items.append(
            {
                "approval_type": Approval_Type_Enum.ASSET_CREATION,
                "target_id": asset_id,
                "title": f"{item.get('Brand', '')} {item.get('Model', '')}".strip()
                or asset_id,
                "subtitle": item.get("ProductDescription", item.get("Category", "")),
                "requester_id": item.get("CreatedBy", ""),
                "created_at": item.get("CreatedAt", ""),
            }
        )
    return items


def _fetch_pending_replacements() -> list[dict]:
    """Fetch issues in REPLACEMENT_REQUIRED status."""
    response = table.query(
        IndexName="IssueStatusIndex",
        KeyConditionExpression=Key("IssueStatusIndexPK").eq(
            "ISSUE_STATUS#REPLACEMENT_REQUIRED"
        ),
        ScanIndexForward=False,
        Limit=MAX_ITEMS,
    )
    items = []
    for item in response.get("Items", []):
        asset_id = item["PK"].replace("ASSET#", "")
        issue_id = item.get("IssueID", item["SK"].replace("ISSUE#", ""))
        # Fetch asset metadata for title
        asset_item = table.get_item(
            Key={"PK": f"ASSET#{asset_id}", "SK": "METADATA"}
        ).get("Item", {})
        items.append(
            {
                "approval_type": Approval_Type_Enum.REPLACEMENT,
                "target_id": issue_id,
                "title": f"{asset_item.get('Brand', '')} {asset_item.get('Model', '')}".strip()
                or asset_id,
                "subtitle": item.get("IssueDescription", "")[:80],
                "requester_id": item.get("ReportedBy", ""),
                "created_at": item.get("CreatedAt", ""),
            }
        )
    return items


def _fetch_pending_software_escalations() -> list[dict]:
    """Fetch software requests in ESCALATED_TO_MANAGEMENT status."""
    response = table.query(
        IndexName="SoftwareStatusIndex",
        KeyConditionExpression=Key("SoftwareStatusIndexPK").eq(
            "SOFTWARE_STATUS#ESCALATED_TO_MANAGEMENT"
        ),
        ScanIndexForward=False,
        Limit=MAX_ITEMS,
    )
    items = []
    for item in response.get("Items", []):
        sw_id = item.get("SoftwareRequestID", item["SK"].replace("SOFTWARE#", ""))
        items.append(
            {
                "approval_type": Approval_Type_Enum.SOFTWARE_ESCALATION,
                "target_id": sw_id,
                "title": item.get("SoftwareName", ""),
                "subtitle": item.get("Justification", "")[:80],
                "requester_id": item.get("RequestedBy", ""),
                "created_at": item.get("CreatedAt", ""),
            }
        )
    return items


def _fetch_pending_disposals() -> list[dict]:
    """Fetch disposals in DISPOSAL_PENDING status (via asset StatusIndex)."""
    response = table.query(
        IndexName="StatusIndex",
        KeyConditionExpression=Key("StatusIndexPK").eq("STATUS#DISPOSAL_PENDING"),
        ScanIndexForward=False,
        Limit=MAX_ITEMS,
    )
    items = []
    for item in response.get("Items", []):
        asset_id = item["PK"].replace("ASSET#", "")
        # Fetch the disposal record for this asset
        disposal_resp = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("DISPOSAL#"),
            ScanIndexForward=False,
            Limit=1,
        )
        disposal_items = disposal_resp.get("Items", [])
        if disposal_items:
            d = disposal_items[0]
            disposal_id = d.get("DisposalID", d["SK"].replace("DISPOSAL#", ""))
            items.append(
                {
                    "approval_type": Approval_Type_Enum.DISPOSAL,
                    "target_id": disposal_id,
                    "title": f"{item.get('Brand', '')} {item.get('Model', '')}".strip()
                    or asset_id,
                    "subtitle": d.get("DisposalReason", ""),
                    "requester_id": d.get("InitiatedBy", ""),
                    "created_at": d.get("InitiatedAt", ""),
                }
            )
    return items


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        require_group(event, User_Role_Enum.MANAGEMENT)

        # Gather candidates from all approval sources
        all_items = []
        all_items.extend(_fetch_pending_asset_creations())
        all_items.extend(_fetch_pending_replacements())
        all_items.extend(_fetch_pending_software_escalations())
        all_items.extend(_fetch_pending_disposals())

        # Sort by created_at descending, take top 3
        all_items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        top_items = all_items[:MAX_ITEMS]

        # Resolve requester names
        user_ids = collect_user_ids(*(item.get("requester_id") for item in top_items))
        names = resolve_user_names(table, user_ids)

        result = []
        for item in top_items:
            requester_id = item.pop("requester_id", "")
            item["requester_name"] = names.get(requester_id, requester_id)
            result.append(ApprovalHubItem(**item))

        return success(ApprovalHubResponse(items=result).model_dump())

    except PermissionError as e:
        return error(str(e), 403)
    except Exception:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
