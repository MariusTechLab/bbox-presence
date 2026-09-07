"""House occupancy binary sensor for Bbox Presence."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, override

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the occupancy sensor."""
    coordinator: BboxPresenceCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BboxHouseOccupancy(entry, coordinator)])


class BboxHouseOccupancy(
    CoordinatorEntity[BboxPresenceCoordinator],
    BinarySensorEntity,
):
    """Report occupancy when at least one selected device is present."""

    _attr_has_entity_name = True
    _attr_translation_key = "house_occupancy"
    _attr_icon = "mdi:home-account"
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    def __init__(
        self,
        entry: ConfigEntry,
        coordinator: BboxPresenceCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_house_occupancy"
        self._tracked_macs = tracked_macs(entry)
        consider_home = entry.options.get(
            CONF_CONSIDER_HOME,
            entry.data.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
        )
        self._consider_home_interval = timedelta(seconds=int(consider_home))
        self._last_seen_by_mac: dict[str, datetime] = {}

        now = dt_util.utcnow()
        for mac in self._tracked_macs:
            if self._raw_connected(mac):
                self._last_seen_by_mac[mac] = now

    @property
    def _hosts(self) -> dict[str, dict[str, Any]]:
        return self.coordinator.data.get("hosts", {})

    @property
    def _wireless_macs(self) -> set[str]:
        return self.coordinator.data.get("wireless_macs", set())

    def _raw_connected(self, mac: str) -> bool:
        host = self._hosts.get(mac, {})
        return host.get("active") == 1 or mac in self._wireless_macs

    def _device_is_home(self, mac: str, now: datetime) -> bool:
        if self._raw_connected(mac):
            self._last_seen_by_mac[mac] = now
            return True
        last_seen = self._last_seen_by_mac.get(mac)
        return bool(
            last_seen is not None and (now - last_seen) < self._consider_home_interval
        )

    def _presence_snapshot(self) -> tuple[list[str], list[str]]:
        now = dt_util.utcnow()
        present: list[str] = []
        raw_present: list[str] = []

        for mac in self._tracked_macs:
            name = host_name(mac, self._hosts.get(mac, {}))
            if self._raw_connected(mac):
                raw_present.append(name)
            if self._device_is_home(mac, now):
                present.append(name)

        return present, raw_present

    @property
    @override
    def is_on(self) -> bool:
        present, _ = self._presence_snapshot()
        return bool(present)

    @property
    @override
    def extra_state_attributes(self) -> dict[str, Any]:
        present, raw_present = self._presence_snapshot()
        return {
            "present_devices": present,
            "present_count": len(present),
            "raw_present_devices": raw_present,
            "tracked_count": len(self._tracked_macs),
            "away_delay_seconds": int(self._consider_home_interval.total_seconds()),
            "uses_dual_presence_source": True,
        }
