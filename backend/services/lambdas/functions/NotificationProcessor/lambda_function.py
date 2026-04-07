import os
import uuid
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Key, Attr
from boto3.dynamodb.types import TypeDeserializer

from utils.enums import User_Status_Enum
from rules import NOTIFICATION_RULES
from model import StreamRecordData, NotificationItem

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
CONNECTIONS_TABLE = os.environ.get("CONNECTIONS_TABLE", "")
WS_ENDPOINT = os.environ.get("WS_ENDPOINT", "")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
connections_table = dynamodb.Table(CONNECTIONS_TABLE) if CONNECTIONS_TABLE else None
deserializer = TypeDeserializer()

# API Gateway Management API client (lazy init)
_apigw_management = None


def _get_apigw_management():
    """Lazy-init the API Gateway Management API client."""
    global _apigw_management
    if _apigw_management is None and WS_ENDPOINT:
        # Convert wss://xxx.execute-api.region.amazonaws.com/stage
        # to https://xxx.execute-api.region.amazonaws.com/stage
        endpoint_url = WS_ENDPOINT.replace("wss://", "https://")
        _apigw_management = boto3.client(
            "apigatewaymanagementapi", endpoint_url=endpoint_url
        )
    return _apigw_management


def _deserialize_image(image: dict) -> dict:
    """Convert a DynamoDB JSON image to a plain Python dict."""
    return {k: deserializer.deserialize(v) for k, v in image.items()}


def _get_entity_prefix(sk: str) -> str:
    """Determine the entity type from the SK value.

    Returns the SK prefix used to match notification rules:
    - 'METADATA' for asset metadata records
    - 'ISSUE#', 'SOFTWARE#', 'HANDOVER#', 'DISPOSAL#', 'RETURN#', 'AUDIT#' for sub-records
    """
    if sk == "METADATA":
        return "METADATA"
    for prefix in (
        "ISSUE#",
        "SOFTWARE#",
        "HANDOVER#",
        "DISPOSAL#",
        "RETURN#",
        "AUDIT#",
    ):
        if sk.startswith(prefix):
            return prefix
    return sk.split("#")[0] + "#" if "#" in sk else sk


def _extract_reference_id(new_image: dict, entity_prefix: str) -> str:
    """Extract the reference ID from the source record.

    - METADATA (assets): strip 'ASSET#' prefix from PK
    - ISSUE#, SOFTWARE#, AUDIT#: use asset_id from PK (frontend routes need /assets/:asset_id/...)
    - HANDOVER#, DISPOSAL#, RETURN#: extract the sub-record ID from SK
    """
    pk = new_image.get("PK", "")
    asset_id = pk.replace("ASSET#", "") if pk.startswith("ASSET#") else pk

    if entity_prefix == "METADATA":
        return asset_id

    # For ISSUE, SOFTWARE, AUDIT — the frontend navigates to the asset's sub-page,
    # so the asset_id is the correct reference (sub-record ID alone is not routable)
    if entity_prefix in ("ISSUE#", "SOFTWARE#", "AUDIT#"):
        return asset_id

    # For HANDOVER, DISPOSAL, RETURN — the notification message references the asset,
    # so return the asset_id extracted from PK (same as ISSUE/SOFTWARE/AUDIT)
    return asset_id


def find_matching_rules(record_data: StreamRecordData) -> list[dict]:
    """Compare a stream record against NOTIFICATION_RULES and return all matches.

    Handles three trigger types:
    - STATUS_CHANGE: status_field changed between OldImage and NewImage, to_status matches
    - FIELD_CHANGE: field present in NewImage but absent/None in OldImage (MODIFY only)
    - INSERT: entity_prefix matches and event is INSERT
    """
    matched = []

    for rule in NOTIFICATION_RULES:
        trigger = rule["trigger_type"]
        if rule["entity_prefix"] != record_data.entity_prefix:
            continue

        if trigger == "STATUS_CHANGE" and record_data.event_name == "MODIFY":
            field = rule["status_field"]
            old_val = (record_data.old_image or {}).get(field)
            new_val = (record_data.new_image or {}).get(field)

            # Status must have actually changed
            if old_val == new_val:
                continue

            # to_status must match
            if rule["to_status"] is not None and new_val != rule["to_status"]:
                continue

            # from_status must match if specified
            if rule["from_status"] is not None and old_val != rule["from_status"]:
                continue

            matched.append(rule)

        elif trigger == "FIELD_CHANGE" and record_data.event_name == "MODIFY":
            field = rule["status_field"]
            old_val = (record_data.old_image or {}).get(field)
            new_val = (record_data.new_image or {}).get(field)

            # Field is present in NewImage but absent/None in OldImage
            if new_val is not None and (old_val is None):
                matched.append(rule)

        elif trigger == "INSERT" and record_data.event_name == "INSERT":
            # Optional PK prefix filter to distinguish asset vs user METADATA records
            pk_prefix = rule.get("pk_prefix")
            if pk_prefix is not None:
                pk = (record_data.new_image or {}).get("PK", "")
                if not pk.startswith(pk_prefix):
                    continue

            # Optional status value check on the inserted record
            to_status = rule.get("to_status")
            if to_status is not None:
                field = rule.get("status_field")
                if field and (record_data.new_image or {}).get(field) != to_status:
                    continue

            matched.append(rule)

    return matched


def resolve_recipients(rule: dict, new_image: dict) -> list[str]:
    """Resolve the list of recipient user IDs for a matched rule.

    - Role-based (target_role is set): query EntityTypeIndex GSI for active users with that role
    - User-specific (target_role is None, recipient_field is set): extract user ID from source record
    """
    target_role = rule.get("target_role")
    recipient_field = rule.get("recipient_field")

    if target_role is not None:
        # Role-based: query for all active users with the target role
        response = table.query(
            IndexName="EntityTypeIndex",
            KeyConditionExpression=Key("EntityType").eq("USER"),
            FilterExpression=Attr("Role").eq(target_role)
            & Attr("Status").eq(User_Status_Enum.ACTIVE),
        )
        user_ids = []
        for item in response.get("Items", []):
            user_id = item.get("UserID") or item.get("PK", "").replace("USER#", "")
            if user_id:
                user_ids.append(user_id)

        if not user_ids:
            logger.info(
                "No active users found for role",
                role=target_role,
                notification_type=rule["notification_type"],
            )
        return user_ids

    if recipient_field is not None:
        raw_value = new_image.get(recipient_field)
        if not raw_value:
            logger.info(
                "Recipient field missing or empty in source record",
                recipient_field=recipient_field,
                notification_type=rule["notification_type"],
            )
            return []

        # Strip EMPLOYEE# prefix for EmployeeAssetIndexPK field
        user_id = str(raw_value)
        if recipient_field == "EmployeeAssetIndexPK" and user_id.startswith(
            "EMPLOYEE#"
        ):
            user_id = user_id.replace("EMPLOYEE#", "", 1)

        return [user_id]

    return []


def create_notifications(recipients: list[str], rule: dict, reference_id: str) -> None:
    """Write notification records to DynamoDB using batch_writer.

    Creates one notification per recipient with all required attributes.
    Also increments UnreadNotificationCount on each recipient's USER metadata.
    """
    if not recipients:
        return

    now = datetime.now(timezone.utc)
    created_at = now.isoformat()
    expires_at = int(now.timestamp()) + 7_776_000  # 90 days
    message = rule["message_template"].format(reference_id=reference_id)

    with table.batch_writer() as batch:
        for user_id in recipients:
            notification_id = str(uuid.uuid4())
            item = {
                "PK": f"USER#{user_id}",
                "SK": f"NOTIFICATION#{created_at}#{notification_id}",
                "NotificationType": rule["notification_type"],
                "Title": rule["title"],
                "Message": message,
                "ReferenceID": reference_id,
                "ReferenceType": rule["reference_type"],
                "IsRead": False,
                "CreatedAt": created_at,
                "ExpiresAt": expires_at,
                "TTL": expires_at,
                "EntityType": "NOTIFICATION",
            }
            batch.put_item(Item=item)

    # Increment UnreadNotificationCount on each recipient's USER metadata
    for user_id in recipients:
        try:
            table.update_item(
                Key={"PK": f"USER#{user_id}", "SK": "METADATA"},
                UpdateExpression="ADD #unc :one",
                ExpressionAttributeNames={"#unc": "UnreadNotificationCount"},
                ExpressionAttributeValues={":one": 1},
            )
        except Exception:
            logger.exception(
                "Failed to increment UnreadNotificationCount",
                user_id=user_id,
            )

    logger.info(
        "Notifications created",
        notification_type=rule["notification_type"],
        recipient_count=len(recipients),
        reference_id=reference_id,
    )


def push_ws_notifications(recipients: list[str], rule: dict, reference_id: str) -> None:
    """Push real-time notification to connected WebSocket clients.

    Looks up each recipient's active connections and sends the notification
    payload. Stale connections are cleaned up automatically.
    """
    if not connections_table or not WS_ENDPOINT:
        return

    apigw = _get_apigw_management()
    if not apigw:
        return

    message = rule["message_template"].format(reference_id=reference_id)
    payload = json.dumps(
        {
            "type": "notification",
            "data": {
                "notification_type": rule["notification_type"],
                "title": rule["title"],
                "message": message,
                "reference_id": reference_id,
                "reference_type": rule["reference_type"],
            },
        }
    )

    for user_id in recipients:
        try:
            response = connections_table.query(
                IndexName="UserIDIndex",
                KeyConditionExpression=Key("UserID").eq(user_id),
            )
            for conn in response.get("Items", []):
                connection_id = conn["ConnectionID"]
                try:
                    apigw.post_to_connection(ConnectionId=connection_id, Data=payload)
                except apigw.exceptions.GoneException:
                    # Connection is stale — clean up
                    connections_table.delete_item(Key={"ConnectionID": connection_id})
                    logger.info("Removed stale connection", connection_id=connection_id)
                except Exception:
                    logger.exception(
                        "Failed to push to connection",
                        connection_id=connection_id,
                    )
        except Exception:
            logger.exception("Failed to query connections for user", user_id=user_id)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Process DynamoDB Stream events and generate notification records."""
    records = event.get("Records", [])
    logger.info("Processing stream batch", record_count=len(records))

    for record in records:
        try:
            event_name = record.get("eventName", "")
            dynamodb_record = record.get("dynamodb", {})

            # Deserialize images
            raw_new = dynamodb_record.get("NewImage")
            raw_old = dynamodb_record.get("OldImage")

            new_image = _deserialize_image(raw_new) if raw_new else None
            old_image = _deserialize_image(raw_old) if raw_old else None

            # Determine entity prefix from SK
            sk = ""
            if new_image:
                sk = new_image.get("SK", "")
            elif old_image:
                sk = old_image.get("SK", "")

            if not sk:
                logger.info("Skipping record with no SK", event_name=event_name)
                continue

            entity_prefix = _get_entity_prefix(sk)

            record_data = StreamRecordData(
                event_name=event_name,
                entity_prefix=entity_prefix,
                old_image=old_image,
                new_image=new_image,
            )

            # Find matching notification rules
            matched_rules = find_matching_rules(record_data)

            if not matched_rules:
                continue

            # Process each matched rule
            for rule in matched_rules:
                reference_id = _extract_reference_id(new_image or {}, entity_prefix)
                recipients = resolve_recipients(rule, new_image or {})
                create_notifications(recipients, rule, reference_id)
                push_ws_notifications(recipients, rule, reference_id)

        except Exception:
            logger.exception(
                "Error processing stream record",
                record=record,
            )
            # Continue processing remaining records — do NOT re-raise
            continue
