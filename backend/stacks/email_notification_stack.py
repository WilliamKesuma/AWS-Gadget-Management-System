"""Unified Email Notification stack — single SQS queue + ProcessEmailNotification Lambda.

Replaces:
- Inline SES calls in SubmitIssue, SubmitSoftwareRequest, RequestReplacement, SubmitAdminReturnEvidence
- ProcessDisposalEmailNotification Lambda (disposal email queue)

All business Lambdas send a message to the unified email queue. The
ProcessEmailNotification Lambda consumes the queue, resolves recipients
by role, and sends SES emails.

The disposal-specific finance notification queue (ProcessFinanceNotification)
is NOT affected — it remains in DisposalStack because it writes
DynamoDB records alongside sending emails.
"""

from aws_cdk import (
    Duration,
    Stack,
    aws_lambda_event_sources as lambda_event_sources,
    aws_sqs as sqs,
    aws_ssm as ssm,
)
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class EmailNotificationStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        project_name: str,
        env_name: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ctx = LambdaStackContext(self, project_name, env_name)

        # ── SQS Dead Letter Queue ─────────────────────────────────
        dlq = sqs.Queue(
            self,
            "EmailNotificationDLQ",
            queue_name=get_resource_name(
                project_name, env_name, "email-notification-dlq"
            ),
            retention_period=Duration.days(14),
        )

        # ── SQS Main Queue ────────────────────────────────────────
        queue = sqs.Queue(
            self,
            "EmailNotificationQueue",
            queue_name=get_resource_name(
                project_name, env_name, "email-notification-queue"
            ),
            visibility_timeout=Duration.seconds(90),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq,
            ),
        )

        # ── SSM exports (cross-stack reference) ───────────────────
        ssm.StringParameter(
            self,
            "EmailNotificationQueueUrl",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "queues", "email-notification-queue-url"
            ),
            string_value=queue.queue_url,
        )

        ssm.StringParameter(
            self,
            "EmailNotificationQueueArn",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "queues", "email-notification-queue-arn"
            ),
            string_value=queue.queue_arn,
        )

        # ── SSM lookup: Sender Email (pre-seeded externally) ─────
        sender_email_ssm_path = get_ssm_parameter_path(
            project_name, env_name, "notifications", "sender-email"
        )

        # ── ProcessEmailNotification Lambda ───────────────────────
        process_fn = create_lambda_function(
            ctx,
            purpose="process-email-notification",
            directory="ProcessEmailNotification",
            construct_prefix="ProcessEmailNotification",
            timeout_seconds=60,
            policies=[
                PolicyConfig(
                    ["dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    [
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes",
                    ],
                    [queue.queue_arn],
                ),
                PolicyConfig(
                    ["ses:SendEmail", "ses:SendRawEmail"],
                    ["*"],
                ),
                PolicyConfig(
                    ["ssm:GetParameter"],
                    [
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter{sender_email_ssm_path}"
                    ],
                ),
            ],
        )

        process_fn.add_environment("SENDER_EMAIL_SSM_PATH", sender_email_ssm_path)

        process_fn.add_event_source(
            lambda_event_sources.SqsEventSource(queue, batch_size=1)
        )
