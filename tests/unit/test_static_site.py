from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_callback_site_is_static_and_copy_ready() -> None:
    html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    assert "myob_oauth_exchange_redirect_url" in html
    assert "connect-src 'none'" in html
    assert "localStorage" not in html
    assert "fetch(" not in html
    assert "XMLHttpRequest" not in html
    assert "client_secret" not in html.lower()
    assert "data-copy-target=\"codexInstruction\"" in html
    assert "data-copy-target=\"redirectUrl\"" in html


def test_callback_fallback_preserves_query_string() -> None:
    html = (ROOT / "site" / "404.html").read_text(encoding="utf-8")

    assert "window.location.search" in html
    assert "window.location.hash" in html
    assert "window.location.replace" in html


def test_static_site_custom_domain_and_robots() -> None:
    cname = (ROOT / "site" / "CNAME").read_text(encoding="utf-8").strip()
    robots = (ROOT / "site" / "robots.txt").read_text(encoding="utf-8")

    assert cname == "app.professionalaccounting.com.au"
    assert "Disallow: /" in robots
