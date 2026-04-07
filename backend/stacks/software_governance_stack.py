"""Software Installation Governance stack — 6 Lambda functions for software request lifecycle."""

from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_ssm_parameter_path


class SoftwareGovernanceStack(Stack):
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

        # 1. SubmitSoftwareRequest
        submit_fn = create_lambda_function(
            ctx,
            purpose="submit-software-request",
            directory="SubmitSoftwareRequest",
            construct_prefix="SubmitSoftwareRequest",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
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

        submit_fn.add_environment("EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url)

        # 2. ListSoftwareRequests
        create_lambda_function(
            ctx,
            purpose="list-software-requests",
            directory="ListSoftwareRequests",
            construct_prefix="ListSoftwareRequests",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 3. GetSoftwareRequest
        create_lambda_function(
            ctx,
            purpose="get-software-request",
            directory="GetSoftwareRequest",
            construct_prefix="GetSoftwareRequest",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 4. ReviewSoftwareRequest
        create_lambda_function(
            ctx,
            purpose="review-software-request",
            directory="ReviewSoftwareRequest",
            construct_prefix="ReviewSoftwareRequest",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 5. ManagementReviewSoftwareRequest
        create_lambda_function(
            ctx,
            purpose="management-review-software-request",
            directory="ManagementReviewSoftwareRequest",
            construct_prefix="ManagementReviewSoftwareRequest",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 6. ListAllSoftwareRequests
        create_lambda_function(
            ctx,
            purpose="list-all-software-requests",
            directory="ListAllSoftwareRequests",
            construct_prefix="ListAllSoftwareRequests",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
