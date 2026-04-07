"""
ProcessEmailNotification — unified SQS consumer for all email notifications.

Replaces:
- Inline SES calls in SubmitIssue, SubmitSoftwareRequest, RequestReplacement, SubmitAdminReturnEvidence
- ProcessDisposalEmailNotification Lambda

All business Lambdas now send a message to a single SQS queue. This Lambda
consumes the queue, resolves recipients by role, and sends SES emails.
"""

import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger, Tracer
from boto3.dynamodb.conditions import Attr, Key

from utils import query_index
from utils.enums import Email_Event_Type_Enum, User_Role_Enum, User_Status_Enum

from model import EmailNotificationMessage

logger = Logger()
tracer = Tracer()

ASSETS_TABLE = os.environ["ASSETS_TABLE"]
SENDER_EMAIL_SSM_PATH = os.environ["SENDER_EMAIL_SSM_PATH"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(ASSETS_TABLE)
ses_client = boto3.client("ses")
ssm_client = boto3.client("ssm")

_sender_email_cache: str | None = None


def _get_sender_email() -> str:
    global _sender_email_cache
    if _sender_email_cache is None:
        response = ssm_client.get_parameter(Name=SENDER_EMAIL_SSM_PATH)
        _sender_email_cache = response["Parameter"]["Value"]
    return _sender_email_cache


def _get_users_by_role(role: str) -> list[dict]:
    return query_index(
        table,
        index_name="EntityTypeIndex",
        key_condition=Key("EntityType").eq("USER"),
        filter_exp=Attr("Role").eq(role) & Attr("Status").eq(User_Status_Enum.ACTIVE),
    )


def _send_email(sender: str, recipient: str, subject: str, body_html: str) -> None:
    ses_client.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": body_html}},
        },
    )


def _send_to_role(sender: str, role: str, subject: str, body_html: str) -> int:
    """Send email to all active users of a given role. Returns count sent."""
    users = _get_users_by_role(role)
    if not users:
        logger.warning("No active users found for role", role=role)
        return 0
    for user in users:
        try:
            _send_email(sender, user["Email"], subject, body_html)
        except Exception:
            logger.exception("Failed to send email", recipient=user.get("UserID"))
    return len(users)


def _send_to_address(
    sender: str, recipient_email: str, subject: str, body_html: str
) -> None:
    """Send email to a specific address."""
    try:
        _send_email(sender, recipient_email, subject, body_html)
    except Exception:
        logger.exception("Failed to send email", recipient=recipient_email)


# ── Email builders per event type ─────────────────────────────────────────


def _handle_issue_submitted(msg: EmailNotificationMessage, sender: str) -> None:
    subject = f"New Issue Report — Asset {msg.asset_id}"
    body = f"""<html><body>
    <h2>New Issue Report</h2>
    <p>A new issue has been reported for an IT asset.</p>
    <table>
      <tr><td><strong>Employee:</strong></td><td>{msg.actor_name or msg.actor_id} ({msg.actor_id})</td></tr>
      <tr><td><strong>Asset ID:</strong></td><td>{msg.asset_id}</td></tr>
      <tr><td><strong>Issue:</strong></td><td>{(msg.issue_description or '')[:200]}</td></tr>
    </table>
    <p>Please log in to the GMS portal to triage this issue.</p>
    </body></html>"""
    _send_to_role(sender, User_Role_Enum.IT_ADMIN, subject, body)


def _handle_replacement_requested(msg: EmailNotificationMessage, sender: str) -> None:
    subject = f"Replacement Approval Required — Asset {msg.asset_id}"
    body = f"""<html><body>
    <h2>Replacement Approval Required</h2>
    <p>A replacement request requires your approval.</p>
    <table>
      <tr><td><strong>Asset ID:</strong></td><td>{msg.asset_id}</td></tr>
      <tr><td><strong>Issue:</strong></td><td>{(msg.issue_description or '')[:200]}</td></tr>
      <tr><td><strong>Justification:</strong></td><td>{(msg.replacement_justification or '')[:200]}</td></tr>
    </table>
    <p>Please log in to the GMS portal to review and approve or reject this request.</p>
    </body></html>"""
    _send_to_role(sender, User_Role_Enum.MANAGEMENT, subject, body)


def _handle_software_request_submitted(
    msg: EmailNotificationMessage, sender: str
) -> None:
    subject = f"New Software Installation Request — {msg.software_name}"
    body = f"""<html><body>
    <h2>New Software Installation Request</h2>
    <p>A new software installation request has been submitted.</p>
    <table>
      <tr><td><strong>Employee:</strong></td><td>{msg.actor_name or msg.actor_id} ({msg.actor_id})</td></tr>
      <tr><td><strong>Software:</strong></td><td>{msg.software_name}</td></tr>
      <tr><td><strong>Asset ID:</strong></td><td>{msg.asset_id}</td></tr>
    </table>
    <p>Please log in to the GMS portal to review the request.</p>
    </body></html>"""
    _send_to_role(sender, User_Role_Enum.IT_ADMIN, subject, body)


def _handle_return_evidence_submitted(
    msg: EmailNotificationMessage, sender: str
) -> None:
    if not msg.employee_email:
        logger.warning(
            "No employee email for return notification", asset_id=msg.asset_id
        )
        return
    device_label = f"{msg.asset_model or 'Unknown'} (S/N: {msg.asset_serial or 'N/A'})"
    subject = "Action Required: Asset Return Confirmation"
    body = f"""<html><body>
    <h2>Asset Return Confirmation Required</h2>
    <p>Dear {msg.employee_name or 'Employee'},</p>
    <p>IT Admin has initiated a return for your device: <strong>{device_label}</strong>.</p>
    <p>Please log in to the system to review the return details and provide your digital signature
    to complete the return process.</p>
    <p>This action is required to finalise the asset return.</p>
    </body></html>"""
    _send_to_address(sender, msg.employee_email, subject, body)


def _handle_disposal_pending(msg: EmailNotificationMessage, sender: str) -> None:
    brand = msg.brand or "N/A"
    model = msg.model or "N/A"
    serial_number = msg.serial_number or "N/A"
    subject = f"Disposal Approval Required — Asset {msg.asset_id}"
    body = f"""<html><body>
    <h2>Disposal Approval Required</h2>
    <p>An IT asset has been submitted for disposal and requires your approval.</p>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><td><strong>Asset ID:</strong></td><td>{msg.asset_id}</td></tr>
      <tr><td><strong>Brand / Model:</strong></td><td>{brand} {model}</td></tr>
      <tr><td><strong>Serial Number:</strong></td><td>{serial_number}</td></tr>
      <tr><td><strong>Disposal Reason:</strong></td><td>{msg.disposal_reason}</td></tr>
      <tr><td><strong>Justification:</strong></td><td>{msg.justification}</td></tr>
    </table>
    <p>Please log in to the system to approve or reject this disposal request.</p>
    </body></html>"""
    _send_to_role(sender, User_Role_Enum.MANAGEMENT, subject, body)


def _handle_disposal_management_approved(
    msg: EmailNotificationMessage, sender: str
) -> None:
    brand = msg.brand or "N/A"
    model = msg.model or "N/A"
    serial_number = msg.serial_number or "N/A"
    subject = f"Disposal Approved — Asset {msg.asset_id}"
    body = f"""<html><body>
    <h2>Disposal Request Approved</h2>
    <p>Management has approved the disposal request for the following asset.</p>
    <table border="1" cellpadding="6" cellspacing="0">
      <tr><td><strong>Asset ID:</strong></td><td>{msg.asset_id}</td></tr>
      <tr><td><strong>Brand / Model:</strong></td><td>{brand} {model}</td></tr>
      <tr><td><strong>Serial Number:</strong></td><td>{serial_number}</td></tr>
      <tr><td><strong>Disposal Reason:</strong></td><td>{msg.disposal_reason}</td></tr>
    </table>
    <p>You may now proceed to complete the disposal by entering the disposal date and confirming data wipe.</p>
    </body></html>"""
    _send_to_role(sender, User_Role_Enum.IT_ADMIN, subject, body)


# ── Event type → handler dispatch ─────────────────────────────────────────

EVENT_HANDLERS = {
    Email_Event_Type_Enum.ISSUE_SUBMITTED: _handle_issue_submitted,
    Email_Event_Type_Enum.REPLACEMENT_REQUESTED: _handle_replacement_requested,
    Email_Event_Type_Enum.SOFTWARE_REQUEST_SUBMITTED: _handle_software_request_submitted,
    Email_Event_Type_Enum.RETURN_EVIDENCE_SUBMITTED: _handle_return_evidence_submitted,
    Email_Event_Type_Enum.DISPOSAL_PENDING: _handle_disposal_pending,
    Email_Event_Type_Enum.DISPOSAL_MANAGEMENT_APPROVED: _handle_disposal_management_approved,
}


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    record = event["Records"][0]
    body = json.loads(record["body"])
    message = EmailNotificationMessage(**body)

    logger.info(
        "Processing email notification",
        event_type=message.event_type,
        asset_id=message.asset_id,
    )

    sender_email = _get_sender_email()

    handler = EVENT_HANDLERS.get(message.event_type)
    if not handler:
        logger.error("Unknown email event type", event_type=message.event_type)
        return {"statusCode": 400, "body": f"Unknown event type: {message.event_type}"}

    handler(message, sender_email)

    return {"statusCode": 200, "body": "Processed"}
