import logging
import os
import time

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

from db import init_db, list_devices, query_readings
from poller import poll_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/tank/<device_id>")
def tank_detail(device_id):
    devices = list_devices()
    device = next((d for d in devices if d["device_id"] == device_id), None)
    if device is None:
        return "Device not found", 404
    return render_template("tank.html", device_id=device_id, name=device["name"])


@app.route("/api/devices")
def api_devices():
    return jsonify(list_devices())


@app.route("/api/readings")
def api_readings():
    """
    Query params:
      device_ids  comma-separated list (optional, defaults to all)
      range       "1h" | "6h" | "24h" | "7d" | "30d" | "all"  (default: "24h")
    """
    raw_ids = request.args.get("device_ids", "")
    device_ids = [d.strip() for d in raw_ids.split(",") if d.strip()] or None

    range_map = {
        "1h":  3600,
        "6h":  21600,
        "24h": 86400,
        "7d":  604800,
        "30d": 2592000,
    }
    range_key = request.args.get("range", "24h")
    now = int(time.time())
    since = 0 if range_key == "all" else now - range_map.get(range_key, 86400)

    rows = query_readings(device_ids, since, now)
    return jsonify(rows)


@app.route("/api/poll", methods=["POST"])
def api_poll():
    """Trigger a manual poll."""
    try:
        poll_once()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

def start_scheduler():
    interval = int(os.environ.get("POLL_INTERVAL", 300))
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_once, "interval", seconds=interval, id="poll",
                      next_run_time=__import__("datetime").datetime.now())
    scheduler.start()
    logger.info("Scheduler started — polling every %ds", interval)
    return scheduler


if __name__ == "__main__":
    init_db()
    scheduler = start_scheduler()
    port = int(os.environ.get("FLASK_PORT", 5000))
    try:
        app.run(host="0.0.0.0", port=port, debug=False)
    finally:
        scheduler.shutdown()
