#!/usr/bin/env python3
import aws_cdk as cdk

from helpers.naming import get_resource_name
from helpers.environment import get_environment, get_project_name, get_env_name
from stacks.layer_stack import LayersStack
from stacks.storage_stack import StorageStack
from stacks.upload_stack import UploadStack
from stacks.scan_stack import ScanStack
from stacks.asset_stack import AssetStack
from stacks.user_stack import UserStack
from stacks.api_stack import ApiStack
from stacks.auth_stack import AuthStack
from stacks.handover_stack import HandoverStack
from stacks.software_governance_stack import SoftwareGovernanceStack
from stacks.issue_management_stack import IssueManagementStack
from stacks.issue_events_stack import IssueEventsStack
from stacks.return_stack import ReturnStack
from stacks.disposal_stack import DisposalStack
from stacks.notification_stack import NotificationStack
from stacks.websocket_stack import WebSocketStack
from stacks.email_notification_stack import EmailNotificationStack
from stacks.maintenance_stack import MaintenanceStack
from stacks.category_stack import CategoryStack
from stacks.counter_stack import CounterStack
from stacks.dashboard_stack import DashboardStack
from stacks.frontend_pipeline_stack import FrontendPipelineStack

app = cdk.App()

project_name = get_project_name()
env_name = get_env_name()
env = get_environment()

stack_kwargs = dict(project_name=project_name, env_name=env_name, env=env)

layers_stack = LayersStack(
    app, get_resource_name(project_name, env_name, "layers", "stack"), **stack_kwargs
)

storage_stack = StorageStack(
    app, get_resource_name(project_name, env_name, "storage", "stack"), **stack_kwargs
)

auth_stack = AuthStack(
    app, get_resource_name(project_name, env_name, "auth", "stack"), **stack_kwargs
)

upload_stack = UploadStack(
    app, get_resource_name(project_name, env_name, "upload", "stack"), **stack_kwargs
)

scan_stack = ScanStack(
    app, get_resource_name(project_name, env_name, "scan", "stack"), **stack_kwargs
)

asset_stack = AssetStack(
    app, get_resource_name(project_name, env_name, "asset", "stack"), **stack_kwargs
)

user_stack = UserStack(
    app, get_resource_name(project_name, env_name, "user", "stack"), **stack_kwargs
)

api_stack = ApiStack(
    app, get_resource_name(project_name, env_name, "api", "stack"), **stack_kwargs
)

handover_stack = HandoverStack(
    app, get_resource_name(project_name, env_name, "handover", "stack"), **stack_kwargs
)

software_governance_stack = SoftwareGovernanceStack(
    app,
    get_resource_name(project_name, env_name, "software-governance", "stack"),
    **stack_kwargs,
)

issue_management_stack = IssueManagementStack(
    app,
    get_resource_name(project_name, env_name, "issue-management", "stack"),
    **stack_kwargs,
)

issue_events_stack = IssueEventsStack(
    app,
    get_resource_name(project_name, env_name, "issue-events", "stack"),
    **stack_kwargs,
)

return_stack = ReturnStack(
    app, get_resource_name(project_name, env_name, "return", "stack"), **stack_kwargs
)

disposal_stack = DisposalStack(
    app,
    get_resource_name(project_name, env_name, "disposal", "stack"),
    **stack_kwargs,
)

notification_stack = NotificationStack(
    app,
    get_resource_name(project_name, env_name, "notification", "stack"),
    **stack_kwargs,
)

email_notification_stack = EmailNotificationStack(
    app,
    get_resource_name(project_name, env_name, "email-notification", "stack"),
    **stack_kwargs,
)

websocket_stack = WebSocketStack(
    app,
    get_resource_name(project_name, env_name, "websocket", "stack"),
    **stack_kwargs,
)

maintenance_stack = MaintenanceStack(
    app,
    get_resource_name(project_name, env_name, "maintenance", "stack"),
    **stack_kwargs,
)

category_stack = CategoryStack(
    app,
    get_resource_name(project_name, env_name, "category", "stack"),
    **stack_kwargs,
)

counter_stack = CounterStack(
    app,
    get_resource_name(project_name, env_name, "counter", "stack"),
    **stack_kwargs,
)

dashboard_stack = DashboardStack(
    app,
    get_resource_name(project_name, env_name, "dashboard", "stack"),
    **stack_kwargs,
)

storage_stack.add_dependency(layers_stack)
scan_stack.add_dependency(storage_stack)
upload_stack.add_dependency(storage_stack)
upload_stack.add_dependency(scan_stack)
asset_stack.add_dependency(storage_stack)
user_stack.add_dependency(storage_stack)
auth_stack.add_dependency(storage_stack)
api_stack.add_dependency(user_stack)
api_stack.add_dependency(upload_stack)
api_stack.add_dependency(scan_stack)
api_stack.add_dependency(asset_stack)
api_stack.add_dependency(auth_stack)
handover_stack.add_dependency(storage_stack)
software_governance_stack.add_dependency(storage_stack)
software_governance_stack.add_dependency(email_notification_stack)
issue_management_stack.add_dependency(storage_stack)
issue_management_stack.add_dependency(issue_events_stack)
issue_management_stack.add_dependency(email_notification_stack)
issue_events_stack.add_dependency(storage_stack)
return_stack.add_dependency(storage_stack)
return_stack.add_dependency(email_notification_stack)
api_stack.add_dependency(handover_stack)
api_stack.add_dependency(software_governance_stack)
api_stack.add_dependency(issue_management_stack)
api_stack.add_dependency(return_stack)
disposal_stack.add_dependency(storage_stack)
disposal_stack.add_dependency(email_notification_stack)
api_stack.add_dependency(disposal_stack)
notification_stack.add_dependency(storage_stack)
notification_stack.add_dependency(websocket_stack)
api_stack.add_dependency(notification_stack)
email_notification_stack.add_dependency(storage_stack)
api_stack.add_dependency(email_notification_stack)
websocket_stack.add_dependency(layers_stack)
websocket_stack.add_dependency(storage_stack)
maintenance_stack.add_dependency(storage_stack)
api_stack.add_dependency(maintenance_stack)
category_stack.add_dependency(layers_stack)
category_stack.add_dependency(storage_stack)
api_stack.add_dependency(category_stack)
counter_stack.add_dependency(storage_stack)
dashboard_stack.add_dependency(storage_stack)
api_stack.add_dependency(counter_stack)
api_stack.add_dependency(dashboard_stack)

frontend_pipeline_stack = FrontendPipelineStack(
    app,
    get_resource_name(project_name, env_name, "frontend-pipeline", "stack"),
    certificate_arn=app.node.try_get_context("certificate_arn"),
    domain_name=app.node.try_get_context("domain_name"),
    **stack_kwargs,
)
frontend_pipeline_stack.add_dependency(api_stack)
frontend_pipeline_stack.add_dependency(auth_stack)

# Apply cost allocation tags to all stacks
all_stacks = [
    layers_stack,
    storage_stack,
    auth_stack,
    upload_stack,
    scan_stack,
    asset_stack,
    user_stack,
    api_stack,
    handover_stack,
    software_governance_stack,
    issue_management_stack,
    issue_events_stack,
    return_stack,
    disposal_stack,
    notification_stack,
    websocket_stack,
    maintenance_stack,
    category_stack,
    counter_stack,
    dashboard_stack,
    frontend_pipeline_stack,
]
for stack in all_stacks:
    cdk.Tags.of(stack).add("Project", project_name)
    cdk.Tags.of(stack).add("Environment", env_name)

app.synth()
