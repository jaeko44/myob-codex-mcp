from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from myob_codex_mcp.auth.oauth import AuthError, MyobOAuth


@dataclass(frozen=True)
class CallbackResult:
    success: bool
    business_id: str | None = None
    error: str | None = None


async def run_oauth_callback_server(auth: MyobOAuth, *, host: str = "127.0.0.1", port: int = 33333) -> CallbackResult:
    result_success = False
    result_business_id: str | None = None
    result_error: str | None = None
    event = asyncio.Event()

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        nonlocal result_business_id, result_error, result_success
        body = "<html><body><h1>MYOB authorization failed</h1></body></html>"
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=10)
            parts = request_line.decode("utf-8", errors="replace").split(" ")
            if len(parts) < 2:
                result_error = "Invalid OAuth callback"
                return
            url = urlparse(parts[1])
            params = parse_qs(url.query)
            if "error" in params:
                error = params.get("error_description", params["error"])[0]
                result_error = error
                body = f"<html><body><h1>MYOB authorization failed</h1><p>{error}</p></body></html>"
                return
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            business_id = params.get("businessId", [None])[0]
            if not code:
                result_error = "No authorization code was returned"
                return
            auth.validate_state(state)
            await auth.exchange_code(code, business_id=business_id)
            result_success = True
            result_business_id = business_id
            body = (
                "<html><body><h1>MYOB authorization successful</h1>"
                "<p>You can close this tab and return to Codex.</p></body></html>"
            )
        except Exception as exc:
            result_error = str(exc)
            body = f"<html><body><h1>MYOB authorization failed</h1><p>{exc}</p></body></html>"
        finally:
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                "Connection: close\r\n\r\n"
                f"{body}"
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            event.set()

    server = await asyncio.start_server(handle, host, port)
    try:
        await asyncio.wait_for(event.wait(), timeout=180)
    except TimeoutError as exc:
        raise AuthError("OAuth callback timed out after 180 seconds") from exc
    finally:
        server.close()
        await server.wait_closed()

    if result_error:
        return CallbackResult(success=False, error=result_error)
    return CallbackResult(success=result_success, business_id=result_business_id)
