"""Config flow for Airconwithme integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .api import AirconwithmeAPI
from .const import DEFAULT_NAME, DEFAULT_PASSWORD, DEFAULT_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_AREA_ID = "area_id"


def _normalize_host(host: str) -> str:
    """Normalize host input."""
    normalized = host.strip().removeprefix("http://").removeprefix("https://").rstrip("/")
    if normalized.endswith("/api.cgi"):
        normalized = normalized[: -len("/api.cgi")]
    return normalized


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


async def _validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, str]:
    """Validate user input by connecting to the device."""
    host = _normalize_host(data[CONF_HOST])

    api = AirconwithmeAPI(
        host=host,
        username=data.get(CONF_USERNAME, DEFAULT_USERNAME),
        password=data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
    )

    try:
        if not await api.login():
            raise CannotConnect

        info = await api.get_info()
        if info.get("success") is not True:
            raise CannotConnect

    finally:
        await api.close()

    device_model = info.get("data", {}).get("info", {}).get("deviceModel")

    return {
        "host": host,
        "model": str(device_model or ""),
    }


class AirconwithmeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Airconwithme."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = _normalize_host(user_input.get(CONF_HOST, ""))

            if not host:
                errors["base"] = "no_host"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                normalized_input = dict(user_input)
                normalized_input[CONF_HOST] = host

                try:
                    await _validate_input(self.hass, normalized_input)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected Airconwithme config flow error")
                    errors["base"] = "unknown"
                else:
                    name = normalized_input.get(CONF_NAME) or f"{DEFAULT_NAME} {host}"

                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_NAME: name,
                            CONF_HOST: host,
                            CONF_USERNAME: normalized_input.get(
                                CONF_USERNAME,
                                DEFAULT_USERNAME,
                            ),
                            CONF_PASSWORD: normalized_input.get(
                                CONF_PASSWORD,
                                DEFAULT_PASSWORD,
                            ),
                            CONF_AREA_ID: normalized_input.get(CONF_AREA_ID),
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_AREA_ID): selector.AreaSelector(),
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """Return the options flow."""
        return AirconwithmeOptionsFlow(config_entry)


class AirconwithmeOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Airconwithme."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )