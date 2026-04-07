from aws_cdk import (
    RemovalPolicy,
    Stack,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_ssm as ssm,
)
from constructs import Construct
from helpers.naming import get_resource_name, get_ssm_parameter_path


class AuthStack(Stack):
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

        # Generate standardized user pool name
        user_pool_name = get_resource_name(project_name, env_name, "user", "pool")
        app_client_name = get_resource_name(project_name, env_name, "app", "client")
        user_pool_domain_name = get_resource_name(project_name, env_name, "domain")

        # ── Layer lookups ──────────────────────────────────────────
        dependencies_layer_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "layers", "dependencies-arn"
            ),
        )
        shared_layer_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "layers", "shared-arn"),
        )
        dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ImportedDependenciesLayer", dependencies_layer_arn
        )
        shared_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ImportedSharedLayer", shared_layer_arn
        )

        table_name = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-table-name"
            ),
        )
        bucket_name = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "storage", "assets-bucket-name"
            ),
        )

        # ── PostConfirmation Lambda ────────────────────────────────
        fn_name = get_resource_name(project_name, env_name, "cognito-post-confirmation")
        role_name = get_resource_name(
            project_name, env_name, "cognito-post-confirmation", "role"
        )

        post_confirmation_role = iam.Role(
            self,
            "PostConfirmationRole",
            role_name=role_name,
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        post_confirmation_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/lambda/{fn_name}:*"
                ],
            )
        )
        post_confirmation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["xray:PutTraceSegments", "xray:PutTelemetryRecords"],
                resources=["*"],
            )
        )
        table_arn = f"arn:aws:dynamodb:{self.region}:{self.account}:table/{table_name}"
        post_confirmation_role.add_to_policy(
            iam.PolicyStatement(
                actions=["dynamodb:PutItem"],
                resources=[table_arn],
            )
        )

        self.post_confirmation_fn = lambda_.Function(
            self,
            "PostConfirmationFunction",
            function_name=fn_name,
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset(
                "services/lambdas/functions/CognitoPostConfirmation"
            ),
            role=post_confirmation_role,
            layers=[dependencies_layer, shared_layer],
            environment={
                "ASSETS_TABLE": table_name,
                "ASSETS_BUCKET": bucket_name,
                "POWERTOOLS_SERVICE_NAME": fn_name,
            },
            tracing=lambda_.Tracing.ACTIVE,
        )

        self.user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=user_pool_name,
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            custom_attributes={
                "role": cognito.StringAttribute(mutable=True),
            },
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_uppercase=True,
                require_lowercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            lambda_triggers=cognito.UserPoolTriggers(
                post_confirmation=self.post_confirmation_fn,
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )

        # User groups
        cognito.CfnUserPoolGroup(
            self,
            "ITAdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="it-admin",
            description="Executes asset creation, assignment, software approval, issue validation, return inspection, and audit initiation",
        )

        cognito.CfnUserPoolGroup(
            self,
            "ManagementGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="management",
            description="Approves asset creation, software installation requests, replacements, and disposals",
        )

        cognito.CfnUserPoolGroup(
            self,
            "EmployeeGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="employee",
            description="Accepts assignments, submits software or issue requests, returns assets, and executes audit confirmations",
        )

        cognito.CfnUserPoolGroup(
            self,
            "FinanceGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="finance",
            description="Executes write-off processing, depreciation adjustments, and asset register updates upon receiving disposal notifications",
        )

        # CloudFront callback URL
        # TODO: Uncomment when frontend stack is deployed and SSM param exists
        # cloudfront_domain = ssm.StringParameter.value_for_string_parameter(
        #     self,
        #     get_ssm_parameter_path(
        #         project_name, env_name, "frontend", "distribution-domain"
        #     ),
        # )
        # cloudfront_url = Fn.join("", ["https://", cloudfront_domain])

        self.app_client = self.user_pool.add_client(
            "AppClient",
            user_pool_client_name=app_client_name,
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True),
            o_auth=cognito.OAuthSettings(
                callback_urls=["http://localhost:3000"],
                logout_urls=["http://localhost:3000"],
            ),
        )

        self.pool_domain = self.user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=user_pool_domain_name
            ),
            managed_login_version=cognito.ManagedLoginVersion.NEWER_MANAGED_LOGIN,
        )

        # Export Cognito identifiers to SSM for cross-stack consumption
        ssm.StringParameter(
            self,
            "UserPoolIdParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "auth", "user-pool-id"
            ),
            string_value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
        )

        ssm.StringParameter(
            self,
            "AppClientIdParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "auth", "app-client-id"
            ),
            string_value=self.app_client.user_pool_client_id,
            description="Cognito App Client ID",
        )
