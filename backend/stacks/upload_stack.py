"""Upload feature stack — GenerateUploadUrls Lambda."""

from aws_cdk import Stack
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from helpers.lambda_helpers import (
    LambdaStackContext,
    PolicyConfig,
    create_lambda_function,
)
from helpers.naming import get_ssm_parameter_path


class UploadStack(Stack):
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

        scan_worker_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "functions", "scan-worker-arn"
            ),
        )

        fn = create_lambda_function(
            ctx,
            purpose="generate-upload-presigned-urls",
            directory="GenerateUploadUrls",
            construct_prefix="GenerateUploadUrls",
            policies=[
                PolicyConfig(["dynamodb:PutItem"], [ctx.table_arn]),
                PolicyConfig(
                    ["s3:PutObject"], [ctx.bucket_arn, ctx.bucket_objects_arn]
                ),
                PolicyConfig(
                    ["lambda:InvokeFunction"],
                    ["*"],
                ),
            ],
        )
        fn.add_environment("SCAN_WORKER_ARN", scan_worker_arn)
