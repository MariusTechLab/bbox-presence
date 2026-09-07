"""Constants for the Bbox Presence integration."""

from typing import Final

DOMAIN: Final = "bbox_presence"

CONF_HOST: Final = "host"
CONF_PASSWORD: Final = "password"
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_CONSIDER_HOME: Final = "consider_home"
CONF_TRACKED_MACS: Final = "tracked_macs"

DEFAULT_HOST: Final = "mabbox.bytel.fr"
DEFAULT_BBOX_IP: Final = "192.168.1.254"
DEFAULT_SCAN_INTERVAL: Final = 15
DEFAULT_CONSIDER_HOME: Final = 180

API_PATH: Final = "/api/v1/hosts"
LOGIN_PATH: Final = "/api/v1/login"
USER_AGENT: Final = "HomeAssistant-BboxPresence/1.0.0"
