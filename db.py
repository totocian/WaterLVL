import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "waterlvl.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                name      TEXT NOT NULL,
                code      TEXT NOT NULL,
                value     REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON readings(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_device ON readings(device_id, ts)")
        conn.commit()


def insert_reading(ts: int, device_id: str, name: str, code: str, value: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO readings (ts, device_id, name, code, value) VALUES (?,?,?,?,?)",
            (ts, device_id, name, code, value),
        )
        conn.commit()


def query_readings(device_ids: list[str] | None, since_ts: int, until_ts: int):
    with get_conn() as conn:
        if device_ids:
            placeholders = ",".join("?" * len(device_ids))
            rows = conn.execute(
                f"SELECT ts, device_id, name, value FROM readings "
                f"WHERE device_id IN ({placeholders}) AND ts BETWEEN ? AND ? "
                f"ORDER BY ts",
                (*device_ids, since_ts, until_ts),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT ts, device_id, name, value FROM readings "
                "WHERE ts BETWEEN ? AND ? ORDER BY ts",
                (since_ts, until_ts),
            ).fetchall()
    return [dict(r) for r in rows]


def get_recent_values(device_id: str, limit: int = 5) -> list[float]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT value FROM readings WHERE device_id = ? ORDER BY ts DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
    return [r["value"] for r in rows]


def list_devices():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT device_id, name FROM readings ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]
