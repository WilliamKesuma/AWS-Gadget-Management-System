import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key

from utils import query_index
from utils.enums import Disposal_Email_Event_Type_Enum, User_Role_Enum, User_Status_Enum
from model import DisposalEmailNotificationMessage

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
SENDER_EMAIL_SSM_PATH = os.environ["SENDER_EMAIL_SSM_PATH"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
ses_client = boto3.client("ses")
ssm_client = boto3.client("ssm")


MANAGEMENT_PENDING_TEMPLATE = """<html>
<body>
  <h2>Disposal Approval Required</h2>
  <p>An IT asset has been submitted for disposal and requires your approval.</p>
  <table border="1" cellpadding="6" cellspacing="0">
    <tr><td><strong>Asset ID:</strong></td><td>{asset_id}</td></tr>
    <tr><td><strong>Brand / Model:</strong></td><td>{brand} {model}</td></tr>
    <tr><td><strong>Serial Number:</strong></td><td>{serial_number}</td></tr>
    <tr><td><strong>Disposal Reason:</strong></td><td>{disposal_reason}</td></tr>
    <tr><td><strong>Justification:</strong></td><td>{justification}</td></tr>
  </table>
  <p>Please log in to the system to approve or reject this disposal request.</p>
</body>
</html>"""

IT_ADMIN_APPROVED_TEMPLATE = """<html>
<body>
  <h2>Disposal Request Approved</h2>
  <p>Management has approved the disposal request for the following asset.</p>
  <table border="1" cellpadding="6" cellspacing="0">
    <tr><td><strong>Asset ID:</strong></td><td>{asset_id}</td></tr>
    <tr><td><strong>Brand / Model:</strong></td><td>{brand} {model}</td></tr>
    <tr><td><strong>Serial Number:</strong></td><td>{serial_number}</td></tr>
    <tr><td><strong>Disposal Reason:</strong></td><td>{disposal_reason}</td></tr>
  </table>
  <p>You may now proceed to complete the disposal by entering the disposal date and confirming data wipe.</p>
</body>
</html>"""


def _get_sender_email() -> str:
    response = ssm_client.get_parameter(Name=SENDER_EMAIL_SSM_PATH)
    return response["Parameter"]["Value"]


def _get_users_by_role(role: str) -> list[dict]:
    return query_index(
        table,
        index_name="EntityTypeIndex",
        key_condition=Key("EntityType").eq("USER"),
        filter_exp=Attr("Role").eq(role) & Attr("Status").eq(User_Status_Enum.ACTIVE),
    )


def _send_email(sender: str, recipient: str, subject: str, html_body: str) -> None:
    ses_client.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": html_body}},
        },
    )


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    record = event["Records"][0]
    body = json.loads(record["body"])
    message = DisposalEmailNotificationMessage(**body)

    sender_email = _get_sender_email()
    brand = message.brand or "N/A"
    model = message.model or "N/A"
    serial_number = message.serial_number or "N/A"

    if message.event_type == Disposal_Email_Event_Type_Enum.DISPOSAL_PENDING:
        # Notify all active management users
        recipients = _get_users_by_role(User_Role_Enum.MANAGEMENT)
        if not recipients:
            logger.warning(
                "No active management users found for disposal notification",
                asset_id=message.asset_id,
            )
            return {"statusCode": 200, "body": "No management users found"}

        subject = f"Disposal Approval Required — Asset {message.asset_id}"
        html_body = MANAGEMENT_PENDING_TEMPLATE.format(
            asset_id=message.asset_id,
            brand=brand,
            model=model,
            serial_number=serial_number,
            disposal_reason=message.disposal_reason,
            justification=message.justification,
        )
        for user in recipients:
            try:
                _send_email(sender_email, user["Email"], subject, html_body)
                logger.info(
                    "Disposal pending email sent to management",
                    asset_id=message.asset_id,
                    recipient=user.get("UserID"),
                )
            except Exception:
                logger.exception(
                    "Failed to send disposal pending email",
                    asset_id=message.asset_id,
                    recipient=user.get("UserID"),
                )

    elif (
        message.event_type
        == Disposal_Email_Event_Type_Enum.DISPOSAL_MANAGEMENT_APPROVED
    ):
        # Notify all active IT admin users
        recipients = _get_users_by_role(User_Role_Enum.IT_ADMIN)
        if not recipients:
            logger.warning(
                "No active IT admin users found for disposal approval notification",
                asset_id=message.asset_id,
            )
            return {"statusCode": 200, "body": "No IT admin users found"}

        subject = f"Disposal Approved — Asset {message.asset_id}"
        html_body = IT_ADMIN_APPROVED_TEMPLATE.format(
            asset_id=message.asset_id,
            brand=brand,
            model=model,
            serial_number=serial_number,
            disposal_reason=message.disposal_reason,
        )
        for user in recipients:
            try:
                _send_email(sender_email, user["Email"], subject, html_body)
                logger.info(
                    "Disposal approved email sent to IT admin",
                    asset_id=message.asset_id,
                    recipient=user.get("UserID"),
                )
            except Exception:
                logger.exception(
                    "Failed to send disposal approved email",
                    asset_id=message.asset_id,
                    recipient=user.get("UserID"),
                )

    return {"statusCode": 200, "body": "Processed"}
