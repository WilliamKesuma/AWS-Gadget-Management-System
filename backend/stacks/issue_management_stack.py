"""Issue Management stack — 14 Lambda functions for issue lifecycle."""

from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_resource_name, get_ssm_parameter_path


class IssueManagementStack(Stack):
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

        # SSM lookup for SES sender email
        sender_email_ssm_path = get_ssm_parameter_path(
            project_name, env_name, "notifications", "sender-email"
        )

        # SSM lookup for unified email notification queue
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

        # EventBridge bus name
        event_bus_name = get_resource_name(project_name, env_name, "issue-events")

        # 1. SubmitIssue (+ email notification via unified SQS queue)
        submit_fn = create_lambda_function(
            ctx,
            purpose="submit-issue",
            directory="SubmitIssue",
            construct_prefix="SubmitIssue",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [email_queue_arn],
                ),
            ],
        )
        submit_fn.add_environment("EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url)

        # 2. ResolveRepair
        create_lambda_function(
            ctx,
            purpose="resolve-repair",
            directory="ResolveRepair",
            construct_prefix="ResolveRepair",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 3. SendWarranty
        create_lambda_function(
            ctx,
            purpose="send-warranty",
            directory="SendWarranty",
            construct_prefix="SendWarranty",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 4. CompleteRepair
        create_lambda_function(
            ctx,
            purpose="complete-repair",
            directory="CompleteRepair",
            construct_prefix="CompleteRepair",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 5. RequestReplacement (+ email notification via unified SQS queue)
        request_replacement_fn = create_lambda_function(
            ctx,
            purpose="request-replacement",
            directory="RequestReplacement",
            construct_prefix="RequestReplacement",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [email_queue_arn],
                ),
            ],
        )
        request_replacement_fn.add_environment(
            "EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url
        )

        # 6. ManagementReviewIssue (+ EventBridge event on approval)
        mgmt_review_fn = create_lambda_function(
            ctx,
            purpose="management-review-issue",
            directory="ManagementReviewIssue",
            construct_prefix="ManagementReviewIssue",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["events:PutEvents"],
                    [
                        f"arn:aws:events:{self.region}:{self.account}:event-bus/{event_bus_name}"
                    ],
                ),
            ],
        )
        mgmt_review_fn.add_environment("EVENT_BUS_NAME", event_bus_name)

        # 7. ListIssues
        create_lambda_function(
            ctx,
            purpose="list-issues",
            directory="ListIssues",
            construct_prefix="ListIssues",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 8. GetIssue (+ S3 presigned URLs for issue photos)
        create_lambda_function(
            ctx,
            purpose="get-issue",
            directory="GetIssue",
            construct_prefix="GetIssue",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:BatchGetItem",
                        "dynamodb:Query",
                        "dynamodb:UpdateItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
                PolicyConfig(
                    ["s3:ListBucket"],
                    [ctx.bucket_arn],
                ),
            ],
        )

        # 9. ListPendingReplacements
        create_lambda_function(
            ctx,
            purpose="list-pending-replacements",
            directory="ListPendingReplacements",
            construct_prefix="ListPendingReplacements",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 10. GenerateIssueUploadUrls (S3 presigned URLs for issue photos)
        create_lambda_function(
            ctx,
            purpose="generate-issue-upload-urls",
            directory="GenerateIssueUploadUrls",
            construct_prefix="GenerateIssueUploadUrls",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:UpdateItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:PutObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 12. ListAllIssues (IT admin — all issues across all assets)
        create_lambda_function(
            ctx,
            purpose="list-all-issues",
            directory="ListAllIssues",
            construct_prefix="ListAllIssues",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
