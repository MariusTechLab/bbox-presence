"""Config and options flows for Bbox Presence."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BboxApi, BboxApiError, BboxAuthRequired
from .const import (
    CONF_CONSIDER_HOME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TRACKED_MACS,
    DEFAULT_CONSIDER_HOME,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .helpers import host_name, is_phone, normalize_mac, tracked_macs


def _device_options(
    hosts: dict[str, dict[str, Any]],
    include_macs: tuple[str, ...] = (),
) -> list[selector.SelectOptionDict]:
    """Build stable, descriptive options for the device selector."""
    options: list[selector.SelectOptionDict] = []
    all_macs = set(hosts) | set(include_macs)
    for mac in sorted(all_macs, key=lambda item: host_name(item, hosts.get(item, {}))):
        host = hosts.get(mac, {})
        name = host_name(mac, host)
        ip_address = host.get("ipaddress")
        details = f" — {ip_address}" if ip_address else ""
        options.append({"label": f"{name}{details} ({mac})", "value": mac})
    return options


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=defaults.get(CONF_HOST, DEFAULT_HOST),
            ): str,
            vol.Optional(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
            vol.Required(
                CONF_CONSIDER_HOME,
                default=defaults.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1800)),
        }
    )


class BboxPresenceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Bbox Presence."""

    VERSION = 2

    def __init__(self) -> None:
        self._connection_data: dict[str, Any] = {}
        self._hosts: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Validate the connection details."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = BboxApi.clean_host(str(user_input[CONF_HOST]))
            password = str(user_input.get(CONF_PASSWORD, "") or "")
            api = BboxApi(async_get_clientsession(self.hass), host, password)

            try:
                data = await api.async_get_presence_data()
            except BboxAuthRequired:
                errors["base"] = "auth_required"
            except BboxApiError:
                errors["base"] = "cannot_connect"
            else:
                if not data["hosts"]:
                    errors["base"] = "no_hosts"
                else:
                    self._connection_data = dict(user_input)
                    self._connection_data[CONF_HOST] = host
                    if not password:
                        self._connection_data.pop(CONF_PASSWORD, None)
                    self._hosts = data["hosts"]
                    return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Select the devices that contribute to occupancy."""
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = [normalize_mac(mac) for mac in user_input[CONF_TRACKED_MACS]]
            if not selected:
                errors["base"] = "no_devices_selected"
            else:
                data = dict(self._connection_data)
                data[CONF_TRACKED_MACS] = selected
                return self.async_create_entry(title="Bbox Presence", data=data)

        defaults = [mac for mac, host in self._hosts.items() if is_phone(host)]
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TRACKED_MACS,
                    default=defaults,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_device_options(self._hosts),
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id="devices",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BboxPresenceOptionsFlow:
        """Create the options flow."""
        return BboxPresenceOptionsFlow()


class BboxPresenceOptionsFlow(config_entries.OptionsFlowWithReload):
    """Change polling, departure delay, and tracked devices."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage Bbox Presence options."""
        errors: dict[str, str] = {}
        selected = tracked_macs(self.config_entry)
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        hosts = coordinator.data.get("hosts", {}) if coordinator else {}

        if user_input is not None:
            configured = [normalize_mac(mac) for mac in user_input[CONF_TRACKED_MACS]]
            if not configured:
                errors["base"] = "no_devices_selected"
            else:
                user_input[CONF_TRACKED_MACS] = configured
                return self.async_create_entry(data=user_input)

        current = {
            CONF_SCAN_INTERVAL: self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ),
            CONF_CONSIDER_HOME: self.config_entry.options.get(
                CONF_CONSIDER_HOME,
                self.config_entry.data.get(CONF_CONSIDER_HOME, DEFAULT_CONSIDER_HOME),
            ),
            CONF_TRACKED_MACS: list(selected),
        }
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=current[CONF_SCAN_INTERVAL],
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                vol.Required(
                    CONF_CONSIDER_HOME,
                    default=current[CONF_CONSIDER_HOME],
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1800)),
                vol.Required(
                    CONF_TRACKED_MACS,
                    default=current[CONF_TRACKED_MACS],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=_device_options(hosts, selected),
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
