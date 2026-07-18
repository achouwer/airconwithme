"""Climate platform for Airconwithme."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_AREA_ID,
    DOMAIN,
    FAN_MAP,
    MANUFACTURER,
    MODEL,
    SWING_MAP,
    UID_FAN,
    UID_MAX_SETPOINT,
    UID_MIN_SETPOINT,
    UID_MODE,
    UID_POWER,
    UID_ROOM_TEMPERATURE,
    UID_SWING,
    UID_TARGET_TEMPERATURE,
)
from .coordinator import AirconwithmeCoordinator

_LOGGER = logging.getLogger(__name__)

MODE_TO_HVAC = {
    0: HVACMode.AUTO,
    1: HVACMode.HEAT,
    2: HVACMode.DRY,
    3: HVACMode.FAN_ONLY,
    4: HVACMode.COOL,
}
HVAC_TO_MODE = {value: key for key, value in MODE_TO_HVAC.items()}
FAN_MAP_REV = {value: key for key, value in FAN_MAP.items()}
SWING_MAP_REV = {value: key for key, value in SWING_MAP.items()}


class AirconwithmeClimate(CoordinatorEntity[AirconwithmeCoordinator], ClimateEntity):
    """Airconwithme climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.AUTO,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.COOL,
    ]
    _attr_fan_modes = list(FAN_MAP.values())
    _attr_swing_modes = list(SWING_MAP.values())

    def __init__(self, coordinator: AirconwithmeCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)

        self._host = entry.data.get(CONF_HOST, entry.entry_id)
        self._name = entry.data.get(CONF_NAME, entry.title)
        self._area_id = entry.data.get(CONF_AREA_ID)

        self._attr_name = self._name
        self._attr_unique_id = f"{entry.entry_id}_climate"

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

    def _get(self, uid: int, default: Any = None) -> Any:
        """Safely get a raw datapoint value."""
        try:
            data = self.coordinator.data or {}
            if not data.get("success"):
                return default

            item = data.get("raw", {}).get(uid, {})
            if item.get("status") not in (None, 0):
                return default

            return item.get("value", default)
        except Exception:
            _LOGGER.exception("Data access failed")
            return default

    @staticmethod
    def _temp_from_raw(value: Any) -> float | None:
        """Convert API temperature value to Celsius."""
        try:
            if value is None:
                return None
            raw = int(value)
            if raw == 32768:
                return None
            return raw / 10.0
        except Exception:
            return None

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current HVAC mode."""
        try:
            power = self._get(UID_POWER)
            if power == 0:
                return HVACMode.OFF

            raw = self._get(UID_MODE, 0)
            return MODE_TO_HVAC.get(raw, HVACMode.AUTO)
        except Exception:
            return HVACMode.AUTO

    @property
    def current_temperature(self) -> float | None:
        """Return current room temperature."""
        return self._temp_from_raw(self._get(UID_ROOM_TEMPERATURE))

    @property
    def target_temperature(self) -> float | None:
        """Return target temperature."""
        return self._temp_from_raw(self._get(UID_TARGET_TEMPERATURE))

    @property
    def min_temp(self) -> float:
        """Return minimum target temperature."""
        return self._temp_from_raw(self._get(UID_MIN_SETPOINT)) or 18.0

    @property
    def max_temp(self) -> float:
        """Return maximum target temperature."""
        return self._temp_from_raw(self._get(UID_MAX_SETPOINT)) or 30.0

    @property
    def fan_mode(self) -> str | None:
        """Return fan mode as a readable Home Assistant value."""
        raw = self._get(UID_FAN)
        if raw is None:
            return None
        return FAN_MAP.get(raw, f"Speed {raw}")

    @property
    def swing_mode(self) -> str | None:
        """Return swing mode as a readable Home Assistant value."""
        raw = self._get(UID_SWING)
        if raw is None:
            return "Off"
        return SWING_MAP.get(raw, "Off")

    async def async_turn_on(self) -> None:
        """Turn the unit on."""
        try:
            await self.coordinator.async_set_value(UID_POWER, 1)
        except Exception:
            _LOGGER.exception("turn_on failed")

    async def async_turn_off(self) -> None:
        """Turn the unit off."""
        try:
            await self.coordinator.async_set_value(UID_POWER, 0)
        except Exception:
            _LOGGER.exception("turn_off failed")

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        try:
            temp = kwargs.get("temperature")
            if temp is None:
                return

            await self.coordinator.async_set_value(
                UID_TARGET_TEMPERATURE,
                int(float(temp) * 10),
            )
        except Exception:
            _LOGGER.exception("set_temperature failed")

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                await self.async_turn_off()
                return

            raw = HVAC_TO_MODE.get(hvac_mode)
            if raw is None:
                return

            await self.coordinator.async_set_value(UID_POWER, 1)
            await self.coordinator.async_set_value(UID_MODE, raw)
        except Exception:
            _LOGGER.exception("set_hvac_mode failed")

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set fan mode from readable Home Assistant value."""
        try:
            raw = FAN_MAP_REV.get(fan_mode)
            if raw is None and fan_mode.isdigit():
                raw = int(fan_mode)
            if raw is None:
                _LOGGER.warning("Unsupported fan mode: %s", fan_mode)
                return
            await self.coordinator.async_set_value(UID_FAN, raw)
        except Exception:
            _LOGGER.exception("set_fan_mode failed")

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing mode from readable Home Assistant value."""
        try:
            raw = SWING_MAP_REV.get(swing_mode)
            if raw is None and swing_mode.isdigit():
                raw = int(swing_mode)
            if raw is None:
                _LOGGER.warning("Unsupported swing mode: %s", swing_mode)
                return
            await self.coordinator.async_set_value(UID_SWING, raw)
        except Exception:
            _LOGGER.exception("set_swing_mode failed")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Airconwithme climate entity."""
    coordinator: AirconwithmeCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([AirconwithmeClimate(coordinator, entry)])

