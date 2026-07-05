"""Service layer for Airconwithme integration."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register services."""

    async def _get_coordinator(hass: HomeAssistant, call: ServiceCall):
        """Helper to get coordinator safely."""

        entry_id = call.data.get("entry_id")
        if not entry_id:
            return None

        try:
            return hass.data[DOMAIN][entry_id]["coordinator"]
        except Exception:
            _LOGGER.exception("Coordinator not found")
            return None

    # -------------------------
    # POWER SERVICE
    # -------------------------
    async def set_power(call: ServiceCall) -> None:
        try:
            coord = await _get_coordinator(hass, call)
            if not coord:
                return

            await coord.async_set_value(1, call.data.get("state", 1))

        except Exception:
            _LOGGER.exception("set_power failed")

    # -------------------------
    # MODE SERVICE
    # -------------------------
    async def set_mode(call: ServiceCall) -> None:
        try:
            coord = await _get_coordinator(hass, call)
            if not coord:
                return

            await coord.async_set_value(2, call.data.get("mode"))

        except Exception:
            _LOGGER.exception("set_mode failed")

    # -------------------------
    # TEMP SERVICE
    # -------------------------
    async def set_temperature(call: ServiceCall) -> None:
        try:
            coord = await _get_coordinator(hass, call)
            if not coord:
                return

            temp = call.data.get("temperature")
            if temp is None:
                return

            await coord.async_set_value(9, int(float(temp) * 10))

        except Exception:
            _LOGGER.exception("set_temperature failed")

    # -------------------------
    # FAN SERVICE
    # -------------------------
    async def set_fan(call: ServiceCall) -> None:
        try:
            coord = await _get_coordinator(hass, call)
            if not coord:
                return

            await coord.async_set_value(4, call.data.get("fan"))

        except Exception:
            _LOGGER.exception("set_fan failed")

    # Register services
    hass.services.async_register(DOMAIN, "set_power", set_power)
    hass.services.async_register(DOMAIN, "set_mode", set_mode)
    hass.services.async_register(DOMAIN, "set_temperature", set_temperature)
    hass.services.async_register(DOMAIN, "set_fan", set_fan)