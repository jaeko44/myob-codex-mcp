from __future__ import annotations

import webbrowser
from urllib.parse import urlparse

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
    async def myob_oauth_authorize(open_browser: bool = True, manual: bool = False, ctx: Context = None) -> dict:
        """Start MYOB OAuth consent. Use manual=true if localhost callback is not available."""
        app = app_context(ctx)
        request = app.auth.build_authorization_request(manual=manual)
        if open_browser:
            webbrowser.open(request.url)
        if manual:
            return {
                "authorization_url": request.url,
                "state": request.state,
                "redirect_uri": request.redirect_uri,
                "message": "Open the URL, approve MYOB access, then call myob_oauth_exchange_code with the code and businessId.",
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
    async def myob_oauth_exchange_code(code: str, business_id: str | None = None, ctx: Context = None) -> dict:
        """Manually exchange an OAuth code for MYOB tokens and save businessId context."""
        app = app_context(ctx)
        tokens = await app.auth.exchange_code(code, business_id=business_id)
        return {
            "authenticated": True,
            "business_id": tokens.get("business_id"),
            "scope": tokens.get("scope", ""),
            "expires_at": tokens.get("expires_at"),
        }

    @mcp.tool()
    async def myob_oauth_refresh(ctx: Context) -> dict:
        """Refresh MYOB OAuth access token using the stored refresh token."""
        app = app_context(ctx)
        tokens = await app.auth.refresh_access_token()
        return {
            "authenticated": True,
            "business_id": tokens.get("business_id"),
            "scope": tokens.get("scope", ""),
            "expires_at": tokens.get("expires_at"),
        }

    @mcp.tool()
    async def myob_oauth_logout(ctx: Context) -> dict:
        """Clear stored MYOB OAuth tokens from this machine."""
        app = app_context(ctx)
        return app.auth.logout()
