import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import (
    Asset_Status_Enum,
    Email_Event_Type_Enum,
    Issue_Status_Enum,
    User_Role_Enum,
)
from utils.email_queue import send_email_event

from model import RequestReplacementRequest, RequestReplacementResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]
        issue_id = event["pathParameters"]["issue_id"]

        # Parse body and validate
        body = json.loads(event.get("body") or "{}")
        request = RequestReplacementRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check asset is in ISSUE_REPORTED status (asset domain — Asset_Status_Enum)
        if asset_item["Status"] != Asset_Status_Enum.ISSUE_REPORTED:
            raise ConflictException("Asset is not in ISSUE_REPORTED status")

        # Fetch issue record
        issue_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"}
        )
        if not issue_item:
            raise NotFoundException("Issue record not found")

        now = datetime.now(timezone.utc).isoformat()

        # TransactWriteItems: update Issue_Record only (no asset status change)
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": {"S": f"ASSET#{asset_id}"},
                            "SK": {"S": f"ISSUE#{issue_id}"},
                        },
                        "UpdateExpression": "SET #status = :new_status, #resolved_by = :resolved_by, #resolved_at = :resolved_at, #replacement_justification = :replacement_justification, #isipk = :isipk, #isisk = :isisk",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#resolved_by": "ResolvedBy",
                            "#resolved_at": "ResolvedAt",
                            "#replacement_justification": "ReplacementJustification",
                            "#isipk": "IssueStatusIndexPK",
                            "#isisk": "IssueStatusIndexSK",
                        },
                        "ExpressionAttributeValues": {
                            ":new_status": {
                                "S": Issue_Status_Enum.REPLACEMENT_REQUIRED
                            },
                            ":resolved_by": {"S": actor_id},
                            ":resolved_at": {"S": now},
                            ":replacement_justification": {
                                "S": request.replacement_justification
                            },
                            ":isipk": {
                                "S": f"ISSUE_STATUS#{Issue_Status_Enum.REPLACEMENT_REQUIRED.value}"
                            },
                            ":isisk": {
                                "S": f"ISSUE#{issue_item.get('IssueID', issue_item['SK'].replace('ISSUE#', ''))}"
                            },
                        },
                    }
                },
            ]
        )

        response = RequestReplacementResponse(
            asset_id=asset_id,
            issue_id=issue_id,
            status=Issue_Status_Enum.REPLACEMENT_REQUIRED,
        )

        # Queue email notification to Management via unified SQS pipeline
        send_email_event(
            Email_Event_Type_Enum.REPLACEMENT_REQUESTED,
            asset_id=asset_id,
            issue_description=issue_item.get("IssueDescription", ""),
            replacement_justification=request.replacement_justification,
        )

        return success(response.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
