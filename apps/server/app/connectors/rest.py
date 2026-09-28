import base64
import ipaddress
import json
import socket
from time import monotonic
from typing import Any
from urllib.parse import urlparse

import httpx

from app.connectors.base import BaseConnector
from app.core.config import get_settings

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_SAMPLE_BYTES = 1024 * 1024
MAX_ROWS = 5000
FORBIDDEN_HEADERS = {"host", "content-length", "transfer-encoding", "connection", "proxy-authorization"}


def validate_connector_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Connector URL must be an HTTP(S) URL without credentials")
    if get_settings().app_env == "development" and parsed.hostname in {"localhost", "127.0.0.1", "server"}:
        return
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Connector host cannot be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Connector URL must resolve to a public address")


def nested_value(payload: Any, path: str) -> Any:
    value = payload
    for segment in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


class RestApiConnector(BaseConnector):
    def __init__(self, url: str, config: dict, auth_type: str = "none", transport: httpx.AsyncBaseTransport | None = None) -> None:
        validate_connector_url(url)
        self.url = url
        self.config = config
        self.auth_type = auth_type
        self.transport = transport
        self.last_response_meta: dict[str, Any] = {}
        self.method = str(config.get("method", "GET")).upper()
        if self.method not in {"GET", "POST"}:
            raise ValueError("REST connector method must be GET or POST")
        self.timeout = float(config.get("timeout_seconds", 10))
        if not 1 <= self.timeout <= 30:
            raise ValueError("REST timeout must be between 1 and 30 seconds")
        if not isinstance(config.get("query_params", {}), dict) or not isinstance(config.get("request_body", {}), dict):
            raise ValueError("Query params and request body must be objects")
        if config.get("sync_mode", "FULL") not in {"FULL", "INCREMENTAL"}:
            raise ValueError("Unsupported sync mode")
        if config.get("sync_mode") == "INCREMENTAL" and not config.get("incremental_field"):
            raise ValueError("Incremental sync requires incremental_field")
        pagination = config.get("pagination", {})
        if not isinstance(pagination, dict) or pagination.get("type", "NONE") not in {"NONE", "PAGE_NUMBER", "OFFSET_LIMIT", "CURSOR"}:
            raise ValueError("Unsupported pagination configuration")
        self.pagination = pagination
        if not 1 <= int(pagination.get("page_size", 100)) <= 500 or not 1 <= int(pagination.get("max_pages", 20)) <= 50:
            raise ValueError("Pagination size or page limit is out of range")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_type == "bearer" and self.config.get("token"):
            headers["Authorization"] = f"Bearer {self.config['token']}"
        elif self.auth_type in {"header", "api_key_header"} and self.config.get("header_name") and self.config.get("header_value"):
            headers[str(self.config["header_name"])] = str(self.config["header_value"])
        elif self.auth_type == "basic" and self.config.get("username") is not None and self.config.get("password") is not None:
            encoded = base64.b64encode(f"{self.config['username']}:{self.config['password']}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif self.auth_type == "custom_headers":
            custom = self.config.get("headers", {})
            if not isinstance(custom, dict):
                raise ValueError("Custom headers must be an object")
            headers.update({str(key): str(value) for key, value in custom.items()})
        for name, value in headers.items():
            if name.lower() in FORBIDDEN_HEADERS or any(character in name + value for character in "\r\n"):
                raise ValueError("Unsupported connector header")
        return headers

    def _request_parts(self, page: int, cursor: str | None) -> tuple[dict, dict]:
        params = dict(self.config.get("query_params", {}))
        body = dict(self.config.get("request_body", {}))
        if self.config.get("sync_mode", "FULL") == "INCREMENTAL" and self.config.get("last_sync_value"):
            key = str(self.config.get("incremental_param") or self.config.get("incremental_field") or "updated_at")
            destination = body if self.config.get("incremental_location") == "body" else params
            destination[key] = self.config["last_sync_value"]
        kind = self.pagination.get("type", "NONE")
        if kind != "NONE":
            destination = body if self.pagination.get("location") == "body" else params
            page_size = int(self.pagination.get("page_size", 100))
            destination[str(self.pagination.get("size_param", "pageSize"))] = page_size
            if kind == "PAGE_NUMBER":
                destination[str(self.pagination.get("page_param", "page"))] = page
            elif kind == "OFFSET_LIMIT":
                destination[str(self.pagination.get("offset_param", "offset"))] = (page - 1) * page_size
            elif cursor:
                destination[str(self.pagination.get("cursor_param", "cursor"))] = cursor
        return params, body

    async def _request_page(self, client: httpx.AsyncClient, page: int, cursor: str | None, max_bytes: int) -> tuple[list[dict], Any]:
        validate_connector_url(self.url)
        params, body = self._request_parts(page, cursor)
        started = monotonic()
        async with client.stream(self.method, self.url, params=params, json=body if self.method == "POST" else None, headers=self._headers()) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                raise ValueError("Connector redirects are not supported")
            response.raise_for_status()
            self.last_response_meta = {"status_code": response.status_code, "content_type": response.headers.get("content-type", ""),
                "latency_ms": round((monotonic() - started) * 1000)}
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > max_bytes:
                    raise ValueError("Connector response exceeds configured size limit")
        payload = json.loads(data)
        items = nested_value(payload, str(self.config["items_path"])) if self.config.get("items_path") else payload
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list) or any(not isinstance(row, dict) for row in items):
            raise ValueError("Connector payload must contain an object or list of objects")
        return items, payload

    async def _fetch(self, sample: bool = False) -> list[dict]:
        kind = self.pagination.get("type", "NONE")
        max_pages = 1 if sample or kind == "NONE" else int(self.pagination.get("max_pages", 20))
        rows: list[dict] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=False, trust_env=False, transport=self.transport) as client:
            for page in range(1, max_pages + 1):
                items, payload = await self._request_page(client, page, cursor, MAX_SAMPLE_BYTES if sample else MAX_RESPONSE_BYTES)
                rows.extend(items)
                if len(rows) > MAX_ROWS:
                    raise ValueError("Connector result exceeds 5000 rows")
                if sample or kind == "NONE" or not items:
                    break
                if kind == "CURSOR":
                    next_cursor = nested_value(payload, str(self.pagination.get("cursor_path", "nextCursor")))
                    if not next_cursor or str(next_cursor) in seen_cursors:
                        break
                    cursor = str(next_cursor)
                    seen_cursors.add(cursor)
                elif kind in {"PAGE_NUMBER", "OFFSET_LIMIT"}:
                    total = nested_value(payload, str(self.pagination["total_path"])) if self.pagination.get("total_path") else None
                    if total is not None and len(rows) >= int(total):
                        break
                    if len(items) < int(self.pagination.get("page_size", 100)):
                        break
                if page == max_pages:
                    raise ValueError("Pagination page limit reached before source was exhausted")
        return rows[:5] if sample else rows

    async def test_connection(self) -> bool:
        await self._fetch(sample=True)
        return True

    async def fetch_sample(self) -> list[dict]:
        return await self._fetch(sample=True)

    async def fetch_data(self) -> list[dict]:
        return await self._fetch()
