"""Issue Events stack — EventBridge bus + rule for ReplacementApproved events."""

from aws_cdk import Stack, aws_events as events, aws_ssm as ssm
from constructs import Construct

from helpers.naming import get_resource_name, get_ssm_parameter_path


class IssueEventsStack(Stack):
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

        bus_name = get_resource_name(project_name, env_name, "issue-events")

        # Custom EventBridge bus for issue management events
        event_bus = events.EventBus(
            self,
            "IssueEventBus",
            event_bus_name=bus_name,
        )

        # Export bus name and ARN to SSM
        ssm.StringParameter(
            self,
            "IssueEventBusNameParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "events", "issue-event-bus-name"
            ),
            string_value=event_bus.event_bus_name,
        )

        ssm.StringParameter(
            self,
            "IssueEventBusArnParam",
            parameter_name=get_ssm_parameter_path(
                project_name, env_name, "events", "issue-event-bus-arn"
            ),
            string_value=event_bus.event_bus_arn,
        )

        # Rule: ReplacementApproved → logs to CloudWatch (downstream consumers
        # like Phase 5 Return Process can add targets to this rule or create
        # additional rules on the same bus)
        events.Rule(
            self,
            "ReplacementApprovedRule",
            rule_name=get_resource_name(project_name, env_name, "replacement-approved"),
            event_bus=event_bus,
            event_pattern=events.EventPattern(
                source=["gms.issue-management"],
                detail_type=["ReplacementApproved"],
            ),
            description="Fires when a replacement request is approved by management — triggers Phase 5 Return Process",
        )
