"""Return feature stack — 8 Lambda functions for asset return processing."""

from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_ssm_parameter_path


class ReturnStack(Stack):
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

        # 1. InitiateReturn
        create_lambda_function(
            ctx,
            purpose="initiate-return",
            directory="InitiateReturn",
            construct_prefix="InitiateReturn",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 2. GenerateReturnUploadUrls
        create_lambda_function(
            ctx,
            purpose="generate-return-upload-urls",
            directory="GenerateReturnUploadUrls",
            construct_prefix="GenerateReturnUploadUrls",
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

        # 3. CompleteReturn
        create_lambda_function(
            ctx,
            purpose="complete-return",
            directory="CompleteReturn",
            construct_prefix="CompleteReturn",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:TransactWriteItems",
                        "dynamodb:UpdateItem",
                        "dynamodb:PutItem",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 4. ListReturns
        create_lambda_function(
            ctx,
            purpose="list-returns",
            directory="ListReturns",
            construct_prefix="ListReturns",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 5. GetReturn
        create_lambda_function(
            ctx,
            purpose="get-return",
            directory="GetReturn",
            construct_prefix="GetReturn",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 6. SubmitAdminReturnEvidence (+ email notification via unified SQS queue)
        submit_evidence_fn = create_lambda_function(
            ctx,
            purpose="submit-admin-return-evidence",
            directory="SubmitAdminReturnEvidence",
            construct_prefix="SubmitAdminReturnEvidence",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:UpdateItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
                PolicyConfig(
                    ["sqs:SendMessage"],
                    [email_queue_arn],
                ),
            ],
        )
        submit_evidence_fn.add_environment(
            "EMAIL_NOTIFICATION_QUEUE_URL", email_queue_url
        )

        # 7. GenerateReturnSignatureUploadUrl
        create_lambda_function(
            ctx,
            purpose="generate-return-signature-upload-url",
            directory="GenerateReturnSignatureUploadUrl",
            construct_prefix="GenerateReturnSignatureUploadUrl",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:PutObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 8. ListAllReturns
        create_lambda_function(
            ctx,
            purpose="list-all-returns",
            directory="ListAllReturns",
            construct_prefix="ListAllReturns",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
