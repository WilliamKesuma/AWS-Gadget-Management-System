"""Asset feature stack — CreateAsset + ApproveAsset Lambdas."""

from aws_cdk import Stack
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)


class AssetStack(Stack):
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

        create_lambda_function(
            ctx,
            purpose="create-asset",
            directory="CreateAsset",
            construct_prefix="CreateAsset",
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
                    ["s3:GetObject"],
                    [ctx.bucket_arn, ctx.bucket_objects_arn],
                ),
                PolicyConfig(
                    ["s3:ListBucket"],
                    [ctx.bucket_arn],
                ),
            ],
        )

        create_lambda_function(
            ctx,
            purpose="approve-asset",
            directory="ApproveAsset",
            construct_prefix="ApproveAsset",
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

        create_lambda_function(
            ctx,
            purpose="list-assets",
            directory="ListAssets",
            construct_prefix="ListAssets",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        create_lambda_function(
            ctx,
            purpose="get-asset",
            directory="GetAsset",
            construct_prefix="GetAsset",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem"],
                    [ctx.table_arn],
                ),
                PolicyConfig(
                    ["s3:GetObject"],
                    [ctx.bucket_arn, ctx.bucket_objects_arn],
                ),
            ],
        )

        create_lambda_function(
            ctx,
            purpose="get-asset-logs",
            directory="GetAssetLogs",
            construct_prefix="GetAssetLogs",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
