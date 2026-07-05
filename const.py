"""Constants for the Airconwithme integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "airconwithme"

DEFAULT_NAME = "Airconwithme"
DEFAULT_USERNAME = "Admin"
DEFAULT_PASSWORD = "admin"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_TIMEOUT = 10

CONF_HOST = "host"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"

MANUFACTURER = "Intesis"
MODEL = "Airconwithme"

UID_POWER = 1
UID_MODE = 2
UID_FAN = 4
UID_SWING = 5
UID_TARGET_TEMPERATURE = 9
UID_ROOM_TEMPERATURE = 10
UID_REMOTE_DISABLE = 12
UID_OPERATING_HOURS = 13
UID_ALARM = 14
UID_ERROR_CODE = 15
UID_MIN_SETPOINT = 35
UID_MAX_SETPOINT = 36
UID_OUTDOOR_TEMPERATURE = 37