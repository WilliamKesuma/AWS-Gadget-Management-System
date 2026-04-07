"""$default handler — responds to unrecognized WebSocket messages with a no-op."""

from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]
    logger.info("Default route hit", connection_id=connection_id)
    return {"statusCode": 200, "body": "No action"}
