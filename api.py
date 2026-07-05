"""Local Airconwithme / Intesis API client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

CONTENT_TYPE = "application/json; charset=utf-8"
SESSION_EXPIRED_CODE = 1


class AirconwithmeAPI:
    """Async API wrapper for the local Airconwithme / Intesis api.cgi endpoint."""

    def __init__(
        self,
        host: str,
        username: str = "Admin",
        password: str = "admin",
        timeout: int = 10,
    ) -> None:
        self.host = self._normalize_host(host)
        self.username = username
        self.password = password
        self.timeout = aiohttp.ClientTimeout(total=timeout)

        self._session: aiohttp.ClientSession | None = None
        self._session_id: str | None = None
        self._metadata: dict[int, dict[str, Any]] = {}
        self._values: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _normalize_host(host: str) -> str:
        normalized = host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
        if normalized.endswith("/api.cgi"):
            normalized = normalized[: -len("/api.cgi")]
        return normalized

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request_once(self, command: str, data: dict[str, Any] | None) -> dict[str, Any]:
        session = await self._get_session()

        try:
            async with session.post(
                f"http://{self.host}/api.cgi",
                json={"command": command, "data": data or {}},
                headers={"Content-Type": CONTENT_TYPE},
                timeout=self.timeout,
            ) as response:
                if response.status != 200:
                    return {"success": False, "error": {"code": f"http_{response.status}"}}
                body = await response.json(content_type=None)
        except asyncio.TimeoutError:
            return {"success": False, "error": {"code": "timeout"}}
        except aiohttp.ClientError as err:
            _LOGGER.debug("Airconwithme transport error: %s", err)
            return {"success": False, "error": {"code": "transport"}}
        except Exception:
            _LOGGER.exception("Unexpected Airconwithme request failure")
            return {"success": False, "error": {"code": "exception"}}

        if not isinstance(body, dict):
            return {"success": False, "error": {"code": "invalid_json"}}
        return body

    async def _request(
        self,
        command: str,
        data: dict[str, Any] | None = None,
        *,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        request_data = dict(data or {})

        if authenticated:
            if not self._session_id and not await self.login():
                return {"success": False, "error": {"code": "not_authenticated"}}
            request_data["sessionID"] = self._session_id

        last_result: dict[str, Any] = {"success": False, "error": {"code": "unknown"}}

        for attempt in range(3):
            last_result = await self._request_once(command, request_data)
            if last_result.get("success") is True:
                return last_result

            code = self._error_code(last_result)
            if authenticated and retry_auth and code == SESSION_EXPIRED_CODE:
                self._session_id = None
                if await self.login():
                    return await self._request(
                        command,
                        data,
                        authenticated=authenticated,
                        retry_auth=False,
                    )
                return last_result

            if attempt < 2:
                await asyncio.sleep(1)

        return last_result

    @staticmethod
    def _error_code(result: dict[str, Any]) -> int | str | None:
        error = result.get("error")
        if isinstance(error, dict):
            return error.get("code")
        return None

    async def login(self) -> bool:
        """Authenticate and store the client-side session id."""
        result = await self._request_once(
            "login",
            {"username": self.username, "password": self.password},
        )
        if result.get("success") is not True:
            _LOGGER.warning("Airconwithme login failed: %s", self._error_code(result))
            return False

        session_id = result.get("data", {}).get("id", {}).get("sessionID")
        if not isinstance(session_id, str) or not session_id:
            _LOGGER.warning("Airconwithme login response did not contain sessionID")
            return False

        self._session_id = session_id
        return True

    async def get_info(self) -> dict[str, Any]:
        """Return device info."""
        return await self._request("getinfo", None)

    async def get_available_datapoints(self) -> dict[int, dict[str, Any]]:
        """Fetch datapoint metadata."""
        result = await self._request("getavailabledatapoints", None)
        if result.get("success") is not True:
            return self._metadata

        datapoints = result.get("data", {}).get("dp", {}).get("datapoints", [])
        if isinstance(datapoints, list):
            self._metadata = {
                int(item["uid"]): item
                for item in datapoints
                if isinstance(item, dict) and "uid" in item
            }
        return self._metadata

    async def refresh_datapoints(self) -> dict[int, dict[str, Any]]:
        """Refresh all datapoint values using the official UI request shape."""
        result = await self._request("getdatapointvalue", {"uid": "all"})
        if result.get("success") is not True:
            return self._values

        values = result.get("data", {}).get("dpval", [])
        if isinstance(values, list):
            self._values = {
                int(item["uid"]): item
                for item in values
                if isinstance(item, dict) and "uid" in item
            }
        return self._values

    async def get_status(self) -> dict[str, Any]:
        """Return normalized integration status for the coordinator."""
        if not self._metadata:
            await self.get_available_datapoints()

        values = await self.refresh_datapoints()
        if not values:
            return {"success": False, "error": "no_values", "raw": {}}

        def value(uid: int, default: Any = None) -> Any:
            return values.get(uid, {}).get("value", default)

        return {
            "success": True,
            "power": value(1),
            "mode": value(2),
            "fan": value(4),
            "swing": value(5),
            "target_temperature": value(9),
            "room_temperature": value(10),
            "remote_disable": value(12),
            "operating_hours": value(13),
            "alarm": value(14),
            "error_code": value(15),
            "min_setpoint": value(35),
            "max_setpoint": value(36),
            "outdoor_temperature": value(37),
            "raw": values,
            "metadata": self._metadata,
        }

    async def set_value(self, uid: int, value: int) -> dict[str, Any]:
        """Write one datapoint using the official UI request shape."""
        result = await self._request(
            "setdatapointvalue",
            {"uid": int(uid), "value": int(value)},
        )
        if result.get("success") is True:
            await self.refresh_datapoints()
        return result