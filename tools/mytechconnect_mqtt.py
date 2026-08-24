#!/usr/bin/env python3
"""Read MyTechConnect and publish Home Assistant MQTT Discovery entities."""

import json
import logging
import os
import sys

import paho.mqtt.client as mqtt

try:
    from mytechconnect_dump import collect_values
except ModuleNotFoundError:  # Import also works as tools.mytechconnect_mqtt.
    from tools.mytechconnect_dump import collect_values


DEVICE = {
    "identifiers": ["mytechconnect_pool"],
    "name": "MyTechConnect Pool",
    "manufacturer": "MyTechConnect",
    "model": "Cloud web interface",
}

AVAILABILITY_TOPIC = "mytechconnect/pool/availability"


SENSORS = {
    "sensor.pool_water_temperature": {
        "name": "Pool Water Temperature",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    "sensor.pool_outdoor_temperature": {
        "name": "Pool Outdoor Temperature",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
        "state_class": "measurement",
    },
    "sensor.pool_heat_pump_temperature_setpoint": {
        "name": "Pool Heat Pump Temperature Setpoint",
        "unit_of_measurement": "°C",
        "device_class": "temperature",
    },
    "sensor.pool_heat_pump_operation_mode": {
        "name": "Pool Heat Pump Operation Mode",
    },
    "sensor.pool_heat_pump_regulation_mode": {
        "name": "Pool Heat Pump Regulation Mode",
    },
    "binary_sensor.pool_heat_pump": {
        "name": "Pool Heat Pump",
        "payload_on": "ON",
        "payload_off": "OFF",
    },
    "binary_sensor.pool_water_flow": {
        "name": "Pool Water Flow",
        "payload_on": "ON",
        "payload_off": "OFF",
    },
}

NUMERIC_SENSOR_IDS = {
    entity_id
    for entity_id, definition in SENSORS.items()
    if "unit_of_measurement" in definition
}

LOGGER = logging.getLogger(__name__)


def topic_for(entity_id):
    object_id = entity_id.split(".", 1)[1]
    object_id = object_id.removeprefix("pool_")
    return f"mytechconnect/pool/{object_id}/state"


def publish(client, topic, payload, retain=True):
    info = client.publish(topic, payload, retain=retain)
    info.wait_for_publish(timeout=10)


def discovery_topic(entity_id, prefix):
    domain, object_id = entity_id.split(".", 1)
    return f"{prefix}/{domain}/{object_id}/config"


def mqtt_client(host, port, username, password):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if username:
        client.username_pw_set(username, password or None)
    client.will_set(AVAILABILITY_TOPIC, "offline", retain=True)
    client.connect(host, port, keepalive=30)
    client.loop_start()
    return client


def publish_discovery(client, prefix):
    for entity_id, definition in SENSORS.items():
        payload = {
            **definition,
            "unique_id": f"mytechconnect_{entity_id.replace('.', '_')}",
            "state_topic": topic_for(entity_id),
            "availability_topic": AVAILABILITY_TOPIC,
            "payload_available": "online",
            "payload_not_available": "offline",
            "device": DEVICE,
        }
        publish(client, discovery_topic(entity_id, prefix), json.dumps(payload))


def main():
    try:
        values = collect_values(os.environ.get("MYTECHCONNECT_URL"))
    except Exception as exc:
        LOGGER.error("MyTechConnect MQTT poll failed: %s", exc)
        return 1

    host = os.environ.get("MQTT_HOST", "core-mosquitto")
    port = int(os.environ.get("MQTT_PORT", "1883"))
    username = os.environ.get("MQTT_USERNAME")
    password = os.environ.get("MQTT_PASSWORD")
    prefix = os.environ.get("MQTT_DISCOVERY_PREFIX", "homeassistant")

    client = mqtt_client(host, port, username, password)
    try:
        LOGGER.info("Publishing MyTechConnect MQTT Discovery and sensor states")
        publish_discovery(client, prefix)
        publish(client, AVAILABILITY_TOPIC, "online")
        for entity_id in SENSORS:
            value = values.get(entity_id)
            if value is None:
                # Home Assistant's MQTT sensor parser expects numeric topics
                # to remain numeric. The literal "unavailable" is rejected
                # for sensors with a unit/device class; "None" maps to
                # unknown without producing a conversion error.
                state = "None" if entity_id in NUMERIC_SENSOR_IDS else "unavailable"
            else:
                state = str(value)
            publish(client, topic_for(entity_id), state)
        client.loop_stop()
        client.disconnect()
        LOGGER.info("MyTechConnect MQTT publication completed")
    except Exception:
        client.loop_stop()
        client.disconnect()
        raise

    print(json.dumps({"values": values}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
