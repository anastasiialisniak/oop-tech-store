from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.api.dependencies import get_user_service
from src.services.user_service import UserService
from src.services.token_service import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(
    request: RegisterRequest,
    service: UserService = Depends(get_user_service),
):
    try:
        user = service.register_user(
            request.name,
            str(request.email),
            request.password,
        )

        token = create_access_token(
            user_id=user.get_user_id(),
            role=user.get_role(),
        )

        return {
            "message": "Registration successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "name": user.get_name(),
                "email": user.get_email(),
                "role": user.get_role(),
            },
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post("/login")
def login(
    request: LoginRequest,
    service: UserService = Depends(get_user_service),
):
    user = service.authenticate_user(
        str(request.email),
        request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(
        user_id=user.get_user_id(),
        role=user.get_role(),
    )

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "name": user.get_name(),
            "email": user.get_email(),
            "role": user.get_role(),
        },
    }
