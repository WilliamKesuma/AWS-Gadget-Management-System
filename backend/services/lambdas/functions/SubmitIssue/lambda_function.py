import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import (
    Asset_Status_Enum,
    Email_Event_Type_Enum,
    Issue_Status_Enum,
    Maintenance_Record_Type_Enum,
    User_Role_Enum,
)
from utils.models import AssetMetadataModel, IssueRepairModel
from utils.id_generator import generate_domain_id
from utils.email_queue import send_email_event

from model import SubmitIssueRequest, SubmitIssueResponse

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
serializer = TypeSerializer()


def _serialize_item(item: dict) -> dict:
    """Convert a Python dict to DynamoDB JSON format."""
    return {k: serializer.serialize(v) for k, v in item.items() if v is not None}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        actor_id = require_group(event, User_Role_Enum.EMPLOYEE)

        asset_id = event["pathParameters"]["asset_id"]

        body = json.loads(event.get("body") or "{}")
        request = SubmitIssueRequest(**body)

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        asset = AssetMetadataModel(**asset_item)

        # Check asset is in ASSIGNED status
        if asset.Status != Asset_Status_Enum.ASSIGNED:
            raise ConflictException(
                "Issue reports are only allowed for assets in ASSIGNED status"
            )

        # Query latest handover record to verify employee assignment
        handover_response = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#"),
            ScanIndexForward=False,
            Limit=1,
        )
        handover_items = handover_response.get("Items", [])

        if not handover_items or handover_items[0].get("EmployeeID") != actor_id:
            raise PermissionError("You are not assigned to this asset")

        # Generate issue ID and timestamp
        issue_id = generate_domain_id(table, "ISSUE")
        now = datetime.now(timezone.utc).isoformat()

        # Build IssueRepairModel
        issue_record = IssueRepairModel(
            PK=f"ASSET#{asset_id}",
            SK=f"ISSUE#{issue_id}",
            IssueID=issue_id,
            IssueDescription=request.issue_description,
            Category=request.category,
            Status=Issue_Status_Enum.TROUBLESHOOTING,
            ActionPath=None,
            ReportedBy=actor_id,
            CreatedAt=now,
            IssueStatusIndexPK=f"ISSUE_STATUS#{Issue_Status_Enum.TROUBLESHOOTING.value}",
            IssueStatusIndexSK=f"ISSUE#{issue_id}",
        )

        # Serialize items
        issue_item = _serialize_item(issue_record.model_dump())

        # TransactWriteItems: put Issue_Record + update Asset_Record status
        dynamodb_client.transact_write_items(
            TransactItems=[
                {"Put": {"TableName": ASSETS_TABLE, "Item": issue_item}},
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": {"S": f"ASSET#{asset_id}"},
                            "SK": {"S": "METADATA"},
                        },
                        "UpdateExpression": "SET #status = :new_status, #sipk = :sipk, #sisk = :sisk",
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#status": "Status",
                            "#sipk": "StatusIndexPK",
                            "#sisk": "StatusIndexSK",
                        },
                        "ExpressionAttributeValues": {
                            ":new_status": {"S": Asset_Status_Enum.ISSUE_REPORTED},
                            ":expected_status": {"S": Asset_Status_Enum.ASSIGNED},
                            ":sipk": {
                                "S": f"STATUS#{Asset_Status_Enum.ISSUE_REPORTED.value}"
                            },
                            ":sisk": {"S": f"ASSET#{asset_id}"},
                        },
                    }
                },
            ]
        )

        # Backfill MaintenanceEntityIndex GSI fields — transact_write_items does not trigger streams
        table.update_item(
            Key={"PK": f"ASSET#{asset_id}", "SK": f"ISSUE#{issue_id}"},
            UpdateExpression="SET #met = :met, #mts = :mts, #mrt = :mrt",
            ExpressionAttributeNames={
                "#met": "MaintenanceEntityType",
                "#mts": "MaintenanceTimestamp",
                "#mrt": "MaintenanceRecordType",
            },
            ExpressionAttributeValues={
                ":met": "MAINTENANCE",
                ":mts": now,
                ":mrt": Maintenance_Record_Type_Enum.ISSUE,
            },
        )

        response = SubmitIssueResponse(
            asset_id=asset_id,
            issue_id=issue_id,
            status=Issue_Status_Enum.TROUBLESHOOTING,
        )

        # Queue email notification to IT Admins via unified SQS pipeline
        send_email_event(
            Email_Event_Type_Enum.ISSUE_SUBMITTED,
            asset_id=asset_id,
            actor_name=handover_items[0].get("EmployeeName", actor_id),
            actor_id=actor_id,
            issue_description=request.issue_description,
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
