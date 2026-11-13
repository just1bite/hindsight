"""Single-admin authentication for Hindsight API.

# ponytail: single admin user from env; upgrade path: database-backed users table with RBAC.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import time
from typing import Any

import jwt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

DEFAULT_SECRET_KEY = "hindsight-insecure-secret-key-change-me"
TOKEN_EXPIRY_SECONDS = 86400  # 24 hours


class AuthConfig:
    def __init__(self) -> None:
        self.enabled = os.getenv("AUTH_ENABLED", os.getenv("HINDSIGHT_API_AUTH_ENABLED", "false")).lower() in (
            "true",
            "1",
            "yes",
        )
        self.username = os.getenv("AUTH_USERNAME", os.getenv("HINDSIGHT_API_AUTH_USERNAME", "admin"))
        self.password = os.getenv("AUTH_PASSWORD", os.getenv("HINDSIGHT_API_AUTH_PASSWORD", "admin"))
        self.secret_key = os.getenv("AUTH_SECRET_KEY", os.getenv("HINDSIGHT_API_AUTH_SECRET_KEY", DEFAULT_SECRET_KEY))
        self.api_key = os.getenv("AUTH_API_KEY", os.getenv("HINDSIGHT_API_AUTH_API_KEY", ""))
        self.allow_mcp = os.getenv("AUTH_ALLOW_MCP", os.getenv("HINDSIGHT_API_AUTH_ALLOW_MCP", "true")).lower() in (
            "true",
            "1",
            "yes",
        )


def get_auth_config() -> AuthConfig:
    return AuthConfig()


def create_access_token(username: str, secret_key: str, expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    now = int(time.time())  # noqa: TID251
    payload = {
        "sub": username,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_access_token(token: str, secret_key: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_EXPIRY_SECONDS
    username: str


class MeResponse(BaseModel):
    username: str
    authenticated: bool = True


auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response) -> LoginResponse:
    config = get_auth_config()
    username_ok = hmac.compare_digest(req.username, config.username)
    password_ok = hmac.compare_digest(req.password, config.password)

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(req.username, config.secret_key)
    response.set_cookie(
        key="access_token",
        value=token,
        max_age=TOKEN_EXPIRY_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=TOKEN_EXPIRY_SECONDS,
        username=req.username,
    )


@auth_router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key="access_token", path="/")
    return {"success": True}


@auth_router.get("/me", response_model=MeResponse)
async def me(request: Request) -> MeResponse:
    config = get_auth_config()
    token = _extract_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    if config.api_key and hmac.compare_digest(token, config.api_key):
        return MeResponse(username="api_key_user")

    claims = verify_access_token(token, config.secret_key)
    if not claims or "sub" not in claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return MeResponse(username=str(claims["sub"]))


def _extract_token_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth:
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        return auth.strip()

    x_api_key = request.headers.get("x-api-key")
    if x_api_key:
        return x_api_key.strip()

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token.strip()

    return None


class AuthMiddleware:
    """ASGI middleware for single admin auth enforcement."""

    EXEMPT_EXACT = {
        "/",
        "/health",
        "/health/ready",
        "/health/live",
        "/version",
        "/v1/version",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }

    EXEMPT_PREFIXES = (
        "/auth/login",
        "/auth/logout",
    )

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        config = get_auth_config()
        if not config.enabled:
            await self.app(scope, receive, send)
            return

        # Always permit OPTIONS for CORS preflight
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        # Check exact and prefix exemptions
        if path in self.EXEMPT_EXACT:
            await self.app(scope, receive, send)
            return

        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                await self.app(scope, receive, send)
                return

        # MCP agent bypass if configured
        if config.allow_mcp and path.startswith("/mcp"):
            await self.app(scope, receive, send)
            return

        # Extract credentials from ASGI headers
        token = self._extract_token_from_scope(scope)
        if token:
            if config.api_key and hmac.compare_digest(token, config.api_key):
                await self.app(scope, receive, send)
                return

            claims = verify_access_token(token, config.secret_key)
            if claims:
                scope.setdefault("state", {})["auth_user"] = claims.get("sub")
                await self.app(scope, receive, send)
                return

        # Reject with 401
        payload = json.dumps({"detail": "Unauthorized: Authentication required"}).encode("utf-8")
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(payload)).encode("utf-8")),
            (b"www-authenticate", b"Bearer"),
        ]
        await send({"type": "http.response.start", "status": 401, "headers": headers})
        await send({"type": "http.response.body", "body": payload})

    def _extract_token_from_scope(self, scope: Scope) -> str | None:
        headers = dict(scope.get("headers", []))

        # Authorization header
        auth = headers.get(b"authorization")
        if auth:
            try:
                auth_str = auth.decode("utf-8").strip()
                if auth_str.lower().startswith("bearer "):
                    return auth_str[7:].strip()
                return auth_str
            except UnicodeDecodeError:
                pass

        # X-API-Key header
        api_key = headers.get(b"x-api-key")
        if api_key:
            try:
                return api_key.decode("utf-8").strip()
            except UnicodeDecodeError:
                pass

        # Cookie header
        cookie = headers.get(b"cookie")
        if cookie:
            try:
                cookie_str = cookie.decode("utf-8")
                for part in cookie_str.split(";"):
                    k, _, v = part.strip().partition("=")
                    if k.strip() == "access_token":
                        return v.strip()
            except UnicodeDecodeError:
                pass

        return None
