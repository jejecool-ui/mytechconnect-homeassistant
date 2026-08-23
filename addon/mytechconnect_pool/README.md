# MyTechConnect Pool

This app reads the MyTechConnect web interface in read-only mode with Chromium
and publishes sensors to Home Assistant through MQTT Discovery.

## Installation

1. In Home Assistant, open **Settings → Apps → Install app**.
2. Open the `⋮` menu and select **Repositories**.
3. Add the custom repository:
   `https://github.com/jejecool-ui/mytechconnect-homeassistant`.
4. Install **MyTechConnect Pool** from the repository.
5. Enter the MyTechConnect session URL, MQTT host, and MQTT credentials in the
   app configuration.
6. Start the app and check the MQTT Discovery entities.

The session URL and MQTT password are masked options and are not included in
the Docker image.

## Architecture supportée

L'image publiée est actuellement disponible pour `aarch64` uniquement.
