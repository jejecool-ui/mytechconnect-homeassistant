# MyTechConnect Pool

Cet add-on lit l'interface web MyTechConnect en lecture seule avec Chromium
et publie les capteurs dans Home Assistant via MQTT Discovery.

## Installation

1. Ajouter le dépôt GitHub personnalisé :
   `https://github.com/jejecool-ui/mytechconnect-homeassistant`.
2. Installer **MyTechConnect Pool** depuis le dépôt.
3. Renseigner l'URL de session MyTechConnect, l'hôte MQTT et les identifiants
   MQTT dans la configuration de l'add-on.
4. Démarrer l'add-on et vérifier les entités MQTT Discovery.

L'URL de session et le mot de passe MQTT sont des options masquées et ne sont
pas inclus dans l'image Docker.

## Architecture supportée

L'image publiée est actuellement disponible pour `aarch64` uniquement.
