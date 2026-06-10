from __future__ import annotations

import base64
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


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

    def load(self) -> dict[str, Any] | None:
        if not self.token_path.exists():
            return None
        try:
            decrypted = self._fernet().decrypt(self.token_path.read_bytes())
            return json.loads(decrypted.decode("utf-8"))
        except (InvalidToken, OSError, json.JSONDecodeError) as exc:
            raise TokenStoreError("Failed to decrypt or parse token store") from exc

    def save(self, tokens: dict[str, Any]) -> None:
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(tokens, sort_keys=True).encode("utf-8")
        self.token_path.write_bytes(self._fernet().encrypt(payload))
        with suppress(OSError):
            os.chmod(self.token_path, 0o600)

    def clear(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()


class MemoryTokenStore:
    """In-memory token store for tests."""

    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self.tokens = initial

    def load(self) -> dict[str, Any] | None:
        return self.tokens

    def save(self, tokens: dict[str, Any]) -> None:
        self.tokens = dict(tokens)

    def clear(self) -> None:
        self.tokens = None
