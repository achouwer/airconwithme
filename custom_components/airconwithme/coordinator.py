"""Data coordinator for Airconwithme."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AirconwithmeAPI
from .const import (
    DEFAULT_SCAN_INTERVAL,
    UID_ALARM,
    UID_ERROR_CODE,
    UID_FAN,
    UID_MAINTENANCE_CONFIG,
    UID_MAINTENANCE_FILTER_CONFIG,
    UID_MAINTENANCE_FILTER_TIME,
    UID_MAINTENANCE_TIME,
    UID_MAX_SETPOINT,
    UID_MIN_SETPOINT,
    UID_MODE,
    UID_OPERATING_HOURS,
    UID_OUTDOOR_TEMPERATURE,
    UID_POWER,
    UID_REMOTE_DISABLE,
    UID_ROOM_TEMPERATURE,
    UID_SWING,
    UID_TARGET_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)

UID_TO_KEY = {
    UID_POWER: "power",
    UID_MODE: "mode",
    UID_FAN: "fan",
    UID_SWING: "swing",
    UID_TARGET_TEMPERATURE: "target_temperature",
    UID_ROOM_TEMPERATURE: "room_temperature",
    UID_REMOTE_DISABLE: "remote_disable",
    UID_OPERATING_HOURS: "operating_hours",
    UID_ALARM: "alarm",
    UID_ERROR_CODE: "error_code",
    UID_MIN_SETPOINT: "min_setpoint",
    UID_MAX_SETPOINT: "max_setpoint",
    UID_OUTDOOR_TEMPERATURE: "outdoor_temperature",
    UID_MAINTENANCE_TIME: "maintenance_time",
    UID_MAINTENANCE_CONFIG: "maintenance_config",
    UID_MAINTENANCE_FILTER_TIME: "maintenance_filter_time",
    UID_MAINTENANCE_FILTER_CONFIG: "maintenance_filter_config",
}


class AirconwithmeCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll Airconwithme status safely."""

    def __init__(self, hass: HomeAssistant, api: AirconwithmeAPI) -> None:
        """Initialize coordinator."""
        self.api = api
        self.hass = hass

        super().__init__(
            hass,
            _LOGGER,
            name="Airconwithme",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        response = await self.api.get_status()

        if not isinstance(response, dict):
            raise UpdateFailed("Invalid response from Airconwithme device")

        if response.get("success") is not True:
            raise UpdateFailed(str(response.get("error", "Airconwithme update failed")))

        return response

    async def async_set_value(self, uid: int, value: int) -> bool:
        """Write a datapoint, update HA immediately, then refresh after device settles."""
        try:
            result = await self.api.set_value(uid, value)

            if not isinstance(result, dict) or result.get("success") is not True:
                _LOGGER.warning(
                    "Set datapoint failed uid=%s value=%s result=%s",
                    uid,
                    value,
                    result,
                )
                return False

            self._optimistic_update(uid, value)
            self.hass.async_create_task(self._delayed_refresh(2))
            self.hass.async_create_task(self._delayed_refresh(8))
            return True

        except Exception:
            _LOGGER.exception("Set value failed")
            return False

    def _optimistic_update(self, uid: int, value: int) -> None:
        """Update coordinator data immediately after a successful write."""
        if not isinstance(self.data, dict):
            return

        data = deepcopy(self.data)
        data["success"] = True

        key = UID_TO_KEY.get(uid)
        if key:
            data[key] = value

        raw = data.setdefault("raw", {})
        if isinstance(raw, dict):
            item = raw.get(uid)
            if not isinstance(item, dict):
                item = {"uid": uid, "status": 0}
            item["value"] = value
            item["status"] = 0
            raw[uid] = item

        self.async_set_updated_data(data)

    async def _delayed_refresh(self, delay: int) -> None:
        """Refresh after the Intesis device has had time to publish the new value."""
        await asyncio.sleep(delay)
        try:
            await self.async_request_refresh()
        except Exception:
            _LOGGER.exception("Delayed refresh failed")
