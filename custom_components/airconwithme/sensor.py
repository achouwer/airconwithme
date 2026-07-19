"""Sensor platform for Airconwithme."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_AREA_ID, DOMAIN, MANUFACTURER, MODEL
from .coordinator import AirconwithmeCoordinator


@dataclass(frozen=True, kw_only=True)
class AirconwithmeSensorDescription(SensorEntityDescription):
    """Description of an Airconwithme sensor."""

    value_key: str
    divide_by_ten: bool = False


SENSORS: tuple[AirconwithmeSensorDescription, ...] = (
    AirconwithmeSensorDescription(
        key="room_temperature",
        name="Room temperature",
        value_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        divide_by_ten=True,
    ),
    AirconwithmeSensorDescription(
        key="outdoor_temperature",
        name="Outdoor temperature",
        value_key="outdoor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        divide_by_ten=True,
    ),
    AirconwithmeSensorDescription(
        key="operating_hours",
        name="Operating hours",
        value_key="operating_hours",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    AirconwithmeSensorDescription(
        key="error_code",
        name="Error code",
        value_key="error_code",
    ),
    AirconwithmeSensorDescription(
        key="alarm",
        name="Alarm",
        value_key="alarm",
    ),
    AirconwithmeSensorDescription(
        key="min_setpoint",
        name="Minimum setpoint",
        value_key="min_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        divide_by_ten=True,
    ),
    AirconwithmeSensorDescription(
        key="max_setpoint",
        name="Maximum setpoint",
        value_key="max_setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        divide_by_ten=True,
    ),
)


class AirconwithmeSensor(CoordinatorEntity[AirconwithmeCoordinator], SensorEntity):
    """Airconwithme sensor entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirconwithmeCoordinator,
        entry: ConfigEntry,
        description: AirconwithmeSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._host = entry.data.get(CONF_HOST, entry.entry_id)
        self._name = entry.data.get(CONF_NAME, entry.title)
        self._area_id = entry.data.get(CONF_AREA_ID)

        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class

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
        """Return whether the sensor is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def native_value(self) -> int | float | None:
        """Return sensor value."""
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

        if self.entity_description.divide_by_ten:
            return raw / 10.0

        return raw


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme sensors."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        AirconwithmeSensor(coordinator, entry, description)
        for description in SENSORS
    )
