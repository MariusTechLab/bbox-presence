"""Selected-device trackers for Bbox Presence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, override

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME, DOMAIN
from .coordinator import BboxPresenceCoordinator
from .helpers import host_name, tracked_macs


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one tracker for every selected Bbox device."""
    coordinator: BboxPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]
    hosts = coordinator.data.get("hosts", {})
    async_add_entities(
        BboxDeviceTracker(entry, coordinator, mac, hosts.get(mac, {}))
        for mac in tracked_macs(entry)
    )


class BboxDeviceTracker(
    CoordinatorEntity[BboxPresenceCoordinator],
    ScannerEntity,
):
    """Represent a selected device seen by the Bbox."""

    _attr_icon = "mdi:wifi-marker"

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: BboxPresenceCoordinator,
        mac: str,
        initial_host: dict[str, Any],
    ) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"bbox_presence_{mac.replace(':', '')}"
        self._attr_name = host_name(mac, initial_host)
        consider_home = entry.options.get(
            CONF_CONSIDER_HOME,
            entry.data.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
        )
        self._consider_home_interval = timedelta(seconds=int(consider_home))
        self._last_seen: datetime | None = (
            dt_util.utcnow() if self._raw_connected else None
        )

    @property
    def _hosts(self) -> dict[str, dict[str, Any]]:
        return self.coordinator.data.get("hosts", {})

    @property
    def _wireless_macs(self) -> set[str]:
        return self.coordinator.data.get("wireless_macs", set())

    @property
    def _host(self) -> dict[str, Any]:
        return self._hosts.get(self._mac, {})

    @property
    def _bbox_active(self) -> bool:
        return self._host.get("active") == 1

    @property
    def _wifi_station_present(self) -> bool:
        return self._mac in self._wireless_macs

    @property
    def _raw_connected(self) -> bool:
        return self._bbox_active or self._wifi_station_present

    @property
    @override
    def mac_address(self) -> str:
        return self._mac

    @property
    @override
    def ip_address(self) -> str | None:
        return self._host.get("ipaddress")

    @property
    @override
    def hostname(self) -> str | None:
        return self._host.get("hostname") or self._attr_name

    @property
    @override
    def is_connected(self) -> bool:
        if self._raw_connected:
            self._last_seen = dt_util.utcnow()
            return True
        return bool(
            self._last_seen is not None
            and (dt_util.utcnow() - self._last_seen) < self._consider_home_interval
        )

    @property
    @override
    def entity_registry_enabled_default(self) -> bool:
        return True

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        information = self._host.get("informations", {})
        wireless = self._host.get("wireless", {})
        rssi = wireless.get("rssi0")
        try:
            rssi = int(rssi) if rssi not in (None, "") else None
        except (TypeError, ValueError):
            pass

        return {
            "bbox_active": self._bbox_active,
            "wifi_station_present": self._wifi_station_present,
            "raw_presence": self._raw_connected,
            "link": self._host.get("link"),
            "rssi": rssi,
            "manufacturer": information.get("manufacturer") or None,
            "model": information.get("model") or None,
            "operating_system": information.get("operatingSystem") or None,
        }
