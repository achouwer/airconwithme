"""Select platform for Airconwithme."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AREA_ID,
    DOMAIN,
    FAN_MAP,
    MANUFACTURER,
    MODE_MAP,
    MODEL,
    REMOTE_CONTROL_MAP,
    SWING_MAP,
    UID_FAN,
    UID_MODE,
    UID_REMOTE_DISABLE,
    UID_SWING,
)
from .coordinator import AirconwithmeCoordinator


@dataclass(frozen=True, kw_only=True)
class AirconwithmeSelectDescription(SelectEntityDescription):
    """Description of an Airconwithme select."""

    uid: int
    value_key: str
    options_map: dict[int, str] = field(default_factory=dict)


SELECTS: tuple[AirconwithmeSelectDescription, ...] = (
    AirconwithmeSelectDescription(
        key="mode",
        name="Mode",
        uid=UID_MODE,
        value_key="mode",
        options_map=MODE_MAP,
    ),
    AirconwithmeSelectDescription(
        key="fan_speed",
        name="Fan speed",
        uid=UID_FAN,
        value_key="fan",
        options_map=FAN_MAP,
    ),
    AirconwithmeSelectDescription(
        key="swing",
        name="Swing",
        uid=UID_SWING,
        value_key="swing",
        options_map=SWING_MAP,
    ),
    AirconwithmeSelectDescription(
        key="remote_control",
        name="Remote control",
        uid=UID_REMOTE_DISABLE,
        value_key="remote_disable",
        options_map=REMOTE_CONTROL_MAP,
    ),
)


class AirconwithmeSelect(CoordinatorEntity[AirconwithmeCoordinator], SelectEntity):
    """Airconwithme select entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AirconwithmeCoordinator,
        entry: ConfigEntry,
        description: AirconwithmeSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._reverse_map = {value: key for key, value in description.options_map.items()}
        self._host = entry.data.get(CONF_HOST, entry.entry_id)
        self._name = entry.data.get(CONF_NAME, entry.title)
        self._area_id = entry.data.get(CONF_AREA_ID)

        self._attr_name = description.name
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_options = list(description.options_map.values())

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
        """Return whether the select is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        data = self.coordinator.data or {}
        value = data.get(self.entity_description.value_key)
        if value is None:
            if self.entity_description.key == "swing":
                return "Off"
            return None

        try:
            raw = int(value)
        except (TypeError, ValueError):
            return None

        return self.entity_description.options_map.get(raw)

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        raw = self._reverse_map.get(option)
        if raw is None:
            return

        await self.coordinator.async_set_value(self.entity_description.uid, raw)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme selects."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        AirconwithmeSelect(coordinator, entry, description)
        for description in SELECTS
    )
