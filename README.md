# Airconwithme Home Assistant Integration

Custom Home Assistant integration for local Airconwithme / Intesis `api.cgi` devices.

## Features

- Local polling via the device webserver API
- Multiple devices via config flow
- Climate entity
- Separate entities for easier dashboards and automations:
  - room temperature sensor
  - outdoor temperature sensor
  - operating hours sensor
  - alarm/error sensors
  - power switch
  - mode select
  - fan speed select
  - swing select
  - target temperature number

## Install

Copy `custom_components/airconwithme` to:

```text
/config/custom_components/airconwithme
```

Restart Home Assistant, then add the integration from Settings > Devices & services.

