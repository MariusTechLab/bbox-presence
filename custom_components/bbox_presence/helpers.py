"""Shared helpers for Bbox Presence entities and configuration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import CONF_TRACKED_MACS


def normalize_mac(value: str) -> str:
    """Return the lower-case colon-separated form used by the Bbox API."""
    compact = "".join(character for character in value.lower() if character.isalnum())
    if len(compact) == 12:
        return ":".join(compact[index : index + 2] for index in range(0, 12, 2))
    return value.strip().lower()


def host_name(mac: str, host: dict[str, Any]) -> str:
    """Return a human-readable name without assuming a device type."""
    return str(host.get("hostname") or host.get("displayname") or mac)


def is_phone(host: dict[str, Any]) -> bool:
    """Return whether the Bbox classifies a host as a phone."""
    information = host.get("informations", {})
    icon = str(information.get("icon", "")).lower()
    device_type = str(information.get("type", "")).lower()
    return icon == "phone" or device_type in {
        "phone",
        "telephone",
        "téléphone",
        "tã©lã©phone",
    }


def tracked_macs(entry: ConfigEntry) -> tuple[str, ...]:
    """Return the configured devices, with options taking precedence over data."""
    configured = entry.options.get(
        CONF_TRACKED_MACS,
        entry.data.get(CONF_TRACKED_MACS, []),
    )
    return tuple(dict.fromkeys(normalize_mac(str(mac)) for mac in configured))
