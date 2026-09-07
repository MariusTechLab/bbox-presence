"""Data update coordinator for Bbox Presence."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BboxApi, BboxApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class BboxPresenceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the Bbox hosts endpoint."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: BboxApi,
        scan_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_presence_data()
        except BboxApiError as err:
            raise UpdateFailed(f"Bbox API error: {err}") from err
