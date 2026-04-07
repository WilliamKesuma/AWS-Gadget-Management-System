"""
Naming helper functions for standardized AWS resource naming.

This module provides utility functions to generate consistent resource names
following the pattern: {project}-{env}-{resource-specific-parts}
All names use lowercase with hyphens for consistency.
"""


def get_resource_name(project: str, env: str, *parts: str) -> str:
    """
    Generate standardized resource name.
    
    Args:
        project: Project identifier (e.g., "ecommerce")
        env: Environment identifier (e.g., "dev", "staging", "prod")
        *parts: Additional name components
    
    Returns:
        Hyphenated lowercase resource name
    
    Example:
        get_resource_name("ecommerce", "dev", "create", "user")
        # Returns: "ecommerce-dev-create-user"
    """
    all_parts = [project, env] + list(parts)
    return "-".join(all_parts).lower()


def get_ssm_parameter_path(project: str, env: str, category: str, name: str) -> str:
    """
    Generate SSM parameter path.
    
    Args:
        project: Project identifier
        env: Environment identifier
        category: Parameter category (e.g., "config", "layers")
        name: Parameter name
    
    Returns:
        SSM parameter path
    
    Example:
        get_ssm_parameter_path("ecommerce", "dev", "config", "stripe-secret-arn")
        # Returns: "/ecommerce/dev/config/stripe-secret-arn"
    """
    return f"/{project}/{env}/{category}/{name}"
