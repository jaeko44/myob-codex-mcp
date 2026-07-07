from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from myob_codex_mcp.auth.oauth import MyobOAuth
from myob_codex_mcp.auth.token_store import MemoryTokenStore
from myob_codex_mcp.config import AuthConfig


def test_authorization_url_uses_consent_state_and_scopes() -> None:
    auth = MyobOAuth(
        AuthConfig(
            client_id="client-id",
            client_secret="secret",
            redirect_uri="http://127.0.0.1:33333/callback",
            scopes=["sme-company-file", "sme-sales", "offline_access"],
        ),
        MemoryTokenStore(),
    )

    request = auth.build_authorization_request()
    parsed = urlparse(request.url)
    params = parse_qs(parsed.query)

    assert parsed.netloc == "secure.myob.com"
    assert params["client_id"] == ["client-id"]
    assert params["response_type"] == ["code"]
    assert params["prompt"] == ["consent"]
    assert params["scope"] == ["sme-company-file sme-sales offline_access"]
    assert params["state"] == [request.state]


def test_state_validation_rejects_mismatch() -> None:
    auth = MyobOAuth(AuthConfig(client_id="client-id", client_secret="secret"), MemoryTokenStore())
    auth.build_authorization_request()

    try:
        auth.validate_state("wrong")
    except Exception as exc:
        assert "state mismatch" in str(exc)
    else:
        raise AssertionError("Expected state mismatch")


async def test_oauth_selects_tokens_by_business() -> None:
    store = MemoryTokenStore()
    store.save_business_tokens(
        "business-a",
        {
            "access_token": "access-a",
            "refresh_token": "refresh-a",
            "expires_at": 9999999999,
            "business_id": "business-a",
        },
    )
    store.save_business_tokens(
        "business-b",
        {
            "access_token": "access-b",
            "refresh_token": "refresh-b",
            "expires_at": 9999999999,
            "business_id": "business-b",
        },
    )
    auth = MyobOAuth(AuthConfig(client_id="client-id", client_secret="secret"), store)

    assert await auth.get_valid_access_token("business-a") == "access-a"
    assert await auth.get_valid_access_token("business-b") == "access-b"

    auth.set_default_business("business-a")
    assert auth.business_id() == "business-a"
    assert auth.list_authorized_businesses()[0]["business_id"] == "business-a"
