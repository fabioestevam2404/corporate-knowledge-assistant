from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cka.api.dependencies import AuthenticateUserDep
from cka.application.authenticate_user import InvalidCredentialsError

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest, authenticate_user: AuthenticateUserDep) -> LoginResponse:
    try:
        token = authenticate_user(request.username, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail="Invalid username or password.") from exc

    return LoginResponse(access_token=token)
