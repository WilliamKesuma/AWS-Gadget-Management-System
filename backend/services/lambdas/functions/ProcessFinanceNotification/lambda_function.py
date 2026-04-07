import os
from datetime import datetime, timezone

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeSerializer

from utils import put_item, query_index
from utils.enums import Finance_Notification_Status_Enum, User_Role_Enum
from utils.models import FinanceNotificationRecordModel

from model import FinanceNotificationMessage

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
SENDER_EMAIL_SSM_PATH = os.environ["SENDER_EMAIL_SSM_PATH"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
dynamodb_client = boto3.client("dynamodb")
ses_client = boto3.client("ses")
ssm_client = boto3.client("ssm")
serializer = TypeSerializer()


EMAIL_TEMPLATE = """<html>
<body>
  <h2>Asset Disposal Notification</h2>
  <p>An asset has been disposed and requires financial processing.</p>
  <table>
    <tr><td><strong>Asset ID:</strong></td><td>{asset_id}</td></tr>
    <tr><td><strong>Serial Number:</strong></td><td>{serial_number}</td></tr>
    <tr><td><strong>Purchase Date:</strong></td><td>{purchase_date}</td></tr>
    <tr><td><strong>Original Cost:</strong></td><td>{original_cost}</td></tr>
    <tr><td><strong>Disposal Date:</strong></td><td>{disposal_date}</td></tr>
    <tr><td><strong>Disposal Reason:</strong></td><td>{disposal_reason}</td></tr>
  </table>
  <p><strong>Action Required:</strong> Please perform the following:</p>
  <ul>
    <li>Write-off processing</li>
    <li>Depreciation adjustment</li>
    <li>Asset register updates</li>
  </ul>
</body>
</html>"""


def _get_finance_users():
    """Query all users with finance role using EntityTypeIndex."""
    users = query_index(
        table,
        index_name="EntityTypeIndex",
        key_condition=Key("EntityType").eq("USER"),
        filter_exp=Attr("Role").eq(User_Role_Enum.FINANCE),
    )
    return users


def _get_sender_email():
    """Retrieve sender email address from SSM Parameter Store."""
    response = ssm_client.get_parameter(Name=SENDER_EMAIL_SSM_PATH)
    return response["Parameter"]["Value"]


def _update_disposal_record(asset_id, updates):
    """Find and update the most recent disposal record for the asset."""
    disposal_response = table.query(
        KeyConditionExpression=Key("PK").eq(f"ASSET#{asset_id}")
        & Key("SK").begins_with("DISPOSAL#"),
        ScanIndexForward=False,
        Limit=1,
    )
    disposal_items = disposal_response.get("Items", [])
    if not disposal_items:
        logger.warning("No disposal record found for asset", asset_id=asset_id)
        return

    disposal_sk = disposal_items[0]["SK"]

    update_expr_parts = []
    expr_names = {}
    expr_values = {}
    for key, value in updates.items():
        alias = key.lower()
        update_expr_parts.append(f"#{alias} = :{alias}")
        expr_names[f"#{alias}"] = key
        expr_values[f":{alias}"] = serializer.serialize(value)

    dynamodb_client.update_item(
        TableName=ASSETS_TABLE,
        Key={
            "PK": serializer.serialize(f"ASSET#{asset_id}"),
            "SK": serializer.serialize(disposal_sk),
        },
        UpdateExpression="SET " + ", ".join(update_expr_parts),
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )


def _send_email(sender_email, recipient_email, asset_id, message):
    """Send HTML email via Amazon SES to a finance user."""
    html_body = EMAIL_TEMPLATE.format(
        asset_id=message.asset_id,
        serial_number=message.serial_number or "N/A",
        purchase_date=message.purchase_date or "N/A",
        original_cost=(
            message.original_cost if message.original_cost is not None else "N/A"
        ),
        disposal_date=message.disposal_date,
        disposal_reason=message.disposal_reason,
    )

    ses_client.send_email(
        Source=sender_email,
        Destination={"ToAddresses": [recipient_email]},
        Message={
            "Subject": {"Data": f"Asset Disposal Notification - {asset_id}"},
            "Body": {"Html": {"Data": html_body}},
        },
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    try:
        # Parse SQS message body
        record = event["Records"][0]
        body = json.loads(record["body"])
        message = FinanceNotificationMessage(**body)

        asset_id = message.asset_id
        logger.info("Processing finance notification", asset_id=asset_id)

        # Query finance users
        finance_users = _get_finance_users()

        if not finance_users:
            logger.warning("No finance users found for disposal notification")
            _update_disposal_record(
                asset_id,
                {
                    "FinanceNotificationSent": False,
                    "FinanceNotificationStatus": Finance_Notification_Status_Enum.NO_FINANCE_USERS,
                },
            )
            return {"statusCode": 200, "body": "No finance users found"}

        # Retrieve sender email from SSM Parameter Store
        sender_email = _get_sender_email()

        now = datetime.now(timezone.utc).isoformat()

        # Process each finance user
        for user in finance_users:
            user_id = user["UserID"]
            user_email = user["Email"]

            # Create FinanceNotificationRecord in DynamoDB
            notification_record = FinanceNotificationRecordModel(
                PK=f"ASSET#{asset_id}",
                SK=f"FINANCE_NOTIFICATION#{now}#{user_id}",
                RecipientUserID=user_id,
                NotifiedAt=now,
                AssetID=asset_id,
                SerialNumber=message.serial_number,
                PurchaseDate=message.purchase_date,
                OriginalCost=message.original_cost,
                DisposalDate=message.disposal_date,
                DisposalReason=message.disposal_reason,
            )
            put_item(table, notification_record.model_dump())

            # Send email via SES
            try:
                _send_email(sender_email, user_email, asset_id, message)
                logger.info(
                    "Finance notification email sent",
                    asset_id=asset_id,
                    recipient=user_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to send email to finance user",
                    asset_id=asset_id,
                    recipient=user_id,
                    error=str(e),
                )

        # Update Disposal_Record with completion status
        _update_disposal_record(
            asset_id,
            {
                "FinanceNotifiedAt": now,
                "FinanceNotificationSent": True,
                "FinanceNotificationStatus": Finance_Notification_Status_Enum.COMPLETED,
            },
        )

        logger.info(
            "Finance notifications processed",
            asset_id=asset_id,
            notified_count=len(finance_users),
        )
        return {"statusCode": 200, "body": "Finance notifications processed"}

    except Exception as e:
        logger.exception("Failed to process finance notification")
        raise
