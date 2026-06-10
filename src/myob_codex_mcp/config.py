from __future__ import annotations

import json
import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)(?::-(.*?))?\}")


class ConfigError(RuntimeError):
    """Raised when configuration is invalid."""


def _default_home() -> Path:
    configured = os.getenv("MYOB_CODEX_MCP_HOME")
    if configured:
        return Path(configured).expanduser()
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "myob-codex-mcp"
    return Path.home() / ".myob-codex-mcp"


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            return os.getenv(name, default or "")

        return ENV_RE.sub(replace, value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_bytes()
    if path.suffix.lower() == ".json":
        return json.loads(raw.decode("utf-8"))
    if path.suffix.lower() in {".toml", ".tml"}:
        return tomllib.loads(raw.decode("utf-8"))
    raise ConfigError(f"Unsupported config file format: {path}")


def _config_candidates(explicit_path: str | None = None) -> list[Path]:
    candidates: list[Path] = []
    if explicit_path:
        candidates.append(Path(explicit_path).expanduser())
    env_path = os.getenv("MYOB_CODEX_MCP_CONFIG")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.append(Path.cwd() / ".myob-codex-mcp.toml")
    candidates.append(_default_home() / "config.toml")
    return candidates


@dataclass(frozen=True)
class AuthConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://127.0.0.1:33333/callback"
    scopes: list[str] = field(default_factory=lambda: [
        "sme-company-file",
        "sme-general-ledger",
        "sme-sales",
        "sme-purchases",
        "sme-banking",
        "sme-contacts-customer",
        "sme-contacts-supplier",
        "sme-contacts-employee",
        "offline_access",
    ])


@dataclass(frozen=True)
class PermissionConfig:
    allow_writes: bool = True
    approval_mode: str = "local_approval"
    approval_ttl_seconds: int = 900
    pending_ttl_seconds: int = 3600
    require_approval_for: list[str] = field(default_factory=lambda: [
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ])


@dataclass(frozen=True)
class AppConfig:
    home: Path
    auth: AuthConfig
    permissions: PermissionConfig
    default_business_id: str = ""
    api_base_url: str = "https://api.myob.com/accountright"
    token_path: Path = field(default_factory=lambda: _default_home() / "tokens.enc")
    pending_path: Path = field(default_factory=lambda: _default_home() / "pending-operations.json")
    audit_path: Path = field(default_factory=lambda: _default_home() / "audit.jsonl")
    signing_key_path: Path = field(default_factory=lambda: _default_home() / "approval-signing.key")
    token_key_path: Path = field(default_factory=lambda: _default_home() / "token.key")
    log_level: str = "INFO"


def _bool_from_env(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_config(explicit_path: str | None = None) -> AppConfig:
    loaded: dict[str, Any] = {}
    for candidate in _config_candidates(explicit_path):
        if candidate.exists():
            loaded = _expand_env(_read_config_file(candidate))
            break

    home = Path(loaded.get("home") or _default_home()).expanduser()
    myob = loaded.get("myob", {})
    auth = loaded.get("auth", {})
    permissions = loaded.get("permissions", {})
    audit = loaded.get("audit", {})

    client_id = os.getenv("MYOB_CLIENT_ID") or myob.get("client_id") or auth.get("client_id") or ""
    client_secret = (
        os.getenv("MYOB_CLIENT_SECRET")
        or myob.get("client_secret")
        or auth.get("client_secret")
        or ""
    )
    default_business_id = (
        os.getenv("MYOB_DEFAULT_BUSINESS_ID")
        or myob.get("default_business_id")
        or myob.get("default_company_file_id")
        or ""
    )

    token_path = Path(auth.get("token_path") or loaded.get("token_path") or home / "tokens.enc")
    pending_path = Path(permissions.get("pending_path") or home / "pending-operations.json")
    audit_path = Path(audit.get("path") or home / "audit.jsonl")
    signing_key_path = Path(permissions.get("signing_key_path") or home / "approval-signing.key")
    token_key_path = Path(auth.get("token_key_path") or home / "token.key")

    return AppConfig(
        home=home,
        auth=AuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=(
                os.getenv("MYOB_REDIRECT_URI")
                or myob.get("redirect_uri")
                or auth.get("redirect_uri")
                or AuthConfig.redirect_uri
            ),
            scopes=list(auth.get("scopes") or myob.get("scopes") or AuthConfig().scopes),
        ),
        permissions=PermissionConfig(
            allow_writes=_bool_from_env(
                os.getenv("MYOB_ALLOW_WRITES"),
                bool(permissions.get("allow_writes", True)),
            ),
            approval_mode=os.getenv("MYOB_APPROVAL_MODE")
            or permissions.get("approval_mode")
            or "local_approval",
            approval_ttl_seconds=int(permissions.get("approval_ttl_seconds", 900)),
            pending_ttl_seconds=int(permissions.get("pending_ttl_seconds", 3600)),
            require_approval_for=list(
                permissions.get("require_approval_for")
                or PermissionConfig().require_approval_for
            ),
        ),
        default_business_id=default_business_id,
        api_base_url=myob.get("api_base_url") or "https://api.myob.com/accountright",
        token_path=token_path.expanduser(),
        pending_path=pending_path.expanduser(),
        audit_path=audit_path.expanduser(),
        signing_key_path=signing_key_path.expanduser(),
        token_key_path=token_key_path.expanduser(),
        log_level=str(loaded.get("log_level") or os.getenv("MYOB_CODEX_MCP_LOG_LEVEL") or "INFO"),
    )
