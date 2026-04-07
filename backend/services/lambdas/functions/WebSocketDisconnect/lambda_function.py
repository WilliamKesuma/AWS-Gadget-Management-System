"""$disconnect handler — removes connection record from DynamoDB."""

import os

import boto3
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()

CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]

dynamodb = boto3.resource("dynamodb")
connections_table = dynamodb.Table(CONNECTIONS_TABLE)


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]

    connections_table.delete_item(Key={"ConnectionID": connection_id})

    logger.info("Connection removed", connection_id=connection_id)
    return {"statusCode": 200, "body": "Disconnected"}
