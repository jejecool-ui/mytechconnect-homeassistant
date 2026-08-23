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

L'add-on Home Assistant est défini dans `addon/mytechconnect_pool/` et
référence l'image publique
`ghcr.io/jejecool-ui/mytechconnect-homeassistant`. L'image est actuellement
publiée pour `aarch64` (`linux/arm64`) et ses tags de version doivent rester
alignés avec `addon/mytechconnect_pool/config.yaml`.

Home Assistant fournit les options de l'add-on dans `/data/options.json`.
`docker/options_env.py` les convertit en variables d'environnement au
démarrage ; aucune URL de session ni aucun identifiant MQTT ne doit être
intégré à l'image ou au dépôt.

Le Supervisor Home Assistant gère le cycle de vie de l'add-on et affiche les
sorties standard de l'image dans ses logs. L'image effectue le polling et la
publication MQTT ; elle ne doit jamais envoyer de commande à la PAC.

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

## Image Docker

Le contexte de build est la racine du projet :

```bash
docker buildx build --platform linux/arm64 -f docker/Dockerfile -t mytechconnect-pool:arm64 --load .
```

Depuis un WSL amd64, activer d'abord l'émulation ARM64 si nécessaire :

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker buildx inspect --bootstrap
```

La sortie de `docker buildx inspect --bootstrap` doit mentionner `linux/arm64`. L'erreur `exec format error` pendant un `RUN apt-get` indique généralement que cette émulation n'est pas activée.

L'image utilise Chromium système et exécute un polling toutes les 900 secondes par défaut. Les variables obligatoires sont `MYTECHCONNECT_URL`, `MQTT_HOST`, `MQTT_USERNAME` et `MQTT_PASSWORD`; `POLL_INTERVAL_SECONDS` permet de modifier l'intervalle.

Home Assistant OS ne doit pas être administré avec `docker run` directement. Pour l'exécuter sur cette plateforme, intégrer cette image dans un add-on Home Assistant personnalisé.

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
/tmp/mytechconnect-venv/bin/python -m py_compile docker/options_env.py tools/mytechconnect_client.py tools/mytechconnect_dump.py tools/mytechconnect_mqtt.py tools/mytechconnect_probe.py
bash -n tools/run_mytechconnect_dump.sh tools/run_mytechconnect_mqtt.sh
bash -n docker/entrypoint.sh
```

Mettre à jour `PLAN.md` lorsque l'architecture, les sensors ou les règles de sécurité changent.
