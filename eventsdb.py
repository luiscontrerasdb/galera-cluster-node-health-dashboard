import sqlite3
from datetime import datetime

def create_events_db():
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS node_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            node_label TEXT,
            event TEXT,
            timestamp DATETIME,
            downtime_sec INTEGER DEFAULT NULL
        )
    """)
    conn.commit()
    conn.close()

def log_node_event(node_id, node_label, event, downtime_sec=None):
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
    c.execute("INSERT INTO node_events (node_id, node_label, event, timestamp, downtime_sec) VALUES (?, ?, ?, ?, ?)",
              (node_id, node_label, event, datetime.now(), downtime_sec))
    conn.commit()
    conn.close()

def get_last_event(node_id):
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
    c.execute("SELECT event, timestamp FROM node_events WHERE node_id=? ORDER BY id DESC LIMIT 1", (node_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def get_down_events(limit=50):
    conn = sqlite3.connect("events.db")
    c = conn.cursor()
    c.execute("SELECT node_id, node_label, event, timestamp, downtime_sec FROM node_events ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

