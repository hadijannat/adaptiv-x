"""OIDC/JWT authentication helpers for Adaptiv-X services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Awaitable, Callable, cast

import httpx
from jose import jwk, jwt  # type: ignore[import-untyped]
from jose.exceptions import JWTError  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


class AuthSettings(BaseModel):
    enabled: bool = False
    issuer: str | None = None
    audience: str | None = None
    jwks_url: str | None = None
    algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    cache_ttl_seconds: int = 300
    allow_paths: list[str] = Field(
        default_factory=lambda: [
            "/health",
            "/healthz",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
    )


class AuthError(Exception):
    """Authentication error."""


@dataclass
class JwksCache:
    jwks_url: str
    ttl_seconds: int
    _keys: dict[str, Any]
    _expires_at: datetime

    def __init__(self, jwks_url: str, ttl_seconds: int) -> None:
        self.jwks_url = jwks_url
        self.ttl_seconds = ttl_seconds
        self._keys = {}
        self._expires_at = datetime.fromtimestamp(0, tz=UTC)

    def _is_expired(self) -> bool:
        return datetime.now(tz=UTC) >= self._expires_at

    async def refresh(self) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(self.jwks_url)
            response.raise_for_status()
            payload = response.json()

        keys = {}
        for key in payload.get("keys", []):
            kid = key.get("kid")
            if kid:
                keys[kid] = key
        self._keys = keys
        self._expires_at = datetime.now(tz=UTC) + timedelta(seconds=self.ttl_seconds)

    async def get_key(self, kid: str | None) -> Any:
        if self._is_expired() or (kid and kid not in self._keys):
            await self.refresh()
        if kid:
            return self._keys.get(kid)
        if len(self._keys) == 1:
            return next(iter(self._keys.values()))
        return None


class AuthVerifier:
    """Verify JWTs against OIDC JWKS endpoint."""

    def __init__(self, settings: AuthSettings) -> None:
        self.settings = settings
        if settings.enabled:
            self.jwks_url = self._resolve_jwks_url(settings)
        else:
            self.jwks_url = settings.jwks_url or ""
        self.cache = JwksCache(self.jwks_url, settings.cache_ttl_seconds)

    def _resolve_jwks_url(self, settings: AuthSettings) -> str:
        if settings.jwks_url:
            return settings.jwks_url
        if settings.issuer:
            return settings.issuer.rstrip("/") + "/protocol/openid-connect/certs"
        raise AuthError("OIDC JWKS URL or issuer must be configured when auth is enabled")

    async def verify(self, token: str) -> dict[str, Any]:
        if not self.settings.issuer:
            raise AuthError("OIDC_ISSUER must be configured when auth is enabled")
        if not self.settings.audience:
            raise AuthError("OIDC_AUDIENCE must be configured when auth is enabled")

        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            jwk_data = await self.cache.get_key(kid)
            if not jwk_data:
                raise AuthError("Unable to resolve signing key")

            key = jwk.construct(jwk_data)
            claims = jwt.decode(
                token,
                key,
                algorithms=self.settings.algorithms,
                audience=self.settings.audience,
                issuer=self.settings.issuer,
            )
            return cast(dict[str, Any], claims)
        except JWTError as exc:
            raise AuthError("Invalid token") from exc


def _extract_bearer(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    if not auth_header.lower().startswith("bearer "):
        return None
    return auth_header.split(" ", 1)[1].strip()


def auth_middleware(
    verifier: AuthVerifier,
) -> Callable[[Request, Callable[[Request], Awaitable[Any]]], Awaitable[Any]]:
    async def middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Any]],
    ) -> Any:
        if not verifier.settings.enabled:
            return await call_next(request)
        if request.url.path in verifier.settings.allow_paths:
            return await call_next(request)

        token = _extract_bearer(request)
        if not token:
            return JSONResponse(
                {"detail": "Missing bearer token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            claims = await verifier.verify(token)
        except AuthError as exc:
            return JSONResponse(
                {"detail": str(exc)},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )

        request.state.auth_claims = claims
        return await call_next(request)

    return middleware


def extract_roles(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    if isinstance(claims.get("roles"), list):
        roles.update(claims.get("roles", []))
    realm_access = claims.get("realm_access")
    if isinstance(realm_access, dict):
        realm_roles = realm_access.get("roles")
        if isinstance(realm_roles, list):
            roles.update(realm_roles)
    resource_access = claims.get("resource_access")
    if isinstance(resource_access, dict):
        for client_data in resource_access.values():
            if isinstance(client_data, dict):
                client_roles = client_data.get("roles")
                if isinstance(client_roles, list):
                    roles.update(client_roles)
    return roles


def require_role(role: str) -> Callable[[Request], Awaitable[dict[str, Any]]]:
    async def dependency(request: Request) -> dict[str, Any]:
        auth_enabled = getattr(request.app.state, "auth_enabled", False)
        claims = getattr(request.state, "auth_claims", None)
        if not auth_enabled:
            return {}
        if claims is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        roles = extract_roles(cast(dict[str, Any], claims))
        if role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return cast(dict[str, Any], claims)

    return dependency
