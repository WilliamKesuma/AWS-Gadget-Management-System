"""Disposal feature stack — API Lambdas, finance notification queue + consumer."""

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


class DisposalStack(Stack):
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

        # ── Finance Notification SQS Queue ────────────────────────
        finance_dlq = sqs.Queue(
            self,
            "FinanceNotificationDLQ",
            queue_name=get_resource_name(
                project_name, env_name, "disposal-finance-notification-dlq"
            ),
            retention_period=Duration.days(14),
        )

        finance_queue = sqs.Queue(
            self,
            "FinanceNotificationQueue",
            queue_name=get_resource_name(
                project_name, env_name, "disposal-finance-notification-queue"
            ),
            visibility_timeout=Duration.seconds(60),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=finance_dlq,
            ),
        )

        # ── Unified email notification queue (SSM lookup) ─────────
        email_queue_url = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "queues", "email-notification-queue-url"
            ),
        )
        email_queue_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "queues", "email-notification-queue-arn"
            ),
        )

        # ── SSM lookup: Sender Email ──────────────────────────────
        sender_email_ssm_path = get_ssm_parameter_path(
            project_name, env_name, "notifications", "sender-email"
        )

        # ── 1. InitiateDisposal ───────────────────────────────────
        initiate_disposal_fn = create_lambda_function(
            ctx,
            purpose="initiate-disposal",
            directory="InitiateDisposal",
            construct_prefix="InitiateDisposal",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [email_queue_arn],
                ),
            ],
        )
        initiate_disposal_fn.add_environment(
            "EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url
        )

        # ── 2. ManagementReviewDisposal ───────────────────────────
        mgmt_review_fn = create_lambda_function(
            ctx,
            purpose="management-review-disposal",
            directory="ManagementReviewDisposal",
            construct_prefix="ManagementReviewDisposal",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                        "dynamodb:UpdateItem",
                        "dynamodb:PutItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [email_queue_arn],
                ),
            ],
        )
        mgmt_review_fn.add_environment("EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url)

        # ── 3. CompleteDisposal ───────────────────────────────────
        complete_disposal_fn = create_lambda_function(
            ctx,
            purpose="complete-disposal",
            directory="CompleteDisposal",
            construct_prefix="CompleteDisposal",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                        "dynamodb:UpdateItem",
                        "dynamodb:PutItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [finance_queue.queue_arn],
                ),
            ],
        )
        complete_disposal_fn.add_environment(
            "FINANCE_NOTIFICATION_QUEUE_URL", finance_queue.queue_url
        )

        # ── 4. ProcessFinanceNotification (SQS consumer) ──────────
        process_finance_fn = create_lambda_function(
            ctx,
            purpose="process-finance-notification",
            directory="ProcessFinanceNotification",
            construct_prefix="ProcessFinanceNotification",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    [
                        "sqs:ReceiveMessage",
                        "sqs:DeleteMessage",
                        "sqs:GetQueueAttributes",
                    ],
                    [finance_queue.queue_arn],
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
        process_finance_fn.add_event_source(
            lambda_event_sources.SqsEventSource(finance_queue, batch_size=1)
        )
        process_finance_fn.add_environment(
            "FINANCE_NOTIFICATION_QUEUE_URL", finance_queue.queue_url
        )
        process_finance_fn.add_environment(
            "SENDER_EMAIL_SSM_PATH", sender_email_ssm_path
        )

        # ── 5. ListDisposals ──────────────────────────────────────
        create_lambda_function(
            ctx,
            purpose="list-disposals",
            directory="ListDisposals",
            construct_prefix="ListDisposals",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:Scan", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # ── 6. ListPendingDisposals ───────────────────────────────
        create_lambda_function(
            ctx,
            purpose="list-pending-disposals",
            directory="ListPendingDisposals",
            construct_prefix="ListPendingDisposals",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # ── 7. GetDisposalDetails ─────────────────────────────────
        create_lambda_function(
            ctx,
            purpose="get-disposal-details",
            directory="GetDisposalDetails",
            construct_prefix="GetDisposalDetails",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # ── 8. ListAssetDisposals ─────────────────────────────────
        create_lambda_function(
            ctx,
            purpose="list-asset-disposals",
            directory="ListAssetDisposals",
            construct_prefix="ListAssetDisposals",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
