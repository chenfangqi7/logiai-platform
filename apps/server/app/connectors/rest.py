import ipaddress
import json
import socket
from urllib.parse import urlparse

import httpx

from app.connectors.base import BaseConnector
from app.core.config import get_settings

MAX_RESPONSE_BYTES = 5 * 1024 * 1024


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


class RestApiConnector(BaseConnector):
    def __init__(self, url: str, config: dict, auth_type: str = "none") -> None:
        validate_connector_url(url)
        self.url = url
        self.config = config
        self.auth_type = auth_type

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.auth_type == "bearer" and self.config.get("token"):
            headers["Authorization"] = f"Bearer {self.config['token']}"
        elif self.auth_type == "header" and self.config.get("header_name") and self.config.get("header_value"):
            name = str(self.config["header_name"])
            if name.lower() in {"host", "content-length"}:
                raise ValueError("Unsupported auth header")
            headers[name] = str(self.config["header_value"])
        return headers

    async def _fetch(self) -> list[dict]:
        # Redirects are disabled so a public URL cannot redirect to an internal service.
        async with httpx.AsyncClient(timeout=10, follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", self.url, headers=self._headers()) as response:
                response.raise_for_status()
                if response.status_code in {301, 302, 303, 307, 308}:
                    raise ValueError("Connector redirects are not supported")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ValueError("Connector response exceeds 5 MB")
        payload = json.loads(body)
        items_path = str(self.config.get("items_path", ""))
        if items_path:
            for segment in items_path.split("."):
                if not isinstance(payload, dict):
                    raise ValueError("Invalid items path")
                payload = payload.get(segment)
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise ValueError("Connector payload must be an object or list of objects")
        return payload

    async def test_connection(self) -> bool:
        await self._fetch()
        return True

    async def fetch_sample(self) -> list[dict]:
        return (await self._fetch())[:5]

    async def fetch_data(self) -> list[dict]:
        return await self._fetch()
