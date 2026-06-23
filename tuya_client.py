import logging
import os
from tuya_connector import TuyaOpenAPI

logger = logging.getLogger(__name__)

_api: TuyaOpenAPI | None = None


def get_api() -> TuyaOpenAPI:
    global _api
    if _api is None:
        endpoint = os.environ["TUYA_API_ENDPOINT"]
        access_id = os.environ["TUYA_ACCESS_ID"]
        access_secret = os.environ["TUYA_ACCESS_SECRET"]
        _api = TuyaOpenAPI(endpoint, access_id, access_secret)
        _api.connect()
        logger.info("Connected to Tuya API at %s", endpoint)
    return _api


def get_device_status(device_id: str) -> list[dict]:
    """Return list of {code, value} dicts for a device."""
    api = get_api()
    resp = api.get(f"/v1.0/devices/{device_id}/status")
    if not resp.get("success"):
        logger.warning("Tuya API error for %s: %s", device_id, resp)
        return []
    return resp.get("result", [])


def parse_devices_env() -> list[tuple[str, str]]:
    """Parse DEVICE_IDS env var into [(device_id, name), ...]."""
    raw = os.environ.get("DEVICE_IDS", "")
    devices = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        if ":" in entry:
            did, name = entry.split(":", 1)
        else:
            did, name = entry, entry
        devices.append((did.strip(), name.strip()))
    return devices
