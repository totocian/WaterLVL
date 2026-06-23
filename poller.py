import logging
import os
import time

from tuya_client import get_device_status, parse_devices_env
from db import insert_reading

logger = logging.getLogger(__name__)


def _pick_value(statuses: list[dict], preferred_code: str | None) -> tuple[str, float] | None:
    """
    Return (code, numeric_value) for the water-level reading.
    If preferred_code is set, use that. Otherwise try common codes,
    then fall back to the first numeric value found.
    """
    index = {s["code"]: s["value"] for s in statuses}

    if preferred_code and preferred_code in index:
        raw = index[preferred_code]
        return preferred_code, _to_float(raw)

    for candidate in ("water_level_percent", "va_humidity", "humidity",
                      "water_level", "level", "percentage"):
        if candidate in index:
            return candidate, _to_float(index[candidate])

    # Log all codes so the user can set WATER_LEVEL_CODE
    logger.info("Available DPS codes: %s", list(index.keys()))
    for code, val in index.items():
        try:
            return code, _to_float(val)
        except (TypeError, ValueError):
            continue
    return None


def _to_float(val) -> float:
    if isinstance(val, bool):
        return float(val)
    if isinstance(val, (int, float)):
        return float(val)
    # Some sensors return strings like "high" / "low" — map to rough %
    mapping = {"empty": 0, "low": 20, "middle": 50, "high": 80, "full": 100}
    if isinstance(val, str) and val.lower() in mapping:
        return float(mapping[val.lower()])
    return float(val)


def poll_once():
    devices = parse_devices_env()
    if not devices:
        logger.warning("No devices configured in DEVICE_IDS")
        return

    preferred_code = os.environ.get("WATER_LEVEL_CODE", "").strip() or None
    ts = int(time.time())

    for device_id, name in devices:
        try:
            statuses = get_device_status(device_id)
            if not statuses:
                continue
            result = _pick_value(statuses, preferred_code)
            if result is None:
                logger.warning("No numeric DPS found for device %s (%s)", device_id, name)
                continue
            code, value = result
            insert_reading(ts, device_id, name, code, value)
            logger.info("Recorded %s (%s): %.2f [%s]", name, device_id, value, code)
        except Exception:
            logger.exception("Error polling device %s (%s)", device_id, name)
