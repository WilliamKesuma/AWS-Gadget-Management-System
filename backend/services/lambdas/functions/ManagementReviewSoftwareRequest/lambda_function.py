import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeSerializer
from pydantic import ValidationError

from custom_exceptions import NotFoundException, ConflictException
from utils import success, error, get_item
from utils.auth import require_group
from utils.enums import Software_Status_Enum, User_Role_Enum
from utils.models import AuditLogModel

from model import ManagementReviewRequest, ManagementReviewResponse

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
        actor_id = require_group(event, User_Role_Enum.MANAGEMENT)

        asset_id = event["pathParameters"]["asset_id"]
        software_request_id = event["pathParameters"]["software_request_id"]

        body = json.loads(event.get("body") or "{}")
        request = ManagementReviewRequest(**body)

        # Fetch the software installation record
        software_item = get_item(
            table, {"PK": f"ASSET#{asset_id}", "SK": f"SOFTWARE#{software_request_id}"}
        )
        if not software_item:
            raise NotFoundException("Software installation request not found")

        # Verify the request is in a state that allows management review
        if software_item["Status"] != Software_Status_Enum.ESCALATED_TO_MANAGEMENT:
            raise ConflictException(
                "This request is not in a state that allows management review"
            )

        # Determine new status based on decision
        status_map = {
            "APPROVE": Software_Status_Enum.SOFTWARE_INSTALL_APPROVED,
            "REJECT": Software_Status_Enum.SOFTWARE_INSTALL_REJECTED,
        }
        new_status = status_map[request.decision]

        review_now = datetime.now(timezone.utc).isoformat()

        # Build update fields
        update_fields = {
            "Status": new_status,
            "ManagementReviewedBy": actor_id,
            "ManagementReviewedAt": review_now,
            "SoftwareStatusIndexPK": f"SOFTWARE_STATUS#{new_status.value}",
            "SoftwareStatusIndexSK": f"SOFTWARE#{software_item.get('SoftwareRequestID', software_item['SK'].replace('SOFTWARE#', ''))}",
            "SoftwareEntityType": "SOFTWARE_REQUEST",
        }
        if request.decision == "APPROVE":
            update_fields["InstallationTimestamp"] = review_now
            if request.remarks:
                update_fields["ManagementRemarks"] = request.remarks
        elif request.decision == "REJECT":
            update_fields["ManagementRejectionReason"] = request.rejection_reason

        # Build UpdateExpression
        set_parts = [f"#{k} = :{k}" for k in update_fields]
        update_expr = "SET " + ", ".join(set_parts)
        expr_names = {f"#{k}": k for k in update_fields}
        expr_values = {
            f":{k}": serializer.serialize(v) for k, v in update_fields.items()
        }

        # Build audit log
        audit_log_kwargs = {
            "PK": f"ASSET#{asset_id}",
            "SK": f"LOG#{review_now}#{actor_id}",
            "ActorID": actor_id,
            "Phase": "SOFTWARE_INSTALL_MANAGEMENT_REVIEW",
            "PreviousStatus": Software_Status_Enum.ESCALATED_TO_MANAGEMENT,
            "NewStatus": new_status,
        }
        if request.decision == "REJECT":
            audit_log_kwargs["RejectionReason"] = request.rejection_reason

        audit_log = AuditLogModel(**audit_log_kwargs)
        audit_item = _serialize_item(audit_log.model_dump())

        # TransactWriteItems: update SOFTWARE# record + put audit log
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    "Update": {
                        "TableName": ASSETS_TABLE,
                        "Key": {
                            "PK": serializer.serialize(f"ASSET#{asset_id}"),
                            "SK": serializer.serialize(
                                f"SOFTWARE#{software_request_id}"
                            ),
                        },
                        "UpdateExpression": update_expr,
                        "ExpressionAttributeNames": expr_names,
                        "ExpressionAttributeValues": expr_values,
                    }
                },
                {"Put": {"TableName": ASSETS_TABLE, "Item": audit_item}},
            ]
        )

        response = ManagementReviewResponse(
            asset_id=asset_id,
            software_request_id=software_request_id,
            status=new_status,
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
