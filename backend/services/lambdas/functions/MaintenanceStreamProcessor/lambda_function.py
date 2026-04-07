import os

import boto3
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.types import TypeDeserializer

from utils.enums import Maintenance_Record_Type_Enum

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
deserializer = TypeDeserializer()

# SK prefix → (MaintenanceRecordType, timestamp field name)
SK_PREFIX_MAP = {
    "ISSUE#": (Maintenance_Record_Type_Enum.ISSUE, "CreatedAt"),
    "SOFTWARE#": (Maintenance_Record_Type_Enum.SOFTWARE_REQUEST, "CreatedAt"),
    "RETURN#": (Maintenance_Record_Type_Enum.RETURN, "InitiatedAt"),
    "DISPOSAL#": (Maintenance_Record_Type_Enum.DISPOSAL, "InitiatedAt"),
}


def _deserialize_image(image: dict) -> dict:
    return {k: deserializer.deserialize(v) for k, v in image.items()}


def _get_matching_prefix(sk: str) -> str | None:
    """Return the matching SK prefix if this record is a maintenance entity."""
    for prefix in SK_PREFIX_MAP:
        if sk.startswith(prefix):
            return prefix
    return None


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    """Process DynamoDB Stream INSERT events and backfill MaintenanceEntityIndex GSI fields."""
    records = event.get("Records", [])
    logger.info("Processing stream batch", record_count=len(records))

    for record in records:
        try:
            event_name = record.get("eventName", "")
            if event_name != "INSERT":
                continue

            dynamodb_record = record.get("dynamodb", {})
            raw_new = dynamodb_record.get("NewImage")
            if not raw_new:
                continue

            new_image = _deserialize_image(raw_new)
            pk = new_image.get("PK", "")
            sk = new_image.get("SK", "")

            if not pk or not sk:
                continue

            prefix = _get_matching_prefix(sk)
            if not prefix:
                continue

            # Skip if already populated (idempotency)
            if new_image.get("MaintenanceEntityType"):
                continue

            record_type_enum, timestamp_field = SK_PREFIX_MAP[prefix]
            timestamp = new_image.get(timestamp_field, "")

            if not timestamp:
                logger.warning(
                    "Missing timestamp field, skipping",
                    pk=pk,
                    sk=sk,
                    timestamp_field=timestamp_field,
                )
                continue

            table.update_item(
                Key={"PK": pk, "SK": sk},
                UpdateExpression="SET #met = :met, #mts = :mts, #mrt = :mrt",
                ExpressionAttributeNames={
                    "#met": "MaintenanceEntityType",
                    "#mts": "MaintenanceTimestamp",
                    "#mrt": "MaintenanceRecordType",
                },
                ExpressionAttributeValues={
                    ":met": "MAINTENANCE",
                    ":mts": timestamp,
                    ":mrt": record_type_enum.value,
                },
            )

            logger.info(
                "Backfilled maintenance GSI fields",
                pk=pk,
                sk=sk,
                record_type=record_type_enum.value,
            )

        except Exception:
            logger.exception("Error processing stream record", record=record)
            continue
