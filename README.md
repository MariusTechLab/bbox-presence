# Bbox Presence for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

"Is anyone home?" from your Bouygues Telecom Bbox, without giving Home
Assistant the router's admin password.

Pick the phones that count, and you get:

- one `device_tracker` per selected device;
- one **house occupancy** `binary_sensor`, on while at least one of them is
  home, ready to use in automations (heating, alarm, lights);
- a **departure delay** you set in the UI, so a phone that sleeps or switches
  between access points for a minute doesn't mark the house as empty.

Everything stays on the local network, with no external library and no cloud.

> This is an independent community project. It is not affiliated with or
> supported by Bouygues Telecom.

## Bbox Presence or hass-bbox2?

[hass-bbox2](https://github.com/Cyr-ius/hass-bbox2) is the full Bbox
integration: traffic sensors, WAN status, Wi-Fi switches, router restart,
phone ring, and trackers for all connected devices. If you want to control the
router, use it.

Bbox Presence only does presence, with a different trade-off:

| | Bbox Presence | hass-bbox2 |
|---|---|---|
| Router admin password | often not needed: asked only if your Bbox requires it | required |
| House occupancy sensor | built in | build your own (group or template) |
| Departure delay | set in the UI | `consider_home`, set by hand |
| Devices tracked | only the ones you select | all connected devices (wired optional) |
| Presence signal | host list and Wi-Fi station tables | host list |
| Router control and traffic sensors | no | yes |
| External dependency | none | `bboxpy` |

Both can run side by side.

## Install in one click

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MariusTechLab&repository=bbox-presence&category=integration)

After downloading and restarting Home Assistant:

[![Open your Home Assistant instance and start setting up Bbox Presence.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=bbox_presence)

Step-by-step instructions are in [Installation](#installation).

## Requirements

- Home Assistant 2026.4 or newer;
- a Bbox exposing the local v1 router API;
- Home Assistant must be able to reach the Bbox on the local network.

Bbox firmware and models differ. Please open an issue with sanitized logs if a
model returns a different API payload. Never include passwords, cookies, public
URLs, or a complete Home Assistant backup in an issue.

## Installation

### HACS (recommended)

1. Use the button above, or add `https://github.com/MariusTechLab/bbox-presence`
   to HACS as a custom repository of type **Integration**.
2. Download **Bbox Presence** and restart Home Assistant.
3. Follow steps 3–7 below.

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
