"""Handover feature stack — Lambda functions for asset assignment & handover."""

from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_docker_lambda_function,
    create_lambda_function,
)
from helpers.naming import get_ssm_parameter_path


class HandoverStack(Stack):
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
        ses_sender_email = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "notifications", "sender-email"
            ),
        )

        # 1. AssignAsset (Docker — WeasyPrint needs system-level deps)
        assign_asset_fn = create_docker_lambda_function(
            ctx,
            purpose="assign-asset",
            directory="AssignAsset",
            construct_prefix="AssignAsset",
            dockerfile_dir="services/lambdas/docker/pdf",
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
                    ["s3:GetObject", "s3:PutObject"],
                    [ctx.bucket_objects_arn],
                ),
                PolicyConfig(
                    ["ses:SendEmail"],
                    ["*"],
                ),
            ],
            timeout_seconds=60,
        )
        assign_asset_fn.add_environment("SES_SENDER_EMAIL", ses_sender_email)

        # 2. GetHandoverForm
        create_lambda_function(
            ctx,
            purpose="get-handover-form",
            directory="GetHandoverForm",
            construct_prefix="GetHandoverForm",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 3. GetSignedHandoverForm
        create_lambda_function(
            ctx,
            purpose="get-signed-handover-form",
            directory="GetSignedHandoverForm",
            construct_prefix="GetSignedHandoverForm",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 4. GenerateSignatureUploadUrl
        create_lambda_function(
            ctx,
            purpose="generate-signature-upload-url",
            directory="GenerateSignatureUploadUrl",
            construct_prefix="GenerateSignatureUploadUrl",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:PutObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 5. AcceptHandover (Docker — WeasyPrint needs system-level deps)
        create_docker_lambda_function(
            ctx,
            purpose="accept-handover",
            directory="AcceptHandover",
            construct_prefix="AcceptHandover",
            dockerfile_dir="services/lambdas/docker/pdf",
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
                    ["s3:GetObject", "s3:PutObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
            timeout_seconds=60,
        )

        # 6. CancelAssignment
        create_lambda_function(
            ctx,
            purpose="cancel-assignment",
            directory="CancelAssignment",
            construct_prefix="CancelAssignment",
            policies=[
                PolicyConfig(
                    [
                        "dynamodb:GetItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:TransactWriteItems",
                    ],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 7. ListEmployeeSignatures
        create_lambda_function(
            ctx,
            purpose="list-employee-signatures",
            directory="ListEmployeeSignatures",
            construct_prefix="ListEmployeeSignatures",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_objects_arn],
                ),
            ],
        )

        # 8. ListPendingSignatures (employee — pending handovers + returns to sign)
        create_lambda_function(
            ctx,
            purpose="list-pending-signatures",
            directory="ListPendingSignatures",
            construct_prefix="ListPendingSignatures",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
