from __future__ import annotations

import webbrowser
from urllib.parse import parse_qs, urlparse

from mcp.server.fastmcp import Context, FastMCP

from myob_codex_mcp.auth.callback_server import run_oauth_callback_server
from myob_codex_mcp.tools.common import app_context


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def myob_auth_status(ctx: Context) -> dict:
        """Show MYOB OAuth authentication, token, and selected business status."""
        app = app_context(ctx)
        status = app.auth.status()
        status["default_business_id"] = app.config.default_business_id
        status["writes_enabled"] = app.config.permissions.allow_writes
        status["approval_mode"] = app.config.permissions.approval_mode
        return status

    @mcp.tool()
    async def myob_oauth_authorize_business(
        open_browser: bool = True,
        manual: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Start MYOB OAuth consent for one business/company file. Repeat once per business."""
        app = app_context(ctx)
        request = app.auth.build_authorization_request(manual=manual)
        if open_browser:
            webbrowser.open(request.url)
        if manual:
            return {
                "authorization_url": request.url,
                "state": request.state,
                "redirect_uri": request.redirect_uri,
                "message": (
                    "Open the URL, approve one MYOB business, then call "
                    "myob_oauth_exchange_redirect_url with the full redirected URL or "
                    "myob_oauth_exchange_code with the code and businessId."
                ),
            }
        parsed = urlparse(app.config.auth.redirect_uri)
        port = parsed.port or 33333
        result = await run_oauth_callback_server(app.auth, port=port)
        return {
            "success": result.success,
            "business_id": result.business_id,
            "error": result.error,
        }

    @mcp.tool()
    async def myob_oauth_authorize(open_browser: bool = True, manual: bool = False, ctx: Context = None) -> dict:
        """Alias for myob_oauth_authorize_business."""
        return await myob_oauth_authorize_business(open_browser=open_browser, manual=manual, ctx=ctx)

    @mcp.tool()
    async def myob_oauth_exchange_code(
        code: str,
        business_id: str,
        state: str | None = None,
        ctx: Context = None,
    ) -> dict:
        """Manually exchange an OAuth code for one MYOB business and store its encrypted tokens."""
        app = app_context(ctx)
        if state and app.auth.has_pending_authorization():
            app.auth.validate_state(state)
        tokens = await app.auth.exchange_code(code, business_id=business_id)
        return {
            "authenticated": True,
            "business_id": tokens.get("business_id"),
            "scope": tokens.get("scope", ""),
            "expires_at": tokens.get("expires_at"),
            "authorized_business_count": len(app.auth.list_authorized_businesses()),
        }

    @mcp.tool()
    async def myob_oauth_exchange_redirect_url(redirect_url: str, ctx: Context = None) -> dict:
        """Exchange the full MYOB OAuth redirected URL containing code, businessId, and state."""
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        business_id = params.get("businessId", params.get("business_id", [None]))[0]
        state = params.get("state", [None])[0]
        if not code or not business_id:
            raise ValueError("redirect_url must contain code and businessId query parameters")
        return await myob_oauth_exchange_code(code=code, business_id=business_id, state=state, ctx=ctx)

    @mcp.tool()
    async def myob_oauth_refresh(business_id: str | None = None, ctx: Context = None) -> dict:
        """Refresh a stored MYOB OAuth access token for one business or the default business."""
        app = app_context(ctx)
        tokens = await app.auth.refresh_access_token(business_id)
        return {
            "authenticated": True,
            "business_id": tokens.get("business_id"),
            "scope": tokens.get("scope", ""),
            "expires_at": tokens.get("expires_at"),
        }

    @mcp.tool()
    async def myob_oauth_logout(ctx: Context) -> dict:
        """Clear all stored MYOB OAuth tokens from this machine."""
        app = app_context(ctx)
        return app.auth.logout()

    @mcp.tool()
    async def myob_business_list_authorized(ctx: Context) -> dict:
        """List MYOB businesses/company files already authorised on this machine."""
        app = app_context(ctx)
        return {
            "default_business_id": app.auth.business_id(),
            "businesses": app.auth.list_authorized_businesses(),
        }

    @mcp.tool()
    async def myob_business_set_default(business_id: str, ctx: Context) -> dict:
        """Set the default MYOB business/company file for future tool calls."""
        app = app_context(ctx)
        return app.auth.set_default_business(business_id)

    @mcp.tool()
    async def myob_business_remove_authorization(business_id: str, ctx: Context) -> dict:
        """Remove locally stored OAuth tokens for one MYOB business/company file."""
        app = app_context(ctx)
        return app.auth.remove_business(business_id)
