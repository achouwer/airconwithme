"""Number platform for Airconwithme."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
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
    UID_MAINTENANCE_CONFIG,
    UID_MAINTENANCE_FILTER_CONFIG,
    UID_MAINTENANCE_FILTER_TIME,
    UID_MAINTENANCE_TIME,
    UID_TARGET_TEMPERATURE,
)
from .coordinator import AirconwithmeCoordinator


@dataclass(frozen=True, kw_only=True)
class AirconwithmeNumberDescription(NumberEntityDescription):
    """Description of an Airconwithme number entity."""

    uid: int
    value_key: str


MAINTENANCE_NUMBERS: tuple[AirconwithmeNumberDescription, ...] = (
    AirconwithmeNumberDescription(
        key="maintenance_time",
        name="Maintenance time",
        uid=UID_MAINTENANCE_TIME,
        value_key="maintenance_time",
        native_unit_of_measurement="h",
        native_step=1,
        mode=NumberMode.BOX,
    ),
    AirconwithmeNumberDescription(
        key="maintenance_config",
        name="Maintenance config",
        uid=UID_MAINTENANCE_CONFIG,
        value_key="maintenance_config",
        native_unit_of_measurement="h",
        native_step=1,
        mode=NumberMode.BOX,
    ),
    AirconwithmeNumberDescription(
        key="maintenance_filter_time",
        name="Maintenance filter time",
        uid=UID_MAINTENANCE_FILTER_TIME,
        value_key="maintenance_filter_time",
        native_unit_of_measurement="h",
        native_step=1,
        mode=NumberMode.BOX,
    ),
    AirconwithmeNumberDescription(
        key="maintenance_filter_config",
        name="Maintenance filter config",
        uid=UID_MAINTENANCE_FILTER_CONFIG,
        value_key="maintenance_filter_config",
        native_unit_of_measurement="h",
        native_step=1,
        mode=NumberMode.BOX,
    ),
)


def _device_info(entry: ConfigEntry) -> dict[str, Any]:
    """Return shared device info for number entities."""
    host = entry.data.get(CONF_HOST, entry.entry_id)
    name = entry.data.get(CONF_NAME, entry.title)
    area_id = entry.data.get(CONF_AREA_ID)

    device_info: dict[str, Any] = {
        "identifiers": {(DOMAIN, host)},
        "name": name,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        "configuration_url": f"http://{host}/",
    }
    if area_id:
        device_info["suggested_area"] = area_id
    return device_info


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
        self._attr_unique_id = f"{entry.entry_id}_target_temperature"
        self._attr_device_info = _device_info(entry)

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


class AirconwithmeMaintenanceNumber(
    CoordinatorEntity[AirconwithmeCoordinator],
    NumberEntity,
):
    """Maintenance hour number entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirconwithmeCoordinator,
        entry: ConfigEntry,
        description: AirconwithmeNumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def available(self) -> bool:
        """Return whether the number is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def native_value(self) -> int | None:
        """Return current maintenance hour value."""
        data = self.coordinator.data or {}
        value = data.get(self.entity_description.value_key)
        if value is None:
            return None
        try:
            raw = int(value)
        except (TypeError, ValueError):
            return None
        if raw == 32768:
            return None
        return raw

    async def async_set_native_value(self, value: float) -> None:
        """Set maintenance hour value."""
        await self.coordinator.async_set_value(
            self.entity_description.uid,
            int(float(value)),
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme number entities."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [
            AirconwithmeTargetTemperatureNumber(coordinator, entry),
            *(
                AirconwithmeMaintenanceNumber(coordinator, entry, description)
                for description in MAINTENANCE_NUMBERS
            ),
        ]
    )
