
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from src.services.user_service import UserService
from src.services.token_service import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])

user_service = UserService()


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register")
def register(request: RegisterRequest):
    try:
        user = user_service.register_user(
            request.name,
            str(request.email),
            request.password,
        )

        token = create_access_token(user_id=user.get_user_id())

        return {
            "message": "Registration successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "name": request.name,
                "email": str(request.email),
                "role": user.get_role(),
            },
        }

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )


@router.post("/login")
def login(request: LoginRequest):
    user = user_service.authenticate_user(
        str(request.email),
        request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    token = create_access_token(user_id=user.get_user_id())

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "email": str(request.email),
            "role": user.get_role(),
        },
    }
