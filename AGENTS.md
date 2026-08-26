# MyTechConnect → Home Assistant

## Objectif

Ce projet récupère en lecture seule l'état d'une pompe à chaleur (PAC) de piscine via l'interface web MyTechConnect et prépare sa publication dans Home Assistant via MQTT Discovery.

La contrainte principale est de ne faire **aucune modification hardware** (pas de boîtier tiers, pas de raccordement RS-485 physique) et de **ne jamais envoyer de commande** à la PAC (lecture seule stricte).

---

## Sensors ciblés

| Entité Home Assistant | Type | Unité / Valeurs | Rôle |
| --- | --- | --- | --- |
| `binary_sensor.pool_heat_pump` | Binary Sensor | `ON` / `OFF` | État de marche de la PAC |
| `binary_sensor.pool_water_flow` | Binary Sensor | `ON` / `OFF` | Débit d'eau détecté (ou alarme débit) |
| `sensor.pool_water_temperature` | Sensor (`temperature`, `measurement`) | `°C` (décimale) | Température de l'eau (depuis Highcharts si débit `ON`) |
| `sensor.pool_outdoor_temperature` | Sensor (`temperature`, `measurement`) | `°C` | Température extérieure (depuis vue principale) |
| `sensor.pool_heat_pump_operation_mode` | Sensor | `heating`, `cooling`, `auto` | Mode de fonctionnement |
| `sensor.pool_heat_pump_regulation_mode` | Sensor | `eco`, `smart`, `boost` | Mode de régulation de puissance |
| `sensor.pool_heat_pump_temperature_setpoint` | Sensor (`temperature`) | `°C` | Consigne de température |

---

## Règle importante pour la température d'eau

La page principale est la source de vérité pour savoir si un débit d'eau est présent.

- **Température extérieure** : lue depuis la page principale à chaque collecte.
- **Débit `ON`** : naviguer vers le graphique et extraire la série `Température d'eau (calculée)` pour obtenir la valeur décimale précise.
- **Débit `OFF`** (message `PAS DE DÉBIT D’EAU (VÉRIFIEZ LA POMPE DE CIRCULATION)`) : ne pas consulter le graphique. Aucune nouvelle valeur n'est publiée sur le topic MQTT de la température d'eau (`sensor.pool_water_temperature`), conservant ainsi la dernière valeur retenue dans MQTT / Home Assistant. La température extérieure reste conservée et mise à jour.
- En cas d'échec d'extraction du graphique alors que le débit est `ON`, ne pas publier de nouvelle valeur de température d'eau sans faire échouer l'ensemble de la collecte.

---

## Fonctionnement sous le capot

### Rétro-ingénierie & Nature de l'interface web
L'application mobile MyTechConnect (`com.ingeli.MyTechConnect`, .NET MAUI / Xamarin) utilise des briques communes avec l'écosystème Polytropic / PolyConnect (`PolyconnectCommons.dll`, `IngeliModbusDriver.dll`, `IngeliStdMqtt.dll`).
Elle redirige l'utilisateur vers une application web hébergée sur `https://mytech-connect.user-app.pool.mytech-connect.io/from-native/<jeton_session>`.

- **Blazor Server & SignalR** : Le HTML initial est une coquille vide (`#user-app`). Le contenu et les données dynamiques sont injectés via un circuit Blazor Server négocié sur `/_blazor/negotiate` avec le protocole `blazorpack` (WebSocket / SSE / Long Polling).
- **Rendu graphique Highcharts** : Le graphique de température est généré dynamiquement côté client par Highcharts (`window.Highcharts.charts`). Les points contiennent `{x: timestamp_ms, y: value}` espacés d'environ 5 minutes.
- **Nécessité de Chromium** : Un simple appel HTTP REST ne suffit pas à récupérer les données ; l'exécution d'un moteur JavaScript headless (Playwright + Chromium) est requise.

### Optimisation des ressources
Pour fonctionner de manière fluide sur des hôtes Home Assistant légers (ex. Raspberry Pi) :
- **Blocage des ressources non essentielles** : interception réseau Playwright pour avorter immédiatement les requêtes `image`, `font`, `media` et `stylesheet`.
- **Viewport mobile réduit** : fixé à `390×844`.
- **Arguments de démarrage optimisés** : limitation à un seul processus de rendu (`--renderer-process-limit=1`), bridage du tas JS V8 (`--js-flags=--max-old-space-size=128`), désactivation de la rastérisation logicielle et coupure du son.
- **Timeouts adaptés** : 240 secondes par défaut pour les étapes, 480 secondes pour le chargement et le rendu initial du circuit Blazor.
- **Priorité CPU (`nice`)** : exécution par défaut avec `nice -n 10` (configurable de `-20` à `19`).
- **Cycle de vie propre** : fermeture systématique du navigateur Chromium dans un bloc `finally` pour éviter tout processus résiduel.
- **Métriques optionnelles (`resource_metrics`)** : surveillance du pic de mémoire PSS (`/proc/<pid>/smaps_rollup`), de la mémoire RSS, du nombre de processus et du temps CPU cumulé des processus Chromium descendants.

---

## Architecture du Dépôt

`Chromium headless + Playwright → extraction DOM/Highcharts → MQTT Discovery → Home Assistant`

- `tools/mytechconnect_client.py` : code commun Playwright, sélecteurs DOM, navigation Highcharts, fonctions de sanitisation et de normalisation.
- `tools/mytechconnect_dump.py` : collecte ponctuelle, sortie JSON sur stdout, gestion du moniteur de ressources.
- `tools/mytechconnect_mqtt.py` : collecte puis publication de la configuration MQTT Discovery et des états MQTT.
- `tools/mytechconnect_probe.py` : outil de diagnostic approfondi (captures d'écran PNG, dumps HTML/texte, export complet des séries Highcharts dans `analysis/`).
- `tools/run_mytechconnect_dump.sh` : lanceur interactif du dump JSON.
- `tools/run_mytechconnect_mqtt.sh` : lanceur interactif de la publication MQTT.
- `docker/Dockerfile` : image Python 3.12 slim + Chromium système Debian.
- `docker/entrypoint.sh` : boucle de polling périodique et gestion du niveau de priorité `nice`.
- `docker/options_env.py` : conversion des options `/data/options.json` en variables d'environnement.
- `addon/mytechconnect_pool/` : définition de l'add-on Home Assistant (`config.yaml`, documentation, icônes).
- `analysis/` : artefacts d'analyse statique du XAPK 6.2, scripts JS Blazor et dumps de référence.

---

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

### Particularités MQTT & Discovery :
- Les configurations Discovery sont publiées sous `{MQTT_DISCOVERY_PREFIX}/{domain}/{object_id}/config` (`homeassistant/` par défaut).
- L'availability (`online` / `offline`) est gérée avec un Last Will and Testament (LWT) sur `mytechconnect/pool/availability`.
- **Sensors numériques** : pour les capteurs avec `unit_of_measurement` (températures), une valeur indisponible est publiée sous la chaîne `"None"` pour que Home Assistant la traite comme `unknown` sans lever d'erreur de conversion numérique (contrairement à la chaîne `"unavailable"`).

---

## Configuration de l'Add-on / Variables d'environnement

| Option Home Assistant | Variable d'environnement | Obligatoire | Valeur par défaut | Description |
| --- | --- | --- | --- | --- |
| `mytechconnect_url` | `MYTECHCONNECT_URL` | **Oui** | — | URL de session complète (`https://.../from-native/...`) |
| `mqtt_host` | `MQTT_HOST` | Non | `core-mosquitto` | Hôte du broker MQTT |
| `mqtt_port` | `MQTT_PORT` | Non | `1883` | Port du broker MQTT |
| `mqtt_username` | `MQTT_USERNAME` | **Oui** | — | Nom d'utilisateur MQTT |
| `mqtt_password` | `MQTT_PASSWORD` | **Oui** | — | Mot de passe MQTT |
| `mqtt_discovery_prefix` | `MQTT_DISCOVERY_PREFIX` | Non | `homeassistant` | Préfixe MQTT Discovery |
| `poll_interval_seconds` | `POLL_INTERVAL_SECONDS` | Non | `900` | Intervalle de collecte en secondes (défaut 15 min) |
| `resource_metrics` | `RESOURCE_METRICS` | Non | `false` | Activer la mesure des ressources CPU/RAM |
| `nice_level` | `NICE_LEVEL` | Non | `10` | Priorité CPU du processus (`-20` à `19`) |

---

## Image Docker & Déploiement

L'add-on référence l'image publique :
`ghcr.io/jejecool-ui/mytechconnect-homeassistant`

Contexte de build à la racine du projet :

```bash
docker buildx build --platform linux/arm64 -f docker/Dockerfile -t mytechconnect-pool:arm64 --load .
```

Depuis un environnement WSL/hôte amd64, activer l'émulation ARM64 si nécessaire :

```bash
docker run --privileged --rm tonistiigi/binfmt --install arm64
docker buildx inspect --bootstrap
```

La sortie de `docker buildx inspect --bootstrap` doit mentionner `linux/arm64`.

---

## Versionnement et publication

La version de l'add-on et le tag de l'image Docker doivent **toujours** rester alignés.
Lors d'une mise à jour de version, modifier simultanément :

1. `addon/mytechconnect_pool/config.yaml` (`version`) ;
2. `.github/workflows/publish-image.yml` (tag Docker publié) ;
3. `README.md` (si le tag d'image y est mentionné).

> **RÈGLE OBLIGATOIRE :**
> Avant tout `git push`, demander explicitement à l'utilisateur s'il souhaite mettre à jour la version. Ne jamais changer la version implicitement.
> Si une mise à jour est demandée, vérifier tous les fichiers ci-dessus avant de pousser ; le workflow GitHub Actions publiera alors le tag de version et `latest` sur GHCR.

---

## Exécution locale

Les tests locaux se font directement avec Python et Chromium, sans passer par Docker.

### 1. Préparation de l'environnement virtuel

```bash
python3 -m venv /tmp/mytechconnect-venv
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-browser.txt
/tmp/mytechconnect-venv/bin/python -m pip install -r tools/requirements-mqtt.txt
```

Le binaire Chromium local est :
```text
/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
```

### 2. Collecte ponctuelle (Dump JSON)

Depuis `conf.local.yaml` (sans afficher l'URL) :

```bash
eval "$(python3 -c 'import yaml, shlex; d=yaml.safe_load(open("conf.local.yaml")); print("export MYTECHCONNECT_URL=" + shlex.quote(str(d["mytechconnect_url"])))')"
export PLAYWRIGHT_CHROMIUM=/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
export RESOURCE_METRICS=true
nice -n 10 /tmp/mytechconnect-venv/bin/python tools/mytechconnect_dump.py
```

### 3. Test de la publication MQTT

```bash
eval "$(python3 -c 'import yaml, shlex; d=yaml.safe_load(open("conf.local.yaml")); m={"MYTECHCONNECT_URL":"mytechconnect_url","MQTT_HOST":"mqtt_host","MQTT_PORT":"mqtt_port","MQTT_USERNAME":"mqtt_username","MQTT_PASSWORD":"mqtt_password","MQTT_DISCOVERY_PREFIX":"mqtt_discovery_prefix","POLL_INTERVAL_SECONDS":"poll_interval_seconds","RESOURCE_METRICS":"resource_metrics","NICE_LEVEL":"nice_level"}; [print(f"export {k}={shlex.quote(str(d[v]))}") for k,v in m.items() if d.get(v) is not None]')"
export PLAYWRIGHT_CHROMIUM=/home/servane/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome
nice -n 10 /tmp/mytechconnect-venv/bin/python tools/mytechconnect_mqtt.py
```

---

## Sécurité & Confidentialité

- **Secrets & Jetons** : Ne jamais versionner l'URL `MYTECHCONNECT_URL`, les cookies, tokens ou identifiants MQTT dans Git.
- **Sanitisation des logs** : Toutes les erreurs Playwright/Python doivent être nettoyées via `sanitize_error()` pour que l'URL de session soit remplacée par `[MYTECHCONNECT_URL_REDACTED]`.
- **Régénération de session** : Toute URL de session ayant été partagée ou exposée doit être immédiatement révoquée/régénérée depuis l'application mobile.
- **Lecture seule absolue** : Aucune commande d'actionnement ne doit être codée, aucun clic sur un bouton d'action PAC ne doit être simulé, aucune écriture Modbus ni publication de topics de commande MQTT.

---

## Vérifications avant modification

Toujours exécuter les vérifications de syntaxe et de compilation suivantes avant de valider des changements :

```bash
/tmp/mytechconnect-venv/bin/python -m py_compile docker/options_env.py tools/mytechconnect_client.py tools/mytechconnect_dump.py tools/mytechconnect_mqtt.py tools/mytechconnect_probe.py
bash -n tools/run_mytechconnect_dump.sh tools/run_mytechconnect_mqtt.sh
bash -n docker/entrypoint.sh
```

Mettre à jour `PLAN.md` lorsque l'architecture, les sensors ou les règles de sécurité évoluent.
