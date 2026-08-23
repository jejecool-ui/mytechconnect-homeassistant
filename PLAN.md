# Plan d'intégration MyTechConnect dans Home Assistant

## Objectif prioritaire

Obtenir uniquement la température de l'eau en degrés Celsius dans Home Assistant et l'enregistrer afin de l'afficher dans un graphique. La commande de la PAC et les autres paramètres sont secondaires.

## Contrainte matérielle

Aucune modification hardware : ne pas remplacer le boîtier Wi-Fi, ne pas ajouter de liaison RS-485 et ne pas intervenir dans la PAC. La solution devra utiliser le cloud MyTechConnect, l'interface web existante ou un mécanisme logiciel sur le réseau.

## État actuel

- [x] Rechercher une intégration Home Assistant existante.
- [x] Identifier le fonctionnement général de MyTechConnect.
- [x] Télécharger l'archive XAPK MyTechConnect 6.2.
- [x] Extraire l'APK principal et les splits.
- [x] Analyser les permissions, bibliothèques et chaînes de caractères.
- [x] Confirmer la présence de composants Bluetooth/Wi-Fi ESP, MQTT et Modbus.
- [x] Identifier l'interface distante `mytech-connect.user-app.pool.mytech-connect.io`.
- [x] Confirmer que l'interface est une application Blazor Server.
- [x] Identifier le transport SignalR `/_blazor/negotiate` et le protocole `blazorpack`.
- [x] Conserver les artefacts dans `analysis/mytechconnect-6.2/`.

## Prochaine étape : capture du fonctionnement web

- [x] Ouvrir l'URL fournie par l'application avec Chromium headless via Playwright.
- [ ] Ouvrir les outils développeur, onglet **Network/Réseau**.
- [ ] Activer la conservation des requêtes.
- [ ] Recharger la page.
- [ ] Enregistrer une lecture de température ou d'état.
- [ ] Modifier une consigne ou un mode de fonctionnement.
- [ ] Arrêter puis redémarrer la PAC si possible.
- [ ] Exporter les échanges au format HAR.
- [ ] Supprimer du HAR les cookies, jetons, identifiants et URL contenant le jeton de session.
- [ ] Analyser les requêtes SignalR et les trames WebSocket restantes.

## Analyse des messages SignalR

- [ ] Identifier les messages d'initialisation du circuit Blazor.
- [ ] Repérer les événements associés aux boutons et contrôles PAC.
- [ ] Associer chaque action utilisateur à son message serveur.
- [ ] Déterminer si les valeurs PAC sont transmises directement ou via un service cloud intermédiaire.
- [ ] Vérifier la durée de validité des sessions et la possibilité d'un compte dédié Home Assistant.
- [ ] Évaluer la faisabilité d'un client SignalR indépendant.

## Analyse locale Modbus

- [ ] Identifier la marque et le modèle exact de la PAC.
- [ ] Comparer le matériel avec les modèles Polytropic compatibles.
- [ ] Identifier le connecteur et le niveau électrique du bus RS-485/Modbus.
- [ ] Obtenir la table des registres correspondant au modèle exact.
- [ ] Vérifier si le boîtier Wi-Fi actuel est un simple pont Modbus.
- [ ] Tester, sans écrire de registre, la lecture locale avec un adaptateur isolé.
- [ ] Envisager une passerelle ESPHome/RS-485 uniquement après validation du câblage et des registres.

## Décision d'implémentation

- [x] Prioriser une lecture seule de la température d'eau avant toute commande ou écriture.
- [x] Exposer les valeurs avec des noms anglais préfixés par `pool` : `sensor.pool_water_temperature`, `binary_sensor.pool_heat_pump`, `binary_sensor.pool_water_flow`, `sensor.pool_heat_pump_operation_mode`, `sensor.pool_heat_pump_regulation_mode`, `sensor.pool_heat_pump_temperature_setpoint` et `sensor.pool_outdoor_temperature`.
- [ ] Vérifier que l'intégration Recorder de Home Assistant conserve cet historique.
- [ ] Ajouter une carte `history-graph` ou `statistics-graph` dans le dashboard.
- [ ] Capturer l'interface web ou le trafic de l'application pour identifier la source de la température.
- [ ] Choisir l'intégration cloud si une API ou des messages MQTT réutilisables sont trouvés.
- [x] Évaluer puis retenir un petit service logiciel avec navigateur headless qui ouvre l'interface MyTechConnect et publie la température vers MQTT/HA.
- [x] Préparer un probe Playwright Python dans `tools/mytechconnect_probe.py`.
- [x] Créer `tools/mytechconnect_dump.py` pour produire les sensors courants en JSON.
- [x] Factoriser le comportement commun dans `tools/mytechconnect_client.py`.
- [x] Normaliser les températures en nombres JSON et publier `null` lorsque la valeur est indisponible.
- [x] Préparer MQTT Discovery et la publication des états dans `tools/mytechconnect_mqtt.py`.
- [x] Ajouter le lanceur interactif `tools/run_mytechconnect_mqtt.sh`.
- [ ] Installer `paho-mqtt` et tester la publication avec le broker MQTT de Home Assistant.
- [x] Emballer le script et Chromium dans l'add-on Home Assistant.
- [x] Préparer une image Docker ARM64 avec Chromium et un polling toutes les 15 minutes dans `docker/`.
- [x] Préparer la structure de l'add-on Home Assistant dans `addon/mytechconnect_pool/`.
- [x] Lire les options de l'add-on depuis `/data/options.json` sans intégrer les secrets à l'image.
- [x] Ajouter le dépôt d'add-on (`repository.yaml`), sa documentation et la publication GHCR via GitHub Actions.
- [x] Préparer le build ARM64 depuis WSL avec `docker buildx`.
- [x] Activer l'émulation ARM64 via `tonistiigi/binfmt` pour construire depuis l'hôte amd64.
- [x] Terminer et vérifier le build de l'image `mytechconnect-pool:arm64` (`linux/arm64`).
- [x] Installer Playwright et Chromium dans un environnement temporaire WSL (`/tmp/mytechconnect-venv`).
- [ ] Fournir une nouvelle URL de session MyTechConnect au probe.
- [x] Identifier dans le DOM rendu le libellé et la valeur de température d'eau.
- [x] Naviguer automatiquement vers `/heat-pump-chart/<device-id>` sans modification de la PAC.
- [x] Extraire les séries Highcharts et conserver les points horodatés localement dans `analysis/mytechconnect-6.2/browser-probe/chart-data.json`.
- [ ] Capturer proprement la session/circuit pour un lecteur périodique durable.
- [ ] Choisir le pilotage local Modbus si le matériel et la table de registres sont accessibles.
- [ ] Préférer une intégration Home Assistant native ou custom component si l'API est stable.
- [ ] Prévoir des entités pour température d'eau, température extérieure, état, mode, consigne, pompe, alarmes et programmation.
- [ ] Ajouter des garde-fous pour empêcher les écritures dangereuses ou incompatibles avec le modèle.

## Résultat de la sonde web

- La page est une application Blazor Server et la navigation authentifiée fonctionne avec Playwright.
- La vue PAC affiche une température d'eau instantanée ; la vue graphique expose la série `Température d'eau (calculée)`.
- Le graphique contient trois séries et des points espacés d'environ cinq minutes. La série eau est lisible depuis `window.Highcharts.charts`.
- La voie la plus simple sans modification hardware est donc un petit service logiciel navigateur → MQTT ou API REST Home Assistant ; il devra renouveler/réutiliser une session valide.

### Règle de lecture de la température d'eau

- Lire d'abord la température entière affichée dans la vue principale de la PAC.
- Si cette valeur est absente, considérer la température d'eau comme indisponible et ne pas ouvrir la page des graphiques : la valeur estimée du graphique est alors jugée invalide.
- Si la valeur principale existe, le graphique peut éventuellement fournir une précision décimale ; en cas d'échec ou de valeur incohérente, conserver la valeur entière de la page principale.

### Essai de lecture 1

- Configuration : PAC arrêtée, température extérieure annoncée à 41,1 °C, température d'eau annoncée à 26,8 °C.
- Lecture de la page principale : état `OFF`, eau `26 °C`, extérieur `41,1 °C`.
- Les modes et la consigne sont absents lorsque la PAC est arrêtée.
- Aucun accès au graphique n'a été effectué pour cet essai.

### Essai de lecture 2 : comparaison avec le graphique

- Vue principale : PAC `OFF`, eau `26 °C`, température extérieure `42,9 °C` au moment du relevé.
- Graphique : dernière valeur de `Température d'eau (calculée)` à `26,8 °C`.
- Le graphique permet donc de récupérer la décimale lorsque la page principale fournit déjà une température entière ; il ne devra pas être consulté lorsque cette température principale est absente.

### Essai de lecture 3 : PAC en marche

- Vue principale : état `ON`, eau `26 °C`, extérieur `43,9 °C`, consigne `28 °C`.
- Icônes DOM : `heat-pump-mode-heating` et `heat-pump-mode-power-smart`, correspondant respectivement à `heating` et `smart`.
- Le relevé a été réalisé sans ouvrir le graphique.
- Correction : pour le sensor de température d'eau, la valeur précise doit être lue dans le graphique lorsque la valeur entière de la page principale est présente ; ce relevé donne `26,8 °C`.

### Essai de lecture 4 : changement de régulation

- PAC `ON`, fonctionnement `heating`, régulation `eco`, consigne `28 °C`.
- Température d'eau précise du graphique : `26,8 °C`.
- Température extérieure au moment du relevé : `40,7 °C`.

### Essai de lecture 5 : changement de fonctionnement

- PAC `ON`, fonctionnement `auto`, régulation `smart`, consigne `28 °C`.
- Température d'eau précise du graphique : `26,8 °C`.
- Température extérieure au moment du relevé : `40,1 °C`.

### Essai de lecture 6 : PAC arrêtée sans débit

- Vue principale : PAC `OFF`, message `PAS DE DÉBIT D’EAU (VÉRIFIEZ LA POMPE DE CIRCULATION)`.
- Température d'eau : absente, donc `unavailable` ; aucune valeur du graphique ne doit être utilisée.
- Température extérieure : `34,2 °C`.
- Fonctionnement, régulation et consigne : `unavailable`.

### Sensor de débit d'eau

- Entité : `binary_sensor.pool_water_flow`.
- État `ON` : débit d'eau détecté / absence du message d'alarme.
- État `OFF` : la page affiche `PAS DE DÉBIT D’EAU (VÉRIFIEZ LA POMPE DE CIRCULATION)`.
- État `unavailable` : page inaccessible ou état indéterminé.
- Topic d'état MQTT prévu : `mytechconnect/pool/water_flow/state`.

## Déploiement actuel

- Installer le dépôt GitHub comme dépôt personnalisé d'add-ons Home Assistant.
- Utiliser l'add-on `mytechconnect_pool` sur une machine `aarch64`.
- Fournir l'URL de session et les identifiants MQTT dans la configuration de l'add-on.
- Effectuer une lecture toutes les 15 minutes par défaut et publier les valeurs via MQTT Discovery.
- Consulter l'état et les logs depuis le Supervisor Home Assistant.

## Sécurité

- [ ] Ne jamais versionner de jeton, cookie, mot de passe ou HAR non nettoyé.
- [ ] Régénérer le lien de session partagé précédemment.
- [ ] Ne pas tester d'écritures Modbus avant validation du modèle et des registres.
