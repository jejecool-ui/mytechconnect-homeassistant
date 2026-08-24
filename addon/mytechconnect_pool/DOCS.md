# Configuration

The following options are available:

- `mytechconnect_url`: MyTechConnect session URL, required.
- `mqtt_host`: MQTT broker host, default `core-mosquitto`.
- `mqtt_port`: MQTT broker port, default `1883`.
- `mqtt_username`: MQTT username, required.
- `mqtt_password`: MQTT password, required.
- `mqtt_discovery_prefix`: MQTT Discovery prefix, default `homeassistant`.
- `poll_interval_seconds`: interval between polls, default `900`.

The service remains strictly read-only: it does not publish commands to the
heat pump and does not modify hardware registers.
