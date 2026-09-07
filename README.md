# Bbox Presence for Home Assistant

Local presence detection for Bouygues Telecom Bbox routers. The integration
polls the router's local `/api/v1/hosts` endpoint and creates:

- one `device_tracker` per device selected during setup;
- one occupancy `binary_sensor` that is on when at least one selected device
  is home.

Presence is checked against both the general Bbox host list and the Wi-Fi
station tables. A configurable departure delay reduces false absences when a
phone briefly sleeps or roams between access points.

> This is an independent community project. It is not affiliated with or
> supported by Bouygues Telecom.

## Requirements

- Home Assistant 2026.4 or newer;
- a Bbox exposing the local v1 router API;
- Home Assistant must be able to reach the Bbox on the local network.

Bbox firmware and models differ. Please open an issue with sanitized logs if a
model returns a different API payload. Never include passwords, cookies, public
URLs, or a complete Home Assistant backup in an issue.

## Installation

### Manual

1. Copy `custom_components/bbox_presence` to your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**.
4. Search for **Bbox Presence**.
5. Keep `mabbox.bytel.fr` unless your network requires a specific local IP.
6. Try without a password first. Enter the Bbox administrator password only if
   the integration reports that authentication is required.
7. Select the devices that should count toward occupancy.

### HACS custom repository

Add `https://github.com/MariusTechLab/bbox-presence` to HACS as an
**Integration**, install it, restart Home Assistant, and then follow steps 3–7
above.

## Options

The integration options let you change:

- the polling interval (5–300 seconds);
- the delay before a disconnected device becomes away (0–1800 seconds);
- the devices used for occupancy.

Changing an option reloads the integration automatically.

## Privacy and security

- All API traffic stays on the local network.
- No telemetry or cloud service is used.
- The optional administrator password is stored in Home Assistant's config
  entry storage. Do not commit `.storage`, `secrets.yaml`, backups, logs, or
  diagnostics without reviewing and redacting them.
- Response bodies are deliberately excluded from error messages because router
  payloads may contain device names, IP addresses, and MAC addresses.

## How occupancy is calculated

A selected device is present when either:

1. the Bbox host list reports `active: 1`; or
2. its MAC address appears in a Wi-Fi station table.

When both signals disappear, the configured departure delay starts. The house
occupancy sensor turns off only after every selected device has exceeded that
delay.

## License

MIT
