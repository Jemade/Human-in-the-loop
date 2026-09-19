from typing import Optional
from fastapi import Header, HTTPException, status
from app.config import get_settings

settings = get_settings()


def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> bool:
    """
    Verifies that the caller has a valid API key or Bearer token.
    If settings.REQUIRE_AUTH is False, requests without keys are allowed.
    """
    if not settings.REQUIRE_AUTH:
        return True

    provided_token = None
    if x_api_key:
        provided_token = x_api_key.strip()
    elif authorization and authorization.startswith("Bearer "):
        provided_token = authorization.replace("Bearer ", "").strip()

    if not provided_token or provided_token != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Provide 'X-API-Key' or 'Authorization: Bearer <token>' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return True


def get_current_actor(
    x_actor_id: Optional[str] = Header(None, alias="X-Actor-Id"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Extracts the actor identifier for the audit trail.
    If provided via X-Actor-Id, uses that (e.g. 'human:alice', 'manager:bob').
    Otherwise falls back to 'human:reviewer' or 'system:api'.
    """
    if x_actor_id and x_actor_id.strip():
        return x_actor_id.strip()

    if x_api_key or authorization:
        return "human:authenticated_reviewer"

    return "human:reviewer"
