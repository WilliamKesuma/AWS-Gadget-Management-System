"""Shared helpers for Lambda feature stacks."""

from dataclasses import dataclass, field

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_ecr_assets as ecr_assets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_ssm as ssm,
)

from helpers.naming import get_resource_name, get_ssm_parameter_path


@dataclass
class PolicyConfig:
    """A single IAM policy statement to attach to a Lambda role."""

    actions: list[str]
    resources: list[str] = field(default_factory=lambda: ["*"])


class LambdaStackContext:
    """Holds shared SSM lookups, layer refs, and ARNs for a Lambda feature stack."""

    def __init__(self, stack: Stack, project_name: str, env_name: str) -> None:
        self.stack = stack
        self.project_name = project_name
        self.env_name = env_name

        # SSM lookups
        deps_arn = ssm.StringParameter.value_for_string_parameter(
            scope=stack,
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "layers", "dependencies-arn"
            ),
        )
        shared_arn = ssm.StringParameter.value_for_string_parameter(
            scope=stack,
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "layers", "shared-arn"
            ),
        )
        self.bucket_name = ssm.StringParameter.value_for_string_parameter(
            scope=stack,
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-bucket-name"
            ),
        )
        self.table_name = ssm.StringParameter.value_for_string_parameter(
            scope=stack,
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-table-name"
            ),
        )

        # Layer references
        self.dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            stack, "ImportedDependenciesLayer", deps_arn
        )
        self.shared_layer = lambda_.LayerVersion.from_layer_version_arn(
            stack, "ImportedSharedLayer", shared_arn
        )

        # ARN constructions
        self.table_arn = (
            f"arn:aws:dynamodb:{stack.region}:{stack.account}:table/{self.table_name}"
        )
        self.table_gsi_arn = f"{self.table_arn}/index/*"
        self.bucket_arn = f"arn:aws:s3:::{self.bucket_name}"
        self.bucket_objects_arn = f"arn:aws:s3:::{self.bucket_name}/*"


def create_lambda_function(
    ctx: LambdaStackContext,
    *,
    purpose: str,
    directory: str,
    construct_prefix: str,
    policies: list[PolicyConfig] | None = None,
    timeout_seconds: int | None = None,
) -> lambda_.Function:
    """Create a Lambda function with dedicated IAM role, log group, and SSM export.

    Args:
        ctx: Shared stack context (layers, ARNs, env).
        purpose: Hyphenated function purpose for naming (e.g. "create-asset").
        directory: Lambda source directory under services/lambdas/functions/.
        construct_prefix: PascalCase prefix for CDK construct IDs.
        policies: Additional IAM policy statements beyond the base
                  CloudWatch Logs + X-Ray policies.
    """
    stack = ctx.stack
    fn_name = get_resource_name(ctx.project_name, ctx.env_name, purpose)
    role_name = get_resource_name(ctx.project_name, ctx.env_name, purpose, "role")
    log_group_path = f"/{ctx.project_name}/{ctx.env_name}/{purpose}"

    # IAM Role
    role = iam.Role(
        stack,
        f"{construct_prefix}Role",
        role_name=role_name,
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )

    # Base policy: CloudWatch Logs (no CreateLogGroup — CDK manages the log group)
    role.add_to_policy(
        iam.PolicyStatement(
            actions=[
                "logs:CreateLogStream",
                "logs:PutLogEvents",
            ],
            resources=[
                f"arn:aws:logs:{stack.region}:{stack.account}:log-group:{log_group_path}:*"
            ],
        )
    )

    # Base policy: X-Ray
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
            resources=["*"],
        )
    )

    # Additional policies
    for policy in policies or []:
        role.add_to_policy(
            iam.PolicyStatement(actions=policy.actions, resources=policy.resources)
        )

    # Log Group
    log_group = logs.LogGroup(
        stack,
        f"{construct_prefix}LogGroup",
        log_group_name=log_group_path,
        retention=logs.RetentionDays.INFINITE,
        removal_policy=RemovalPolicy.DESTROY,
    )

    # Lambda Function
    fn = lambda_.Function(
        stack,
        f"{construct_prefix}Function",
        function_name=fn_name,
        runtime=lambda_.Runtime.PYTHON_3_12,
        handler="lambda_function.lambda_handler",
        code=lambda_.Code.from_asset(f"services/lambdas/functions/{directory}"),
        role=role,
        layers=[ctx.dependencies_layer, ctx.shared_layer],
        environment={
            "ASSETS_TABLE": ctx.table_name,
            "ASSETS_BUCKET": ctx.bucket_name,
        },
        tracing=lambda_.Tracing.ACTIVE,
        log_group=log_group,
        timeout=Duration.seconds(timeout_seconds) if timeout_seconds else None,
    )

    # Ensure the log group exists before the function runs,
    # so Lambda never auto-creates a competing log group.
    fn.node.add_dependency(log_group)

    # Export function ARN to SSM
    ssm.StringParameter(
        stack,
        f"{construct_prefix}FunctionArn",
        parameter_name=get_ssm_parameter_path(
            ctx.project_name, ctx.env_name, "functions", f"{purpose}-arn"
        ),
        string_value=fn.function_arn,
    )

    return fn


def create_docker_lambda_function(
    ctx: LambdaStackContext,
    *,
    purpose: str,
    directory: str,
    construct_prefix: str,
    dockerfile_dir: str,
    policies: list[PolicyConfig] | None = None,
    timeout_seconds: int | None = None,
    memory_size: int = 512,
) -> lambda_.DockerImageFunction:
    """Create a Docker-image Lambda function with dedicated IAM role, log group, and SSM export.

    Used for Lambdas that require system-level dependencies (e.g. WeasyPrint needs
    Pango/HarfBuzz) that cannot be packaged in a standard Lambda layer.

    The Docker build context is the project root (``"."``). The Dockerfile is
    located at ``dockerfile_dir/Dockerfile`` and uses a ``FUNCTION_DIR`` build arg
    to COPY the correct Lambda handler code into the image.

    Args:
        ctx: Shared stack context (layers, ARNs, env).
        purpose: Hyphenated function purpose for naming (e.g. "assign-asset").
        directory: Lambda source directory under services/lambdas/functions/.
        construct_prefix: PascalCase prefix for CDK construct IDs.
        dockerfile_dir: Path to the directory containing the Dockerfile (relative to
                        project root, e.g. "services/lambdas/docker/pdf").
        policies: Additional IAM policy statements.
        timeout_seconds: Lambda timeout in seconds.
        memory_size: Lambda memory in MB (default 512 for WeasyPrint).
    """
    stack = ctx.stack
    fn_name = get_resource_name(ctx.project_name, ctx.env_name, purpose)
    role_name = get_resource_name(ctx.project_name, ctx.env_name, purpose, "role")
    log_group_path = f"/{ctx.project_name}/{ctx.env_name}/{purpose}"

    # IAM Role
    role = iam.Role(
        stack,
        f"{construct_prefix}Role",
        role_name=role_name,
        assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    )

    # Base policy: CloudWatch Logs
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["logs:CreateLogStream", "logs:PutLogEvents"],
            resources=[
                f"arn:aws:logs:{stack.region}:{stack.account}:log-group:{log_group_path}:*"
            ],
        )
    )

    # Base policy: X-Ray
    role.add_to_policy(
        iam.PolicyStatement(
            actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
            resources=["*"],
        )
    )

    # Additional policies
    for policy in policies or []:
        role.add_to_policy(
            iam.PolicyStatement(actions=policy.actions, resources=policy.resources)
        )

    # Log Group
    log_group = logs.LogGroup(
        stack,
        f"{construct_prefix}LogGroup",
        log_group_name=log_group_path,
        retention=logs.RetentionDays.INFINITE,
        removal_policy=RemovalPolicy.DESTROY,
    )

    # Docker Image Lambda — build context is project root so the Dockerfile
    # can COPY from services/lambdas/functions/<dir> and layers/shared/python.
    fn = lambda_.DockerImageFunction(
        stack,
        f"{construct_prefix}Function",
        function_name=fn_name,
        code=lambda_.DockerImageCode.from_image_asset(
            ".",
            file=f"{dockerfile_dir}/Dockerfile",
            build_args={
                "FUNCTION_DIR": f"services/lambdas/functions/{directory}",
            },
            platform=ecr_assets.Platform.LINUX_AMD64,
        ),
        role=role,
        environment={
            "ASSETS_TABLE": ctx.table_name,
            "ASSETS_BUCKET": ctx.bucket_name,
        },
        tracing=lambda_.Tracing.ACTIVE,
        log_group=log_group,
        timeout=Duration.seconds(timeout_seconds) if timeout_seconds else None,
        memory_size=memory_size,
    )

    fn.node.add_dependency(log_group)

    # Export function ARN to SSM
    ssm.StringParameter(
        stack,
        f"{construct_prefix}FunctionArn",
        parameter_name=get_ssm_parameter_path(
            ctx.project_name, ctx.env_name, "functions", f"{purpose}-arn"
        ),
        string_value=fn.function_arn,
    )

    return fn
