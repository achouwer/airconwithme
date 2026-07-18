"""Number platform for Airconwithme."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AREA_ID,
    DOMAIN,
    MANUFACTURER,
    MODEL,
    UID_TARGET_TEMPERATURE,
)
from .coordinator import AirconwithmeCoordinator


class AirconwithmeTargetTemperatureNumber(
    CoordinatorEntity[AirconwithmeCoordinator],
    NumberEntity,
):
    """Target temperature number entity."""

    _attr_has_entity_name = True
    _attr_name = "Target temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_step = 0.5
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: AirconwithmeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._host = entry.data.get(CONF_HOST, entry.entry_id)
        self._name = entry.data.get(CONF_NAME, entry.title)
        self._area_id = entry.data.get(CONF_AREA_ID)

        self._attr_unique_id = f"{entry.entry_id}_target_temperature"

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
        """Return whether the number is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @staticmethod
    def _temp_from_raw(value: Any) -> float | None:
        """Convert API temperature value to Celsius."""
        if value is None:
            return None
        try:
            raw = int(value)
        except (TypeError, ValueError):
            return None
        if raw == 32768:
            return None
        return raw / 10.0

    @property
    def native_min_value(self) -> float:
        """Return minimum target temperature."""
        data = self.coordinator.data or {}
        return self._temp_from_raw(data.get("min_setpoint")) or 18.0

    @property
    def native_max_value(self) -> float:
        """Return maximum target temperature."""
        data = self.coordinator.data or {}
        return self._temp_from_raw(data.get("max_setpoint")) or 30.0

    @property
    def native_value(self) -> float | None:
        """Return target temperature."""
        data = self.coordinator.data or {}
        return self._temp_from_raw(data.get("target_temperature"))

    async def async_set_native_value(self, value: float) -> None:
        """Set target temperature."""
        await self.coordinator.async_set_value(UID_TARGET_TEMPERATURE, int(float(value) * 10))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme number entities."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([AirconwithmeTargetTemperatureNumber(coordinator, entry)])

