"""Lightweight analytics via SQLite — tracks embed loads, API usage, etc."""

import os
import sqlite3
import threading
import time

from .config import ANALYTICS_DB_PATH

_local = threading.local()


def _get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(os.path.dirname(ANALYTICS_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(ANALYTICS_DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                event TEXT NOT NULL,
                host TEXT,
                path TEXT,
                extra TEXT
            )
        """)
        conn.commit()
        _local.conn = conn
    return _local.conn


def log_event(event: str, host: str = None, path: str = None, extra: str = None):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO events (ts, event, host, path, extra) VALUES (?, ?, ?, ?, ?)",
        (time.time(), event, host, path, extra),
    )
    conn.commit()


def query_stats(event_type: str = None, since: float = None, limit: int = 100):
    conn = _get_conn()
    sql = "SELECT event, host, path, extra, ts FROM events WHERE 1=1"
    params = []
    if event_type:
        sql += " AND event = ?"
        params.append(event_type)
    if since:
        sql += " AND ts >= ?"
        params.append(since)
    sql += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [
        {"event": r[0], "host": r[1], "path": r[2], "extra": r[3], "ts": r[4]}
        for r in rows
    ]


def count_stats(event_type: str = None, since: float = None):
    conn = _get_conn()
    sql = "SELECT event, COUNT(*) FROM events WHERE 1=1"
    params = []
    if event_type:
        sql += " AND event = ?"
        params.append(event_type)
    if since:
        sql += " AND ts >= ?"
        params.append(since)
    sql += " GROUP BY event ORDER BY COUNT(*) DESC"
    rows = conn.execute(sql, params).fetchall()
    return {r[0]: r[1] for r in rows}
