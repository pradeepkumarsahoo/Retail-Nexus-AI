# Author: Pradeep Sahoo — Retail Nexus AI
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Annotated

from fastapi import Depends

from app.security.auth import authenticate, create_access_token

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    display_name: str


@router.post("/auth/token", response_model=TokenResponse)
def issue_token(form: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    user = authenticate(form.username, form.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user), role=user.role.value, display_name=user.display_name)
