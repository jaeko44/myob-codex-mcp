from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import httpx

from myob_codex_mcp.auth.oauth import MyobOAuth
from myob_codex_mcp.config import AppConfig
from myob_codex_mcp.myob.errors import MyobApiError, UnsafeRetryError

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class MyobClient:
    def __init__(
        self,
        config: AppConfig,
        auth: MyobOAuth,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.auth = auth
        self._client = http_client
        self._owns_client = http_client is None

    def _business_id(self, business_id: str | None, *, required: bool) -> str | None:
        selected = business_id or self.auth.business_id() or self.config.default_business_id
        if required and not selected:
            raise ValueError(
                "No MYOB business/company file ID is selected. Re-run OAuth to capture businessId "
                "or set MYOB_DEFAULT_BUSINESS_ID."
            )
        return selected

    def _url(self, path: str, business_id: str | None, *, require_business_id: bool) -> str:
        selected = self._business_id(business_id, required=require_business_id)
        clean_path = path if path.startswith("/") else f"/{path}"
        if selected:
            return f"{self.config.api_base_url.rstrip('/')}/{selected}{clean_path}"
        return self.config.api_base_url.rstrip("/") + clean_path

    async def _headers(
        self,
        extra: Mapping[str, str] | None = None,
        *,
        business_id: str | None = None,
    ) -> dict[str, str]:
        token = await self.auth.get_valid_access_token(business_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "x-myobapi-key": self.config.auth.client_id,
            "x-myobapi-version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if extra:
            headers.update(extra)
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def request(
        self,
        method: str,
        path: str,
        *,
        business_id: str | None = None,
        require_business_id: bool = True,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        method = method.upper()
        if method not in SAFE_METHODS | MUTATING_METHODS:
            raise ValueError(f"Unsupported HTTP method for MYOB request: {method}")

        request_params = dict(params or {})
        if method in {"POST", "PUT", "PATCH"}:
            request_params.setdefault("returnBody", "true")

        resolved_business_id = self._business_id(business_id, required=require_business_id)
        request_headers = await self._headers(headers, business_id=resolved_business_id)
        if idempotency_key:
            request_headers["Idempotency-Key"] = idempotency_key

        max_retries = 3
        url = self._url(path, resolved_business_id, require_business_id=require_business_id)

        for attempt in range(max_retries + 1):
            try:
                response = await self._get_client().request(
                    method,
                    url,
                    headers=request_headers,
                    params=request_params,
                    json=json_body,
                )
            except httpx.TimeoutException as exc:
                if method not in SAFE_METHODS and not idempotency_key:
                    raise UnsafeRetryError(
                        0,
                        "Mutating request timed out and was not retried because no idempotency key was provided",
                    ) from exc
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise MyobApiError(0, f"Request timed out: {exc}") from exc
            except httpx.RequestError as exc:
                if attempt < max_retries and (method in SAFE_METHODS or idempotency_key):
                    await asyncio.sleep(0.5 * (2**attempt))
                    continue
                raise MyobApiError(0, f"Request failed: {exc}") from exc

            if response.status_code == 401 and attempt < max_retries:
                await self.auth.refresh_access_token(resolved_business_id)
                request_headers = await self._headers(headers, business_id=resolved_business_id)
                if idempotency_key:
                    request_headers["Idempotency-Key"] = idempotency_key
                continue

            if response.status_code == 429 and attempt < max_retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = min(float(retry_after), 60.0) if retry_after else 0.5 * (2**attempt)
                except ValueError:
                    wait = 0.5 * (2**attempt)
                logger.warning("MYOB rate limit hit; retrying in %.1fs", wait)
                await asyncio.sleep(wait)
                continue

            if response.status_code >= 500 and attempt < max_retries and method in SAFE_METHODS:
                await asyncio.sleep(0.5 * (2**attempt))
                continue

            if response.status_code >= 400:
                raise MyobApiError(response.status_code, f"{method} {path} failed", response.text)

            if response.status_code == 204 or not response.content:
                return None
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type.lower():
                return response.json()
            return response.text

        raise MyobApiError(0, "MYOB request exceeded retry policy")

    async def paged(
        self,
        path: str,
        *,
        business_id: str | None = None,
        params: dict[str, Any] | None = None,
        top: int = 400,
        max_items: int = 1000,
    ) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        skip = 0
        page_size = min(max(top, 1), 400)
        while len(all_items) < max_items:
            page_params = dict(params or {})
            page_params["$top"] = str(page_size)
            page_params["$skip"] = str(skip)
            result = await self.request("GET", path, business_id=business_id, params=page_params)
            if isinstance(result, list):
                items = result
            elif isinstance(result, dict) and isinstance(result.get("Items"), list):
                items = result["Items"]
            elif result:
                items = [result]
            else:
                items = []
            all_items.extend(items)
            if len(items) < page_size:
                break
            skip += page_size
        return all_items[:max_items]

    async def close(self) -> None:
        if self._owns_client and self._client and not self._client.is_closed:
            await self._client.aclose()
