from __future__ import annotations

import base64
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

TOKEN_REGISTRY_VERSION = 2


class TokenStoreError(RuntimeError):
    """Raised when encrypted token storage fails."""


class EncryptedTokenStore:
    """Encrypted JSON token store.

    The preferred key source is Windows Credential Manager / OS keyring. For
    test and headless environments, MYOB_CODEX_MCP_TOKEN_KEY may provide a
    Fernet key. If keyring is unavailable, a local key file is created; the
    token payload is still encrypted at rest.
    """

    def __init__(
        self,
        token_path: Path,
        key_path: Path,
        *,
        service_name: str = "myob-codex-mcp",
        use_keyring: bool = True,
    ) -> None:
        self.token_path = token_path
        self.key_path = key_path
        self.service_name = service_name
        self.use_keyring = use_keyring

    def _load_key_from_keyring(self) -> bytes | None:
        if not self.use_keyring:
            return None
        try:
            import keyring

            value = keyring.get_password(self.service_name, "token-encryption-key")
            return value.encode("ascii") if value else None
        except Exception:
            return None

    def _save_key_to_keyring(self, key: bytes) -> bool:
        if not self.use_keyring:
            return False
        try:
            import keyring

            keyring.set_password(self.service_name, "token-encryption-key", key.decode("ascii"))
            return True
        except Exception:
            return False

    def _load_key_from_file(self) -> bytes | None:
        if not self.key_path.exists():
            return None
        raw = self.key_path.read_bytes().strip()
        return raw or None

    def _save_key_to_file(self, key: bytes) -> None:
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        self.key_path.write_bytes(key)
        with suppress(OSError):
            os.chmod(self.key_path, 0o600)

    def _get_key(self) -> bytes:
        env_key = os.getenv("MYOB_CODEX_MCP_TOKEN_KEY")
        if env_key:
            return env_key.encode("ascii")

        key = self._load_key_from_keyring()
        if key:
            return key

        key = self._load_key_from_file()
        if key:
            return key

        key = Fernet.generate_key()
        if not self._save_key_to_keyring(key):
            self._save_key_to_file(key)
        return key

    def _fernet(self) -> Fernet:
        key = self._get_key()
        try:
            base64.urlsafe_b64decode(key)
            return Fernet(key)
        except Exception as exc:
            raise TokenStoreError("Invalid token encryption key") from exc

    def _decrypt_payload(self) -> dict[str, Any] | None:
        if not self.token_path.exists():
            return None
        try:
            decrypted = self._fernet().decrypt(self.token_path.read_bytes())
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, OSError, json.JSONDecodeError) as exc:
            raise TokenStoreError("Failed to decrypt or parse token store") from exc

    def _encrypt_payload(self, payload: dict[str, Any]) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.token_path.write_bytes(self._fernet().encrypt(raw))
        with suppress(OSError):
            os.chmod(self.token_path, 0o600)

    def _registry(self) -> dict[str, Any]:
        payload = self._decrypt_payload()
        if not payload:
            return {
                "schema_version": TOKEN_REGISTRY_VERSION,
                "default_business_id": None,
                "businesses": {},
            }
        if "businesses" in payload:
            payload.setdefault("schema_version", TOKEN_REGISTRY_VERSION)
            payload.setdefault("default_business_id", None)
            payload.setdefault("businesses", {})
            return payload

        # Backwards compatibility for the original single-token store.
        business_id = payload.get("business_id")
        if not business_id:
            return {
                "schema_version": TOKEN_REGISTRY_VERSION,
                "default_business_id": None,
                "businesses": {},
                "legacy_unscoped_tokens": payload,
            }
        return {
            "schema_version": TOKEN_REGISTRY_VERSION,
            "default_business_id": business_id,
            "businesses": {business_id: payload},
        }

    def load(self) -> dict[str, Any] | None:
        registry = self._registry()
        default_business_id = registry.get("default_business_id")
        businesses = registry.get("businesses", {})
        if default_business_id and default_business_id in businesses:
            return businesses[default_business_id]
        if len(businesses) == 1:
            return next(iter(businesses.values()))
        return registry.get("legacy_unscoped_tokens")

    def save(self, tokens: dict[str, Any]) -> None:
        business_id = tokens.get("business_id")
        if not business_id:
            self._encrypt_payload(tokens)
            return
        self.save_business_tokens(str(business_id), tokens, make_default=True)

    def clear(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()

    def list_businesses(self) -> list[dict[str, Any]]:
        registry = self._registry()
        default_business_id = registry.get("default_business_id")
        businesses = registry.get("businesses", {})
        result: list[dict[str, Any]] = []
        for business_id, tokens in sorted(businesses.items()):
            result.append({
                "business_id": business_id,
                "is_default": business_id == default_business_id,
                "expires_at": tokens.get("expires_at"),
                "scope": tokens.get("scope", ""),
                "has_refresh_token": bool(tokens.get("refresh_token")),
                "display_name": tokens.get("display_name"),
            })
        return result

    def load_business_tokens(self, business_id: str | None = None) -> dict[str, Any] | None:
        registry = self._registry()
        selected = business_id or registry.get("default_business_id")
        businesses = registry.get("businesses", {})
        if selected and selected in businesses:
            return businesses[selected]
        if business_id is None and len(businesses) == 1:
            return next(iter(businesses.values()))
        return None

    def save_business_tokens(
        self,
        business_id: str,
        tokens: dict[str, Any],
        *,
        make_default: bool = True,
    ) -> None:
        if not business_id:
            raise TokenStoreError("business_id is required for multi-business token storage")
        registry = self._registry()
        businesses = dict(registry.get("businesses", {}))
        clean_tokens = dict(tokens)
        clean_tokens["business_id"] = business_id
        businesses[business_id] = clean_tokens
        registry["schema_version"] = TOKEN_REGISTRY_VERSION
        registry["businesses"] = businesses
        if make_default or not registry.get("default_business_id"):
            registry["default_business_id"] = business_id
        self._encrypt_payload(registry)

    def set_default_business(self, business_id: str) -> None:
        registry = self._registry()
        businesses = registry.get("businesses", {})
        if business_id not in businesses:
            raise KeyError(f"Business is not authorised: {business_id}")
        registry["default_business_id"] = business_id
        self._encrypt_payload(registry)

    def remove_business(self, business_id: str) -> bool:
        registry = self._registry()
        businesses = dict(registry.get("businesses", {}))
        existed = business_id in businesses
        businesses.pop(business_id, None)
        registry["businesses"] = businesses
        if registry.get("default_business_id") == business_id:
            registry["default_business_id"] = next(iter(sorted(businesses)), None)
        self._encrypt_payload(registry)
        return existed


class MemoryTokenStore:
    """In-memory token store for tests."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self.payload: dict[str, Any] | None = None
        if initial:
            business_id = initial.get("business_id")
            if business_id:
                self.payload = {
                    "schema_version": TOKEN_REGISTRY_VERSION,
                    "default_business_id": business_id,
                    "businesses": {business_id: dict(initial)},
                }
            else:
                self.payload = dict(initial)

    def load(self) -> dict[str, Any] | None:
        if not self.payload:
            return None
        if "businesses" not in self.payload:
            return self.payload
        default_business_id = self.payload.get("default_business_id")
        businesses = self.payload.get("businesses", {})
        if default_business_id and default_business_id in businesses:
            return businesses[default_business_id]
        if len(businesses) == 1:
            return next(iter(businesses.values()))
        return None

    def save(self, tokens: dict[str, Any]) -> None:
        business_id = tokens.get("business_id")
        if business_id:
            self.save_business_tokens(str(business_id), tokens, make_default=True)
            return
        self.payload = dict(tokens)

    def clear(self) -> None:
        self.payload = None

    def list_businesses(self) -> list[dict[str, Any]]:
        if not self.payload or "businesses" not in self.payload:
            return []
        default_business_id = self.payload.get("default_business_id")
        return [
            {
                "business_id": business_id,
                "is_default": business_id == default_business_id,
                "expires_at": tokens.get("expires_at"),
                "scope": tokens.get("scope", ""),
                "has_refresh_token": bool(tokens.get("refresh_token")),
                "display_name": tokens.get("display_name"),
            }
            for business_id, tokens in sorted(self.payload.get("businesses", {}).items())
        ]

    def load_business_tokens(self, business_id: str | None = None) -> dict[str, Any] | None:
        if not self.payload:
            return None
        if "businesses" not in self.payload:
            return self.payload
        selected = business_id or self.payload.get("default_business_id")
        businesses = self.payload.get("businesses", {})
        if selected and selected in businesses:
            return businesses[selected]
        if business_id is None and len(businesses) == 1:
            return next(iter(businesses.values()))
        return None

    def save_business_tokens(
        self,
        business_id: str,
        tokens: dict[str, Any],
        *,
        make_default: bool = True,
    ) -> None:
        if not self.payload or "businesses" not in self.payload:
            self.payload = {
                "schema_version": TOKEN_REGISTRY_VERSION,
                "default_business_id": None,
                "businesses": {},
            }
        clean_tokens = dict(tokens)
        clean_tokens["business_id"] = business_id
        self.payload["businesses"][business_id] = clean_tokens
        if make_default or not self.payload.get("default_business_id"):
            self.payload["default_business_id"] = business_id

    def set_default_business(self, business_id: str) -> None:
        if not self.payload or business_id not in self.payload.get("businesses", {}):
            raise KeyError(f"Business is not authorised: {business_id}")
        self.payload["default_business_id"] = business_id

    def remove_business(self, business_id: str) -> bool:
        if not self.payload or "businesses" not in self.payload:
            return False
        businesses = self.payload["businesses"]
        existed = business_id in businesses
        businesses.pop(business_id, None)
        if self.payload.get("default_business_id") == business_id:
            self.payload["default_business_id"] = next(iter(sorted(businesses)), None)
        return existed
