"""Shared helper for sending email notification messages to the unified SQS queue.

Usage in any Lambda handler:

    from utils.email_queue import send_email_event
    from utils.enums import Email_Event_Type_Enum

    send_email_event(
        Email_Event_Type_Enum.ISSUE_SUBMITTED,
        asset_id=asset_id,
        actor_name=employee_name,
        actor_id=actor_id,
        issue_description=request.issue_description,
    )
"""

import os

import boto3
import simplejson as json
from aws_lambda_powertools import Logger

from utils.enums import Email_Event_Type_Enum

logger = Logger(child=True)

_sqs_client = None


def _get_sqs_client():
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")
    return _sqs_client


def send_email_event(event_type: Email_Event_Type_Enum, **kwargs) -> None:
    """Send an email notification message to the unified SQS queue.

    The queue URL is read from the EMAIL_NOTIFICATION_QUEUE_URL environment
    variable, which is set by the CDK stack for every Lambda that needs it.

    Args:
        event_type: The email event type enum value.
        **kwargs: Additional fields matching EmailNotificationMessage schema.
    """
    queue_url = os.environ.get("EMAIL_NOTIFICATION_QUEUE_URL")
    if not queue_url:
        logger.warning(
            "EMAIL_NOTIFICATION_QUEUE_URL not set — skipping email notification",
            event_type=event_type,
        )
        return

    message = {"event_type": event_type.value, **kwargs}

    try:
        _get_sqs_client().send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message),
        )
        logger.info("Email notification queued", event_type=event_type)
    except Exception:
        logger.exception("Failed to queue email notification", event_type=event_type)
