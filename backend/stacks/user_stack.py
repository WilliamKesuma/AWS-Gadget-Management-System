"""User management stack — CreateUser, DeactivateUser, ListUsers Lambdas."""

from aws_cdk import Stack, aws_ssm as ssm
from constructs import Construct

from helpers.naming import get_ssm_parameter_path
from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)


class UserStack(Stack):
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

        # Look up Cognito User Pool ID from SSM
        user_pool_id = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "auth", "user-pool-id"),
        )

        # Construct Cognito User Pool ARN for IAM policies
        user_pool_arn = (
            f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{user_pool_id}"
        )

        # CreateUser Lambda
        create_user_fn = create_lambda_function(
            ctx,
            purpose="create-user",
            directory="CreateUser",
            construct_prefix="CreateUser",
            policies=[
                PolicyConfig(
                    ["cognito-idp:AdminCreateUser", "cognito-idp:AdminAddUserToGroup"],
                    [user_pool_arn],
                ),
                PolicyConfig(
                    ["dynamodb:Query", "dynamodb:PutItem"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
        create_user_fn.add_environment("USER_POOL_ID", user_pool_id)

        # DeactivateUser Lambda
        deactivate_user_fn = create_lambda_function(
            ctx,
            purpose="deactivate-user",
            directory="DeactivateUser",
            construct_prefix="DeactivateUser",
            policies=[
                PolicyConfig(
                    ["cognito-idp:AdminDisableUser", "cognito-idp:AdminGetUser"],
                    [user_pool_arn],
                ),
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:UpdateItem"],
                    [ctx.table_arn],
                ),
            ],
        )
        deactivate_user_fn.add_environment("USER_POOL_ID", user_pool_id)

        # ReactivateUser Lambda
        reactivate_user_fn = create_lambda_function(
            ctx,
            purpose="reactivate-user",
            directory="ReactivateUser",
            construct_prefix="ReactivateUser",
            policies=[
                PolicyConfig(
                    ["cognito-idp:AdminEnableUser", "cognito-idp:AdminGetUser"],
                    [user_pool_arn],
                ),
                PolicyConfig(
                    ["dynamodb:GetItem", "dynamodb:UpdateItem"],
                    [ctx.table_arn],
                ),
            ],
        )
        reactivate_user_fn.add_environment("USER_POOL_ID", user_pool_id)

        # ListUsers Lambda
        create_lambda_function(
            ctx,
            purpose="list-users",
            directory="ListUsers",
            construct_prefix="ListUsers",
            policies=[
                PolicyConfig(
                    ["dynamodb:Query"],
                    [ctx.table_arn, ctx.table_gsi_arn],
                ),
            ],
        )
