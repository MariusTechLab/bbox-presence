"""Local Bbox API client with optional session authentication."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlsplit

from aiohttp import (
    ClientConnectorCertificateError,
    ClientConnectorError,
    ClientError,
    ClientResponseError,
    ClientSession,
)

from .const import (
    API_PATH,
    DEFAULT_BBOX_IP,
    DEFAULT_HOST,
    LOGIN_PATH,
    USER_AGENT,
)
from .helpers import normalize_mac

_LOGGER = logging.getLogger(__name__)


class BboxApiError(Exception):
    """Base Bbox API error."""


class BboxAuthRequired(BboxApiError):
    """The Bbox requires authentication."""


class BboxApi:
    """Read local Bbox host and Wi-Fi station data."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        password: str | None = None,
    ) -> None:
        self._session = session
        self._host = self.clean_host(host)
        self._password = (password or "").strip()
        self._cookie_header: str | None = None
        self.last_url: str | None = None

    @staticmethod
    def clean_host(host: str) -> str:
        """Normalize a hostname, IP address, or URL supplied by the user."""
        value = host.strip().rstrip("/")
        if "://" in value:
            parts = urlsplit(value)
            value = parts.netloc or parts.path
        return value or DEFAULT_HOST

    def _candidates(self) -> list[tuple[str, bool | None]]:
        """Return local endpoint candidates in a deterministic order."""
        if self._host == DEFAULT_HOST:
            candidates = [
                (f"https://{DEFAULT_HOST}{API_PATH}", None),
                (f"http://{DEFAULT_BBOX_IP}{API_PATH}", None),
                (f"https://{DEFAULT_BBOX_IP}{API_PATH}", False),
            ]
        else:
            candidates = [
                (f"https://{self._host}{API_PATH}", None),
                (f"http://{self._host}{API_PATH}", None),
                (f"https://{self._host}{API_PATH}", False),
            ]

        seen: set[str] = set()
        result: list[tuple[str, bool | None]] = []
        for candidate in candidates:
            if candidate[0] not in seen:
                seen.add(candidate[0])
                result.append(candidate)
        return result

    @staticmethod
    def _base_url(url: str) -> str:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.netloc}"

    async def _async_login(
        self,
        base_url: str,
        ssl_mode: bool | None,
    ) -> None:
        """Log in and capture the Bbox session cookie."""
        if not self._password:
            raise BboxAuthRequired(
                "The Bbox requires authentication, but no administrator password "
                "is configured."
            )

        login_url = f"{base_url}{LOGIN_PATH}"
        kwargs: dict[str, Any] = {
            "timeout": 10,
            "allow_redirects": True,
            "data": {"password": self._password},
            "headers": {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
        }
        if ssl_mode is False:
            kwargs["ssl"] = False

        _LOGGER.debug("Authenticating to the Bbox via %s", login_url)
        async with self._session.post(login_url, **kwargs) as response:
            if response.status not in (200, 204):
                raise BboxApiError(
                    f"Bbox login failed with HTTP {response.status} at {response.url}"
                )

            cookies = response.cookies
            if cookies:
                self._cookie_header = "; ".join(
                    f"{name}={morsel.value}" for name, morsel in cookies.items()
                )
            else:
                set_cookie_headers = response.headers.getall("Set-Cookie", [])
                if not set_cookie_headers:
                    raise BboxApiError(
                        "The Bbox accepted the login but returned no session cookie."
                    )
                self._cookie_header = "; ".join(
                    header.split(";", 1)[0] for header in set_cookie_headers
                )

    async def _async_fetch_payload(
        self,
        url: str,
        ssl_mode: bool | None,
    ) -> Any:
        """Get the hosts endpoint, authenticating once when required."""
        for auth_attempt in range(2):
            headers = {
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            }
            if self._cookie_header:
                headers["Cookie"] = self._cookie_header

            kwargs: dict[str, Any] = {
                "timeout": 10,
                "allow_redirects": True,
                "headers": headers,
            }
            if ssl_mode is False:
                kwargs["ssl"] = False

            async with self._session.get(url, **kwargs) as response:
                self.last_url = str(response.url)

                if response.status in (401, 403):
                    self._cookie_header = None
                    if auth_attempt == 0:
                        base_url = self._base_url(str(response.url))
                        login_ssl_mode = (
                            None if response.url.host == DEFAULT_HOST else ssl_mode
                        )
                        await self._async_login(base_url, login_ssl_mode)
                        continue
                    raise BboxAuthRequired(
                        f"Bbox authentication was refused with HTTP {response.status}."
                    )

                if response.status != 200:
                    raise BboxApiError(
                        f"Bbox API returned HTTP {response.status} at {response.url}"
                    )

                return await response.json(content_type=None)

        raise BboxApiError("Unable to retrieve Bbox host data.")

    async def async_get_presence_data(self) -> dict[str, Any]:
        """Return hosts and MAC addresses currently in Wi-Fi station tables."""
        errors: list[str] = []
        saw_auth_required = False

        for url, ssl_mode in self._candidates():
            try:
                _LOGGER.debug("Trying Bbox hosts endpoint %s", url)
                payload = await self._async_fetch_payload(url, ssl_mode)
                data = self._parse_payload(payload)
                _LOGGER.debug(
                    "Bbox API succeeded via %s: %d hosts, %d Wi-Fi stations",
                    self.last_url,
                    len(data["hosts"]),
                    len(data["wireless_macs"]),
                )
                return data
            except BboxAuthRequired as err:
                saw_auth_required = True
                errors.append(f"{url} -> authentication required: {err}")
            except (
                ClientConnectorCertificateError,
                ClientConnectorError,
                ClientResponseError,
                ClientError,
                asyncio.TimeoutError,
                ValueError,
                BboxApiError,
            ) as err:
                errors.append(f"{url} -> {type(err).__name__}: {err}")

        detail = " ; ".join(errors)
        if saw_auth_required and not self._password:
            raise BboxAuthRequired(detail)
        raise BboxApiError(detail)

    @staticmethod
    def _parse_payload(payload: Any) -> dict[str, Any]:
        """Extract hosts and Wi-Fi station MAC addresses from API variants."""
        if isinstance(payload, dict):
            blocks = [payload]
        elif isinstance(payload, list):
            blocks = payload
        else:
            raise BboxApiError(
                f"Unexpected Bbox response type: {type(payload).__name__}"
            )

        hosts: dict[str, dict[str, Any]] = {}
        wireless_macs: set[str] = set()

        for block in blocks:
            if not isinstance(block, dict):
                continue

            host_container = block.get("hosts", {})
            if isinstance(host_container, dict):
                host_list = host_container.get("list", [])
                if isinstance(host_list, list):
                    for host in host_list:
                        if not isinstance(host, dict):
                            continue
                        mac = normalize_mac(str(host.get("macaddress", "")))
                        if mac:
                            hosts[mac] = host

            wireless_hosts = block.get("wirelesshosts", [])
            if isinstance(wireless_hosts, list):
                for radio in wireless_hosts:
                    if not isinstance(radio, dict):
                        continue
                    stations = radio.get("stations", [])
                    if not isinstance(stations, list):
                        continue
                    for station in stations:
                        if not isinstance(station, dict):
                            continue
                        mac = normalize_mac(str(station.get("macaddress", "")))
                        if mac:
                            wireless_macs.add(mac)

        return {"hosts": hosts, "wireless_macs": wireless_macs}
