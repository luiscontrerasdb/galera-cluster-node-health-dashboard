import sqlite3
from datetime import datetime

DB_PATH = "auditlog.db"

def init_auditlog():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user TEXT,
                action TEXT,
                detail TEXT,
                ip TEXT
            )
        """)
        conn.commit()

def log_action(user, action, detail, ip):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO audit_log (timestamp, user, action, detail, ip) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(sep=' ', timespec='seconds'), user, action, detail, ip)
        )
        conn.commit()

def get_auditlog(limit=50):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT timestamp, user, action, detail, ip FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return c.fetchall()

