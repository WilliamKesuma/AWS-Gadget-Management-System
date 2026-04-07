import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import ConflictException, NotFoundException
from utils import error, get_item, success, check_record_lock
from utils.auth import require_group
from utils.enums import Asset_Status_Enum, User_Role_Enum
from utils.models import AuditLogModel, AssetMetadataModel

from model import CancelAssignmentResponse

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
        actor_id = require_group(event, User_Role_Enum.IT_ADMIN)

        asset_id = event["pathParameters"]["asset_id"]

        # Fetch asset metadata
        asset_item = get_item(table, {"PK": f"ASSET#{asset_id}", "SK": "METADATA"})
        if not asset_item:
            raise NotFoundException("Asset not found")

        # Check record lock before any other validation
        check_record_lock(asset_item)

        asset = AssetMetadataModel(**asset_item)

        # If asset is ASSIGNED, cancellation is not allowed
        if asset.Status == Asset_Status_Enum.ASSIGNED:
            raise ConflictException(
                "Cannot cancel assignment after employee has accepted the handover"
            )

        # Query for Handover_Record (latest first)
        handover_results = table.query(
            KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
            & Key("SK").begins_with("HANDOVER#"),
            ScanIndexForward=False,
        )["Items"]
        if not handover_results:
            raise NotFoundException("No pending assignment found for this asset")

        # Get the latest Handover_Record
        handover_record = handover_results[0]

        # Generate timestamp
        now = datetime.now(timezone.utc).isoformat()

        # Build AuditLogModel
        audit_log = AuditLogModel(
            PK=f"ASSET#{asset_id}",
            SK=f"LOG#{now}#{actor_id}",
            ActorID=actor_id,
            Phase="ASSET_ASSIGNMENT_CANCELLED",
            PreviousStatus=Asset_Status_Enum.IN_STOCK,
            NewStatus=Asset_Status_Enum.IN_STOCK,
        )

        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: delete Handover_Record, clear GSI keys, put AuditLog
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Delete": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(handover_record["PK"]),
                            "SK": serializer.serialize(handover_record["SK"]),
                        },
                    }
                },
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize("METADATA"),
                        },
                        "UpdateExpression": "REMOVE #eapk, #eask",
                        "ConditionExpression": "#status = :expected_status",
                        "ExpressionAttributeNames": {
                            "#eapk": "EmployeeAssetIndexPK",
                            "#eask": "EmployeeAssetIndexSK",
                            "#status": "Status",
                        },
                        "ExpressionAttributeValues": {
                            ":expected_status": serializer.serialize(
                                Asset_Status_Enum.IN_STOCK
                            ),
                        },
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        response_model = CancelAssignmentResponse(
            asset_id=asset_id,
            status=Asset_Status_Enum.IN_STOCK,
        )
        return success(response_model.model_dump())

    except ValidationError as e:
        return error(str(e), 400)
    except PermissionError as e:
        return error(str(e), 403)
    except NotFoundException as e:
        return error(str(e), 404)
    except ConflictException as e:
        return error(str(e), 409)
    except dynamodb_client.exceptions.TransactionCanceledException:
        return error("Asset status changed concurrently. Please retry.", 409)
    except Exception as e:
        logger.exception("Unhandled error")
        return error("Internal server error", 500)
