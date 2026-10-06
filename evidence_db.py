import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "evidence.db"


def get_conn(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path=DB_PATH):
    conn = get_conn(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            text TEXT,
            origin TEXT,
            retrieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
            quarantined INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            source_ids TEXT NOT NULL,
            status TEXT DEFAULT 'unchecked'
        );
    """)
    conn.commit()
    conn.close()


def add_source(url, title, text, origin, path=DB_PATH) -> int:
    conn = get_conn(path)
    conn.execute(
        "INSERT OR IGNORE INTO sources (url, title, text, origin) VALUES (?, ?, ?, ?)",
        (url, title, text, origin),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM sources WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row["id"]


def get_source(source_id, path=DB_PATH):
    conn = get_conn(path)
    row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def quarantine_source(source_id, path=DB_PATH):
    conn = get_conn(path)
    conn.execute("UPDATE sources SET quarantined = 1 WHERE id = ?", (source_id,))
    conn.commit()
    conn.close()


def add_claim(text, source_ids, path=DB_PATH) -> int:
    conn = get_conn(path)
    cur = conn.execute(
        "INSERT INTO claims (text, source_ids) VALUES (?, ?)",
        (text, json.dumps(source_ids)),
    )
    conn.commit()
    claim_id = cur.lastrowid
    conn.close()
    return claim_id


def set_claim_status(claim_id, status, path=DB_PATH):
    assert status in ("unchecked", "supported", "partial", "unsupported")
    conn = get_conn(path)
    conn.execute("UPDATE claims SET status = ? WHERE id = ?", (status, claim_id))
    conn.commit()
    conn.close()


def get_claims(status=None, path=DB_PATH):
    conn = get_conn(path)
    if status:
        rows = conn.execute("SELECT * FROM claims WHERE status = ?", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM claims").fetchall()
    conn.close()
    out = []
    for r in rows:
        d = dict(r)
        d["source_ids"] = json.loads(d["source_ids"])
        out.append(d)
    return out