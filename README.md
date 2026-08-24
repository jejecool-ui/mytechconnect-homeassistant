# MyTechConnect Pool for Home Assistant

This project reads a heat pump's state from the MyTechConnect web interface
and publishes the values to Home Assistant through MQTT Discovery. It is
strictly read-only: it does not modify the hardware or send commands to the
heat pump.

## Installation in Home Assistant

The Docker image is published to GitHub Container Registry. The app is
currently available for `aarch64` (`linux/arm64`) systems.

1. In Home Assistant, open **Settings → Apps → Install app**.
2. Open the `⋮` menu and select **Repositories**.
3. Add this custom repository:

   ```text
   https://github.com/jejecool-ui/mytechconnect-homeassistant
   ```

4. Install **MyTechConnect Pool**.
5. Open the app configuration and enter the MyTechConnect session URL and
   MQTT settings.
6. Start the app.

Home Assistant supervises the container, provides the options through
`/data/options.json`, and displays the container output in the app logs.

## Configuration

| Option | Required | Default |
| --- | --- | --- |
| `mytechconnect_url` | yes | — |
| `mqtt_host` | no | `core-mosquitto` |
| `mqtt_port` | no | `1883` |
| `mqtt_username` | yes | — |
| `mqtt_password` | yes | — |
| `mqtt_discovery_prefix` | no | `homeassistant` |
| `poll_interval_seconds` | no | `900` |

The MyTechConnect session URL and MQTT password are masked fields in the
app configuration. Never commit them to GitHub or copy them into logs.

## Home Assistant entities

The app publishes these entities automatically:

- `binary_sensor.pool_heat_pump`
- `binary_sensor.pool_water_flow`
- `sensor.pool_water_temperature`
- `sensor.pool_outdoor_temperature`
- `sensor.pool_heat_pump_operation_mode`
- `sensor.pool_heat_pump_regulation_mode`
- `sensor.pool_heat_pump_temperature_setpoint`

States are retained on the `mytechconnect/pool` topics. Availability is
published on:

```text
mytechconnect/pool/availability
```

## Architecture

```text
Home Assistant Supervisor
        ↓ options.json / lifecycle / logs
MyTechConnect Pool app
        ↓ GHCR image
Chromium + Playwright + DOM/Highcharts extraction
        ↓
MQTT Discovery + MQTT states
        ↓
Home Assistant entities
```

The app definition is stored in `addon/mytechconnect_pool/`. The image is
published as:

```text
ghcr.io/jejecool-ui/mytechconnect-homeassistant:0.1.3
```

The `latest` tag is also published by GitHub Actions.

## Local development

Diagnostic and one-shot collection scripts are located in `tools/`. Run the
following minimum checks:

```bash
python3 -m py_compile docker/options_env.py tools/mytechconnect_client.py \
  tools/mytechconnect_dump.py tools/mytechconnect_mqtt.py tools/mytechconnect_probe.py
bash -n docker/entrypoint.sh tools/run_mytechconnect_dump.sh \
  tools/run_mytechconnect_mqtt.sh
```

To build the ARM64 image with Docker Buildx:

```bash
docker buildx build --platform linux/arm64 \
  -f docker/Dockerfile \
  -t mytechconnect-pool:arm64 \
  --load .
```

## Security and limitations

- MyTechConnect is accessed in read-only mode.
- No Modbus writes or heat-pump commands are sent.
- Session URLs, cookies, and MQTT credentials must never be committed.
- The published image currently supports `aarch64` only.
- An exposed MyTechConnect session URL must be regenerated.
