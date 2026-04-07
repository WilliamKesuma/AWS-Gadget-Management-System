import os
import aws_cdk as cdk

PROJECT_NAME = "gms"
ENVIRONMENT = "production"
REGION = "ap-southeast-1"


def get_environment() -> cdk.Environment:
    """Get CDK environment configuration."""
    return cdk.Environment(region=REGION)


def get_project_name() -> str:
    """Get project identifier."""
    return PROJECT_NAME


def get_env_name() -> str:
    """
    Get environment identifier.
    
    Checks DEPLOY_ENV environment variable first, falls back to default.
    
    Returns:
        Environment identifier (dev, staging, or prod)
    """
    return os.environ.get("DEPLOY_ENV", ENVIRONMENT)
