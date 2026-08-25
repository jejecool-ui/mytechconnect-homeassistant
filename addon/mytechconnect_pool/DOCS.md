# Configuration

The following options are available:

- `mytechconnect_url`: MyTechConnect session URL, required.
- `mqtt_host`: MQTT broker host, default `core-mosquitto`.
- `mqtt_port`: MQTT broker port, default `1883`.
- `mqtt_username`: MQTT username, required.
- `mqtt_password`: MQTT password, required.
- `mqtt_discovery_prefix`: MQTT Discovery prefix, default `homeassistant`.
- `poll_interval_seconds`: interval between polls, default `900`.
- `resource_metrics`: enable optional CPU, memory, and process metrics, default `false`.
- `nice_level`: Linux process scheduling priority, default `10`. Values range
  from `-20` to `19`: lower values increase CPU priority, higher values lower
  CPU priority. `0` is the normal default priority; use positive values to
  give Home Assistant more CPU priority when the system is under load.

The service remains strictly read-only: it does not publish commands to the
heat pump and does not modify hardware registers.
