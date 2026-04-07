import simplejson as json
from aws_lambda_powertools import Logger

logger = Logger(child=True)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def success(body: dict, status_code: int = 200) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }


def error(message: str, status_code: int = 400) -> dict:
    if status_code >= 500:
        logger.error(message, status_code=status_code)
    else:
        logger.warning(message, status_code=status_code)

    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"message": message}),
    }
