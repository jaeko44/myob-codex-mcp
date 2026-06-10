from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx

from myob_codex_mcp.config import AuthConfig

AUTH_URL = "https://secure.myob.com/oauth2/account/authorize"
TOKEN_URL = "https://secure.myob.com/oauth2/v1/authorize"


class TokenStore(Protocol):
    def load(self) -> dict[str, Any] | None: ...
    def save(self, tokens: dict[str, Any]) -> None: ...
    def clear(self) -> None: ...


class AuthError(RuntimeError):
    """Raised when OAuth authentication fails."""


@dataclass(frozen=True)
class AuthorizationRequest:
    url: str
    state: str
    redirect_uri: str
    scopes: list[str]


class MyobOAuth:
    def __init__(
        self,
        config: AuthConfig,
        token_store: TokenStore,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.token_store = token_store
        self._tokens = token_store.load()
        self._oauth_state: str | None = None
        self._http_client = http_client

    @property
    def tokens(self) -> dict[str, Any] | None:
        return self._tokens

    def build_authorization_request(self, *, manual: bool = False) -> AuthorizationRequest:
        if not self.config.client_id:
            raise AuthError("MYOB client_id is not configured")
        self._oauth_state = secrets.token_urlsafe(32)
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "prompt": "consent",
            "state": self._oauth_state,
        }
        if manual:
            params["manual"] = "true"
        return AuthorizationRequest(
            url=f"{AUTH_URL}?{urlencode(params)}",
            state=self._oauth_state,
            redirect_uri=self.config.redirect_uri,
            scopes=list(self.config.scopes),
        )

    def validate_state(self, state: str | None) -> None:
        expected = self._oauth_state
        self._oauth_state = None
        if not expected or state != expected:
            raise AuthError("OAuth state mismatch; authorization was rejected")

    async def _post_token(self, payload: dict[str, str]) -> dict[str, Any]:
        if not self.config.client_id or not self.config.client_secret:
            raise AuthError("MYOB client_id/client_secret are not configured")
        if self._http_client:
            resp = await self._http_client.post(TOKEN_URL, data=payload, timeout=30.0)
        else:
            async with httpx.AsyncClient() as client:
                resp = await client.post(TOKEN_URL, data=payload, timeout=30.0)
        if resp.status_code != 200:
            raise AuthError(f"MYOB token request failed ({resp.status_code}): {resp.text}")
        return resp.json()

    async def exchange_code(self, code: str, *, business_id: str | None = None) -> dict[str, Any]:
        data = await self._post_token({
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "redirect_uri": self.config.redirect_uri,
            "grant_type": "authorization_code",
            "code": code,
        })
        tokens = self._normalize_tokens(data, business_id=business_id)
        self._tokens = tokens
        self.token_store.save(tokens)
        return tokens

    async def refresh_access_token(self) -> dict[str, Any]:
        if not self._tokens or not self._tokens.get("refresh_token"):
            raise AuthError("No refresh token is available. Run myob_oauth_authorize first.")
        data = await self._post_token({
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": str(self._tokens["refresh_token"]),
        })
        tokens = self._normalize_tokens(
            data,
            refresh_token_fallback=str(self._tokens["refresh_token"]),
            business_id=self._tokens.get("business_id"),
        )
        self._tokens = tokens
        self.token_store.save(tokens)
        return tokens

    def _normalize_tokens(
        self,
        data: dict[str, Any],
        *,
        business_id: str | None = None,
        refresh_token_fallback: str | None = None,
    ) -> dict[str, Any]:
        if "access_token" not in data:
            raise AuthError("MYOB token response did not include access_token")
        expires_in = int(data.get("expires_in", 1200))
        tokens = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token") or refresh_token_fallback,
            "expires_at": time.time() + expires_in,
            "scope": data.get("scope", ""),
            "token_type": data.get("token_type", "Bearer"),
        }
        if business_id:
            tokens["business_id"] = business_id
        return tokens

    async def get_valid_access_token(self) -> str:
        if not self._tokens:
            raise AuthError("Not authenticated. Run myob_oauth_authorize first.")
        if time.time() > float(self._tokens.get("expires_at", 0)) - 60:
            await self.refresh_access_token()
        return str(self._tokens["access_token"])

    def business_id(self) -> str | None:
        if not self._tokens:
            return None
        value = self._tokens.get("business_id")
        return str(value) if value else None

    def status(self) -> dict[str, Any]:
        if not self._tokens:
            return {
                "authenticated": False,
                "message": "Not authenticated. Run myob_oauth_authorize first.",
            }
        expires_in = max(0, int(float(self._tokens.get("expires_at", 0)) - time.time()))
        return {
            "authenticated": True,
            "expires_in_seconds": expires_in,
            "has_refresh_token": bool(self._tokens.get("refresh_token")),
            "business_id": self._tokens.get("business_id"),
            "scope": self._tokens.get("scope", ""),
        }

    def logout(self) -> dict[str, Any]:
        self._tokens = None
        self.token_store.clear()
        return {"authenticated": False, "message": "Stored MYOB OAuth tokens were cleared."}
