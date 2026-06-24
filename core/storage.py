"""SQLite persistence for CarrierGuard.

Two tables in one DB file:
* ``vetting_records`` — append-only decision trail (the defensibility artifact);
  never updated or deleted.
* ``watchlist`` — carriers the broker is actively using, with their last-known
  state, so Watch mode can detect material changes over time.
"""

from __future__ import annotations

import json
import os
import sqlite3

from core.models import CarrierData, VettingRecord
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

_WATCHLIST_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    mc_number         TEXT PRIMARY KEY,
    legal_name        TEXT,
    authority_status  TEXT,
    insurance_on_file INTEGER,
    safety_rating     TEXT,
    out_of_service    INTEGER,
    last_checked      TEXT
)
"""


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(_SCHEMA)
    conn.execute(_WATCHLIST_SCHEMA)
    return conn


# --- audit log (append-only) -------------------------------------------------

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


# --- watchlist ---------------------------------------------------------------

def add_to_watchlist(mc_number: str, db_path: str) -> None:
    """Add a carrier to the watchlist (no-op if already present). State is
    populated on the next watch run, which becomes the baseline."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (mc_number) VALUES (?)", (str(mc_number),)
        )


def get_watchlist(db_path: str) -> list[dict]:
    """Return all watchlist entries with their last-known state."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT mc_number, legal_name, authority_status, insurance_on_file, "
            "safety_rating, out_of_service, last_checked FROM watchlist"
        ).fetchall()
    return [
        {
            "mc_number": r[0],
            "legal_name": r[1],
            "authority_status": r[2],
            "insurance_on_file": None if r[3] is None else bool(r[3]),
            "safety_rating": r[4],
            "out_of_service": None if r[5] is None else bool(r[5]),
            "last_checked": r[6],
        }
        for r in rows
    ]


def update_watch_state(mc_number: str, carrier: CarrierData, now_iso: str, db_path: str) -> None:
    """Upsert the last-known state for a watched carrier."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO watchlist "
            "(mc_number, legal_name, authority_status, insurance_on_file, safety_rating, out_of_service, last_checked) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(mc_number) DO UPDATE SET "
            "legal_name=excluded.legal_name, authority_status=excluded.authority_status, "
            "insurance_on_file=excluded.insurance_on_file, safety_rating=excluded.safety_rating, "
            "out_of_service=excluded.out_of_service, last_checked=excluded.last_checked",
            (
                str(mc_number),
                carrier.legal_name,
                carrier.authority_status,
                int(carrier.insurance_on_file),
                carrier.safety_rating,
                int(carrier.out_of_service),
                now_iso,
            ),
        )
