from fastapi import Depends, Header, HTTPException

from src.models.user import Admin, User
from src.services.token_service import verify_access_token
from src.services.user_service import UserService


user_service: UserService | None = None


def get_user_service() -> UserService:
    global user_service
    if user_service is None:
        user_service = UserService()
    return user_service


def _extract_bearer_token(authorization: str | None) -> str:
    if not isinstance(authorization, str) or not authorization.strip():
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return parts[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    service: UserService = Depends(get_user_service),
) -> User:
    token = _extract_bearer_token(authorization)
    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload["sub"])
    # Отримуємо актуального користувача та його роль безпосередньо з бази даних
    user = service.get_user_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    service: UserService = Depends(get_user_service),
) -> User | None:
    if not isinstance(authorization, str) or not authorization.strip():
        return None

    return get_current_user(authorization=authorization, service=service)


def require_admin(
    current_user: User = Depends(get_current_user),
) -> Admin:
    if (
        current_user.get_role() != "Admin"
        or not isinstance(current_user, Admin)
        or not current_user.can_manage_products()
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )

    return current_user
