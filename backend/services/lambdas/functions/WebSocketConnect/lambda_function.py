"""$connect handler — validates Cognito token and stores connection in DynamoDB."""

import os
import time

import boto3
import jwt
from aws_lambda_powertools import Logger, Tracer

logger = Logger()
tracer = Tracer()

CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]
USER_POOL_ID = os.environ["USER_POOL_ID"]
REGION = os.environ.get("AWS_REGION", "us-east-1")

dynamodb = boto3.resource("dynamodb")
connections_table = dynamodb.Table(CONNECTIONS_TABLE)

# Cognito JWKS client (caches keys automatically)
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        jwks_url = (
            f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}"
            "/.well-known/jwks.json"
        )
        _jwks_client = jwt.PyJWKClient(jwks_url)
    return _jwks_client


def _decode_token(token: str) -> dict:
    """Decode and validate a Cognito ID token. Returns claims dict."""
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        issuer=f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}",
        options={"verify_aud": False},
    )
    return claims


@tracer.capture_lambda_handler
@logger.inject_lambda_context(log_event=True)
def lambda_handler(event, context):
    connection_id = event["requestContext"]["connectionId"]

    # Token passed as query string: ?token=<id_token>
    qs = event.get("queryStringParameters") or {}
    token = qs.get("token")

    if not token:
        logger.warning("No token provided on $connect")
        return {"statusCode": 401, "body": "Missing token"}

    try:
        claims = _decode_token(token)
    except Exception:
        logger.exception("Token validation failed")
        return {"statusCode": 401, "body": "Invalid token"}

    user_id = claims.get("sub", "")
    groups = claims.get("cognito:groups", "")
    if isinstance(groups, list):
        groups = ",".join(groups)

    # Store connection with 24h TTL
    ttl = int(time.time()) + 86400

    connections_table.put_item(
        Item={
            "ConnectionID": connection_id,
            "UserID": user_id,
            "Groups": groups,
            "ConnectedAt": int(time.time()),
            "TTL": ttl,
        }
    )

    logger.info("Connection stored", connection_id=connection_id, user_id=user_id)
    return {"statusCode": 200, "body": "Connected"}
