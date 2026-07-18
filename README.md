# Airconwithme

Mitsubishi / IntesisHome / Airconwithme integration for Home Assistant.

This custom integration adds local support for Airconwithme air conditioning Wi-Fi modules through the local `api.cgi` interface.

## Features

- Local polling via the device webserver API.
- Multiple devices via config flow.
- Climate entity.
- Separate entities for dashboards and automations:
  - room temperature sensor
  - outdoor temperature sensor
  - operating hours sensor
  - alarm and error sensors
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

## Status

This is a first working version. It was built from locally observed Airconwithme / Intesis API behavior and may need more validation across different device models.

## Development

This integration was created and iteratively improved with help from OpenAI Codex. The implementation is based on locally observed behavior of the Airconwithme / Intesis web interface and Home Assistant testing.
