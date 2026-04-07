"""Asset Category Management stack — create, delete, and list asset categories."""

from aws_cdk import Stack
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)


class CategoryStack(Stack):
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

        # 1. CreateAssetCategory
        create_lambda_function(
            ctx,
            purpose="create-asset-category",
            directory="CreateAssetCategory",
            construct_prefix="CreateAssetCategory",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )

        # 2. DeleteAssetCategory
        create_lambda_function(
            ctx,
            purpose="delete-asset-category",
            directory="DeleteAssetCategory",
            construct_prefix="DeleteAssetCategory",
            policies=[
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:DeleteItem"],
                    [ctx.table_arn],
                ),
            ],
        )

        # 3. ListAssetCategories
        create_lambda_function(
            ctx,
            purpose="list-asset-categories",
            directory="ListAssetCategories",
            construct_prefix="ListAssetCategories",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
