from aws_cdk import (
    BundlingOptions,
    RemovalPolicy,
    Stack,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class LayersStack(Stack):
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

        dependencies_layer_name = get_resource_name(
            project_name, env_name, "dependencies", "layer"
        )
        shared_layer_name = get_resource_name(
            project_name, env_name, "shared", "layer"
        )

        # LambdaBase layer — third-party dependencies (Docker-bundled)
        self.dependencies_layer = lambda_.LayerVersion(
            self,
            "LambdaDependenciesLayer",
            code=lambda_.Code.from_asset(
                "services/lambdas/layers/dependencies",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    platform="linux/amd64",
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Third-party dependencies: powertools, boto3, etc.",
            layer_version_name=dependencies_layer_name,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Generic layer — shared custom utilities and exceptions
        self.shared_layer = lambda_.LayerVersion(
            self,
            "GenericLayer",
            code=lambda_.Code.from_asset("services/lambdas/layers/shared"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities: custom exceptions, response helpers, DDB helper",
            layer_version_name=shared_layer_name,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # --- Export layer ARNs via SSM for cross-stack consumption ---
        ssm.StringParameter(
            self,
            "DependenciesLayerArn",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "layers", "dependencies-arn"
            ),
            string_value=self.dependencies_layer.layer_version_arn,
        )

        ssm.StringParameter(
            self,
            "SharedLayerArn",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "layers", "shared-arn"
            ),
            string_value=self.shared_layer.layer_version_arn,
        )
