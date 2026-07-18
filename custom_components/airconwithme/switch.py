"""Switch platform for Airconwithme."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_AREA_ID, DOMAIN, MANUFACTURER, MODEL, UID_POWER
from .coordinator import AirconwithmeCoordinator


class AirconwithmePowerSwitch(CoordinatorEntity[AirconwithmeCoordinator], SwitchEntity):
    """Power switch for Airconwithme."""

    _attr_has_entity_name = True
    _attr_name = "Power"

    def __init__(self, coordinator: AirconwithmeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._host = entry.data.get(CONF_HOST, entry.entry_id)
        self._name = entry.data.get(CONF_NAME, entry.title)
        self._area_id = entry.data.get(CONF_AREA_ID)

        self._attr_unique_id = f"{entry.entry_id}_power"

        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self._host)},
            "name": self._name,
            "manufacturer": MANUFACTURER,
            "model": MODEL,
            "configuration_url": f"http://{self._host}/",
        }
        if self._area_id:
            device_info["suggested_area"] = self._area_id
        self._attr_device_info = device_info

    @property
    def available(self) -> bool:
        """Return whether the switch is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def is_on(self) -> bool | None:
        """Return whether power is on."""
        data = self.coordinator.data or {}
        power = data.get("power")
        if power is None:
            return None
        return int(power) == 1

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.coordinator.async_set_value(UID_POWER, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.coordinator.async_set_value(UID_POWER, 0)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme switch."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([AirconwithmePowerSwitch(coordinator, entry)])

