"""Diagnostics support for Airconwithme."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    safe_config = dict(entry.data)
    if CONF_PASSWORD in safe_config:
        safe_config[CONF_PASSWORD] = "REDACTED"

    entry_data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = entry_data.get("coordinator")

    device_registry = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

    return {
        "config": safe_config,
        "runtime": {
            "has_api": "api" in entry_data,
            "has_coordinator": coordinator is not None,
            "last_update_success": getattr(coordinator, "last_update_success", None),
        },
        "state": getattr(coordinator, "data", None) or {},
        "devices": [
            {
                "id": device.id,
                "name": device.name,
                "manufacturer": device.manufacturer,
                "model": device.model,
            }
            for device in devices
        ],
    }