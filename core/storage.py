"""Append-only SQLite audit log for vetting records.

Every vetting decision is persisted with its full payload so a broker can later
prove what was checked and when. Records are never updated or deleted here —
the table is insert-only by design (the defensibility trail).
"""

from __future__ import annotations

import json
import sqlite3

from core.models import VettingRecord
from core.record import record_from_dict, record_to_dict

_SCHEMA = """
CREATE TABLE IF NOT EXISTS vetting_records (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mc_number      TEXT,
    checked_at     TEXT,
    decision       TEXT,
    score          INTEGER,
    policy_version TEXT,
    payload        TEXT NOT NULL
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    return conn


def save_record(rec: VettingRecord, db_path: str) -> int:
    """Append a vetting record; return its row id."""
    payload = json.dumps(record_to_dict(rec))
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO vetting_records "
            "(mc_number, checked_at, decision, score, policy_version, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                rec.mc_number,
                rec.checked_at,
                rec.risk.decision.value,
                rec.risk.score,
                rec.policy_version,
                payload,
            ),
        )
        return int(cur.lastrowid)


def get_record(record_id: int, db_path: str) -> VettingRecord:
    """Reconstruct a stored vetting record by id."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT payload FROM vetting_records WHERE id = ?", (record_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"No vetting record with id {record_id}")
    return record_from_dict(json.loads(row[0]))
