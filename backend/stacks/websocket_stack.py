"""WebSocket stack — API Gateway WebSocket API, connection Lambdas, and SSM parameters."""

from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_ssm as ssm,
)
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class WebSocketStack(Stack):
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

        # ── SSM Lookups ────────────────────────────────────────────
        deps_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(
                project_name, env_name, "layers", "dependencies-arn"
            ),
        )
        shared_arn = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "layers", "shared-arn"),
        )
        dependencies_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ImportedDependenciesLayer", deps_arn
        )
        shared_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "ImportedSharedLayer", shared_arn
        )

        user_pool_id = ssm.StringParameter.value_for_string_parameter(
            self,
            get_ssm_parameter_path(project_name, env_name, "auth", "user-pool-id"),
        )

        # ── DynamoDB Connections Table ─────────────────────────────
        connections_table = dynamodb.Table(
            self,
            "WebSocketConnectionsTable",
            table_name=get_resource_name(project_name, env_name, "ws-connections"),
            partition_key=dynamodb.Attribute(
                name="ConnectionID", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="TTL",
        )

        # GSI: look up connections by UserID
        connections_table.add_global_secondary_index(
            index_name="UserIDIndex",
            partition_key=dynamodb.Attribute(
                name="UserID", type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        connections_table_arn = connections_table.table_arn
        connections_table_gsi_arn = f"{connections_table_arn}/index/*"

        # ── WebSocket API ──────────────────────────────────────────
        ws_api = apigwv2.CfnApi(
            self,
            "WebSocketApi",
            name=get_resource_name(project_name, env_name, "ws-api"),
            protocol_type="WEBSOCKET",
            route_selection_expression="$request.body.action",
        )

        # ── Helper to create a WebSocket Lambda ────────────────────
        def _create_ws_lambda(
            purpose: str,
            directory: str,
            construct_prefix: str,
            extra_policies: list[dict] | None = None,
            timeout_seconds: int = 10,
        ) -> lambda_.Function:
            fn_name = get_resource_name(project_name, env_name, purpose)
            role_name = get_resource_name(project_name, env_name, purpose, "role")
            log_group_path = f"/{project_name}/{env_name}/{purpose}"

            role = iam.Role(
                self,
                f"{construct_prefix}Role",
                role_name=role_name,
                assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            )
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[
                        f"arn:aws:logs:{self.region}:{self.account}:log-group:{log_group_path}:*"
                    ],
                )
            )
            role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                    ],
                    resources=["*"],
                )
            )
            for p in extra_policies or []:
                role.add_to_policy(
                    iam.PolicyStatement(actions=p["actions"], resources=p["resources"])
                )

            log_group = logs.LogGroup(
                self,
                f"{construct_prefix}LogGroup",
                log_group_name=log_group_path,
                retention=logs.RetentionDays.INFINITE,
                removal_policy=RemovalPolicy.DESTROY,
            )

            fn = lambda_.Function(
                self,
                f"{construct_prefix}Function",
                function_name=fn_name,
                runtime=lambda_.Runtime.PYTHON_3_12,
                handler="lambda_function.lambda_handler",
                code=lambda_.Code.from_asset(f"services/lambdas/functions/{directory}"),
                role=role,
                layers=[dependencies_layer, shared_layer],
                environment={
                    "CONNECTIONS_TABLE": connections_table.table_name,
                    "USER_POOL_ID": user_pool_id,
                },
                tracing=lambda_.Tracing.ACTIVE,
                log_group=log_group,
                timeout=Duration.seconds(timeout_seconds),
            )
            fn.node.add_dependency(log_group)
            return fn

        # ── $connect Lambda ────────────────────────────────────────
        connect_fn = _create_ws_lambda(
            purpose="ws-connect",
            directory="WebSocketConnect",
            construct_prefix="WsConnect",
            extra_policies=[
                {
                    "actions": ["dynamodb:PutItem"],
                    "resources": [connections_table_arn],
                },
            ],
        )

        # ── $disconnect Lambda ─────────────────────────────────────
        disconnect_fn = _create_ws_lambda(
            purpose="ws-disconnect",
            directory="WebSocketDisconnect",
            construct_prefix="WsDisconnect",
            extra_policies=[
                {
                    "actions": ["dynamodb:DeleteItem"],
                    "resources": [connections_table_arn],
                },
            ],
        )

        # ── $default Lambda ────────────────────────────────────────
        default_fn = _create_ws_lambda(
            purpose="ws-default",
            directory="WebSocketDefault",
            construct_prefix="WsDefault",
        )

        # ── Integrations ──────────────────────────────────────────
        def _create_integration(
            construct_id_name: str, fn: lambda_.Function
        ) -> apigwv2.CfnIntegration:
            return apigwv2.CfnIntegration(
                self,
                construct_id_name,
                api_id=ws_api.ref,
                integration_type="AWS_PROXY",
                integration_uri=(
                    f"arn:aws:apigateway:{self.region}"
                    f":lambda:path/2015-03-31/functions/{fn.function_arn}/invocations"
                ),
            )

        connect_integration = _create_integration("ConnectIntegration", connect_fn)
        disconnect_integration = _create_integration(
            "DisconnectIntegration", disconnect_fn
        )
        default_integration = _create_integration("DefaultIntegration", default_fn)

        # ── Routes ─────────────────────────────────────────────────
        connect_route = apigwv2.CfnRoute(
            self,
            "ConnectRoute",
            api_id=ws_api.ref,
            route_key="$connect",
            authorization_type="NONE",
            target=f"integrations/{connect_integration.ref}",
        )

        disconnect_route = apigwv2.CfnRoute(
            self,
            "DisconnectRoute",
            api_id=ws_api.ref,
            route_key="$disconnect",
            target=f"integrations/{disconnect_integration.ref}",
        )

        default_route = apigwv2.CfnRoute(
            self,
            "DefaultRoute",
            api_id=ws_api.ref,
            route_key="$default",
            target=f"integrations/{default_integration.ref}",
        )

        # ── Deployment & Stage ─────────────────────────────────────
        deployment = apigwv2.CfnDeployment(
            self,
            "WebSocketDeployment",
            api_id=ws_api.ref,
        )
        deployment.add_dependency(connect_route)
        deployment.add_dependency(disconnect_route)
        deployment.add_dependency(default_route)

        stage = apigwv2.CfnStage(
            self,
            "WebSocketStage",
            api_id=ws_api.ref,
            stage_name=env_name,
            deployment_id=deployment.ref,
        )

        # ── Lambda Invoke Permissions ──────────────────────────────
        for fn in [connect_fn, disconnect_fn, default_fn]:
            fn.add_permission(
                "AllowApiGwInvoke",
                principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
                source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{ws_api.ref}/*",
            )

        # ── SSM Exports ───────────────────────────────────────────
        ws_endpoint = (
            f"wss://{ws_api.ref}.execute-api.{self.region}.amazonaws.com/{env_name}"
        )

        ssm.StringParameter(
            self,
            "WsApiEndpoint",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "websocket", "endpoint"
            ),
            string_value=ws_endpoint,
        )

        ssm.StringParameter(
            self,
            "WsApiId",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "websocket", "api-id"
            ),
            string_value=ws_api.ref,
        )

        ssm.StringParameter(
            self,
            "WsConnectionsTableName",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "websocket", "connections-table-name"
            ),
            string_value=connections_table.table_name,
        )

        ssm.StringParameter(
            self,
            "WsConnectionsTableArn",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "websocket", "connections-table-arn"
            ),
            string_value=connections_table_arn,
        )
