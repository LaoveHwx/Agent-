"""Issue short-lived access tokens for the shared account."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.auth import authenticate


auth_router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@auth_router.post("/login")
async def login(request: LoginRequest):
    try:
        token = authenticate(request.username, request.password)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="登录服务尚未配置") from exc
    if token is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"access_token": token, "token_type": "bearer", "username": request.username}
