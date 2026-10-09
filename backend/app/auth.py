import os
from datetime import timedelta
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .db import User, session, now

passwords = PasswordHash.recommended()
SECRET = os.getenv("AUTH_SECRET", "development-only-change-this-secret-32-characters")
if os.getenv("ENVIRONMENT") == "production" and (
    len(SECRET) < 32 or SECRET.startswith("development-")
):
    raise RuntimeError(
        "Set a random AUTH_SECRET of at least 32 characters in production"
    )


def token(user):
    return jwt.encode(
        {
            "sub": user.id,
            "exp": now() + timedelta(hours=8),
            "iat": now(),
            "iss": "closetwise",
        },
        SECRET,
        algorithm="HS256",
    )


def current(request: Request, s: Session = Depends(session)):
    value = request.cookies.get("closetwise_session")
    if not value:
        raise HTTPException(
            401, detail={"code": "UNAUTHENTICATED", "message": "Sign in to continue."}
        )
    try:
        claims = jwt.decode(
            value,
            SECRET,
            algorithms=["HS256"],
            issuer="closetwise",
            options={"require": ["sub", "exp", "iat", "iss"]},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            401,
            detail={
                "code": "UNAUTHENTICATED",
                "message": "Your session expired. Sign in again.",
            },
        )
    user = s.get(User, claims["sub"])
    if not user:
        raise HTTPException(
            401, detail={"code": "UNAUTHENTICATED", "message": "Account not found."}
        )
    return user


def set_cookie(response, user):
    response.set_cookie(
        "closetwise_session",
        token(user),
        httponly=True,
        samesite="lax",
        secure=os.getenv("ENVIRONMENT") == "production",
        max_age=28800,
        path="/",
    )
