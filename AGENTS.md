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

- Lire la température extérieure depuis la page principale à chaque collecte.
- Ouvrir le graphique et lire la série `Température d'eau (calculée)` uniquement lorsque `water_flow` vaut `ON`.
- Lorsque `water_flow` vaut `OFF`, ne lire ni publier aucune température d'eau ; conserver la température extérieure de la page principale.

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
`RESOURCE_METRICS` active optionnellement les métriques de ressources du poll ;
elle est désactivée par défaut.
`NICE_LEVEL` contrôle la priorité CPU du polling ; sa valeur par défaut est
`10` et sa plage valide est `-20` à `19`.

Home Assistant OS ne doit pas être administré avec `docker run` directement. Pour l'exécuter sur cette plateforme, intégrer cette image dans un add-on Home Assistant personnalisé.

## Versionnement et publication

La version de l'add-on et le tag de l'image Docker doivent toujours rester
alignés. Lors d'une mise à jour de version, modifier la même version dans :

- `addon/mytechconnect_pool/config.yaml` (`version`) ;
- `.github/workflows/publish-image.yml` (tag Docker publié) ;
- `README.md` si le tag d'image y est mentionné.

Avant tout `git push`, demander explicitement à l'utilisateur s'il souhaite
mettre à jour la version. Ne jamais changer la version implicitement. Si une
mise à jour est demandée, vérifier tous les fichiers ci-dessus avant de
pousser ; le workflow GitHub Actions publiera alors le tag de version et
`latest` sur GHCR.

## Exécution locale

Les tests locaux se font directement avec Python et Chromium, sans Docker.
Depuis la racine du projet, créer l'environnement puis installer les
dépendances nécessaires au dump :

```bash
python3 -m venv /tmp/mytechconnect-venv
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-browser.txt
```

Le navigateur Chromium utilisé localement est :

```text
/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
```

Pour effectuer une collecte ponctuelle directement avec `mytechconnect_dump.py`,
charger l'URL depuis `conf.local.yaml` sans l'afficher :

```bash
eval "$(python3 -c 'import yaml, shlex; d=yaml.safe_load(open("conf.local.yaml")); print("export MYTECHCONNECT_URL=" + shlex.quote(str(d["mytechconnect_url"])))')"
export PLAYWRIGHT_CHROMIUM=/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
/tmp/mytechconnect-venv/bin/python tools/mytechconnect_dump.py
```

Les métriques de ressources sont désactivées par défaut. Pour les activer et
limiter la priorité CPU du test à `nice 10` :

```bash
export RESOURCE_METRICS=true
nice -n 10 /tmp/mytechconnect-venv/bin/python tools/mytechconnect_dump.py
```

Le résultat JSON est écrit sur la sortie standard ; les métriques sont
rapportées dans les logs (`max_processes`, `max_memory_mb` et
`child_cpu_seconds`). `NICE_LEVEL` est une option de l'entrypoint Docker ; en
exécution Python directe, utiliser `nice -n 10` comme ci-dessus.

Pour tester la publication MQTT directement, installer aussi les dépendances
MQTT :

```bash
eval "$(python3 -c 'import yaml, shlex; d=yaml.safe_load(open("conf.local.yaml")); m={"MYTECHCONNECT_URL":"mytechconnect_url","MQTT_HOST":"mqtt_host","MQTT_PORT":"mqtt_port","MQTT_USERNAME":"mqtt_username","MQTT_PASSWORD":"mqtt_password","MQTT_DISCOVERY_PREFIX":"mqtt_discovery_prefix","POLL_INTERVAL_SECONDS":"poll_interval_seconds","RESOURCE_METRICS":"resource_metrics","NICE_LEVEL":"nice_level"}; [print(f"export {k}={shlex.quote(str(d[v]))}") for k,v in m.items() if d.get(v) is not None]')"
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-mqtt.txt
nice -n 10 /tmp/mytechconnect-venv/bin/python tools/mytechconnect_mqtt.py
```

Le nom `core-mosquitto` est généralement résolu uniquement dans le réseau
Home Assistant. En dehors de ce réseau, utiliser dans `conf.local.yaml` un
nom ou une adresse MQTT accessible depuis la machine de test.

Pour un test interactif du dump, le lanceur reste disponible :

```bash
export PLAYWRIGHT_CHROMIUM=/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
./tools/run_mytechconnect_dump.sh
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
