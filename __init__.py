"""Airconwithme integration setup."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import AirconwithmeAPI
from .const import DEFAULT_PASSWORD, DEFAULT_USERNAME, DOMAIN
from .coordinator import AirconwithmeCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Airconwithme from a config entry."""
    host = entry.data[CONF_HOST]
    username = entry.data.get(CONF_USERNAME, DEFAULT_USERNAME)
    password = entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD)

    api = AirconwithmeAPI(host=host, username=username, password=password)
    coordinator = AirconwithmeCoordinator(hass=hass, api=api)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        await api.close()
        raise ConfigEntryNotReady(f"Airconwithme device {host} is not ready") from err

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Airconwithme config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    entry_data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if entry_data:
        api = entry_data.get("api")
        if isinstance(api, AirconwithmeAPI):
            await api.close()

    return unload_ok