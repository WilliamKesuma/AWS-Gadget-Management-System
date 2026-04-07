from utils.enums import User_Role_Enum

VALID_GROUPS = {
    User_Role_Enum.IT_ADMIN,
    User_Role_Enum.MANAGEMENT,
    User_Role_Enum.EMPLOYEE,
    User_Role_Enum.FINANCE,
}


def require_group(event: dict, group: str) -> str:
    """Validate caller belongs to the required Cognito group.

    Returns the actor_id (sub claim) on success.
    Raises PermissionError (→ 403) if the caller is not in the required group.
    """
    claims = event["requestContext"]["authorizer"]["claims"]
    groups = claims.get("cognito:groups", "").split(",")
    if group not in groups:
        raise PermissionError(f"You are required to have {group} role")
    return claims["sub"]


def require_roles(event: dict, roles: list) -> tuple[str, str]:
    """Validate caller belongs to one of the allowed roles.

    Returns (actor_id, matched_role) on success.
    Raises PermissionError (→ 403) if the caller is not in any of the allowed roles.
    """
    claims = event["requestContext"]["authorizer"]["claims"]
    groups = claims.get("cognito:groups", "").split(",")
    for role in roles:
        role_value = role.value if hasattr(role, "value") else role
        if role_value in groups:
            return claims["sub"], role_value
    raise PermissionError("You do not have permission to access this resource")


def get_caller_info(event: dict) -> tuple[str, list[str]]:
    """Extract actor_id and group memberships from Cognito claims.

    Returns a tuple of (actor_id, groups) where:
      - actor_id is the Cognito sub claim
      - groups is a list of Cognito group names the caller belongs to
    """
    claims = event["requestContext"]["authorizer"]["claims"]
    actor_id = claims["sub"]
    groups = claims.get("cognito:groups", "").split(",")
    return actor_id, groups
