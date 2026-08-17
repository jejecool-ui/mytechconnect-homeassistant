# MyTechConnect → Home Assistant

## Objectif

Ce projet récupère en lecture seule l'état d'une pompe à chaleur via l'interface web MyTechConnect et prépare sa publication dans Home Assistant via MQTT.

La contrainte principale est de ne faire aucune modification hardware et de ne pas envoyer de commande à la PAC.

## Sensors ciblés

- `binary_sensor.pool_heat_pump` : état `ON`/`OFF`.
- `binary_sensor.pool_water_flow` : débit d'eau détecté ou absence de débit.
- `sensor.pool_water_temperature` : température de l'eau en °C.
- `sensor.pool_outdoor_temperature` : température extérieure en °C.
- `sensor.pool_heat_pump_operation_mode` : `heating`, `cooling` ou `auto`.
- `sensor.pool_heat_pump_regulation_mode` : `eco`, `smart` ou `boost`.
- `sensor.pool_heat_pump_temperature_setpoint` : consigne en °C.

## Règle importante pour la température d'eau

La page principale est la source de vérité pour savoir si une température d'eau est disponible.

- Si la page principale n'affiche aucune température d'eau, publier une valeur indisponible et ne pas ouvrir le graphique.
- Si la page principale affiche une température entière, le graphique peut être ouvert pour obtenir la dernière valeur décimale de `Température d'eau (calculée)`.
- Ne jamais utiliser la valeur du graphique lorsque la page principale signale l'absence de débit ou ne fournit pas de température.

## Architecture

`Chromium headless + Playwright → extraction DOM/Highcharts → MQTT Discovery → Home Assistant`

Le code commun est dans `tools/mytechconnect_client.py`.

- `mytechconnect_probe.py` : diagnostic, captures HTML/PNG et extraction complète du graphique.
- `mytechconnect_dump.py` : collecte ponctuelle et sortie JSON.
- `mytechconnect_mqtt.py` : collecte puis publication MQTT Discovery et états MQTT.
- `run_mytechconnect_dump.sh` : lanceur interactif du dump JSON.
- `run_mytechconnect_mqtt.sh` : lanceur interactif de la publication MQTT.

## Topics MQTT

Les états sont publiés avec `retain=true` :

```text
mytechconnect/pool/water_temperature/state
mytechconnect/pool/water_flow/state
mytechconnect/pool/heat_pump/state
mytechconnect/pool/outdoor_temperature/state
mytechconnect/pool/heat_pump/operation_mode/state
mytechconnect/pool/heat_pump/regulation_mode/state
mytechconnect/pool/heat_pump/temperature_setpoint/state
mytechconnect/pool/availability
```

Les configurations MQTT Discovery sont publiées sous `homeassistant/` par défaut.

## Exécution locale

Depuis la racine du projet :

```bash
export PLAYWRIGHT_CHROMIUM=/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
./tools/run_mytechconnect_dump.sh
```

Pour MQTT :

```bash
export MQTT_HOST=core-mosquitto
export MQTT_PORT=1883
export MQTT_USERNAME=...
export MQTT_PASSWORD=...
./tools/run_mytechconnect_mqtt.sh
```

Dépendances :

```bash
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-browser.txt
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-mqtt.txt
```

## Sécurité

- Ne jamais écrire l'URL `MYTECHCONNECT_URL`, les cookies ou les identifiants MQTT dans Git.
- Ne jamais afficher ou recopier l'URL de session dans les logs.
- Utiliser une nouvelle URL de session si celle-ci a été partagée ou exposée.
- Toute évolution doit rester en lecture seule : pas de clic de commande, pas d'écriture Modbus et pas de publication MQTT de commandes.

## Vérifications avant modification

```bash
/tmp/mytechconnect-venv/bin/python -m py_compile tools/mytechconnect_client.py tools/mytechconnect_dump.py tools/mytechconnect_mqtt.py tools/mytechconnect_probe.py
bash -n tools/run_mytechconnect_dump.sh tools/run_mytechconnect_mqtt.sh
```

Mettre à jour `PLAN.md` lorsque l'architecture, les sensors ou les règles de sécurité changent.
