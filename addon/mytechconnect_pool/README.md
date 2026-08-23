# MyTechConnect Pool

Cette app lit l'interface web MyTechConnect en lecture seule avec Chromium
et publie les capteurs dans Home Assistant via MQTT Discovery.

## Installation

1. Dans Home Assistant, ouvrir **Settings → Apps → Install app**.
2. Ouvrir le menu `⋮`, puis **Repositories**.
3. Ajouter le dépôt GitHub personnalisé :
   `https://github.com/jejecool-ui/mytechconnect-homeassistant`.
4. Installer **MyTechConnect Pool** depuis le dépôt.
5. Renseigner l'URL de session MyTechConnect, l'hôte MQTT et les identifiants
   MQTT dans la configuration de l'app.
6. Démarrer l'app et vérifier les entités MQTT Discovery.

L'URL de session et le mot de passe MQTT sont des options masquées et ne sont
pas inclus dans l'image Docker.

## Architecture supportée

L'image publiée est actuellement disponible pour `aarch64` uniquement.
