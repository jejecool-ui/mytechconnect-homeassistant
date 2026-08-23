# Configuration

Les options suivantes sont disponibles :

- `mytechconnect_url` : URL de session MyTechConnect, obligatoire.
- `mqtt_host` : hôte du broker MQTT, par défaut `core-mosquitto`.
- `mqtt_port` : port MQTT, par défaut `1883`.
- `mqtt_username` : identifiant MQTT, obligatoire.
- `mqtt_password` : mot de passe MQTT, obligatoire.
- `mqtt_discovery_prefix` : préfixe MQTT Discovery, par défaut `homeassistant`.
- `poll_interval_seconds` : intervalle entre deux lectures, par défaut `900`.

Le service reste strictement en lecture seule : il ne publie aucune commande
vers la pompe à chaleur et ne modifie aucun registre matériel.
