"""Watch mode: re-check watched carriers and alert on material changes.

A broker books with a carrier today; weeks later that carrier's authority gets
revoked or its insurance lapses. Watch mode re-pulls each watched carrier on a
schedule and flags the moment something turns bad — the thing a one-shot prompt
can never do.

Run it as a scheduled job:  ``python -m core.watch``
Add carriers:               ``python -m core.watch add 107478 1217040``
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from core import storage
from core.fmcsa.client import fetch_carrier
from core.models import CarrierData

AUDIT_DB = os.environ.get("CARRIERGUARD_AUDIT_DB", "data/audit.db")
_SAFETY_RANK = {"SATISFACTORY": 0, "CONDITIONAL": 1, "UNSATISFACTORY": 2}


@dataclass
class Alert:
    mc_number: str
    legal_name: str | None
    change_code: str
    detail: str


def _diff(prev: dict, cur: CarrierData) -> list[Alert]:
    """Material, worsening changes between the last-known state and now."""
    mc = cur.mc_number or prev.get("mc_number", "")
    name = cur.legal_name or prev.get("legal_name")
    alerts: list[Alert] = []

    if prev.get("authority_status") == "ACTIVE" and (cur.authority_status or "").upper() != "ACTIVE":
        alerts.append(Alert(mc, name, "AUTHORITY_LOST",
                            f"Operating authority changed: {prev.get('authority_status')} -> {cur.authority_status}."))
    if prev.get("insurance_on_file") and not cur.insurance_on_file:
        alerts.append(Alert(mc, name, "INSURANCE_LAPSED", "BIPD insurance is no longer on file."))
    if not prev.get("out_of_service") and cur.out_of_service:
        alerts.append(Alert(mc, name, "OUT_OF_SERVICE", "Carrier was placed out of service."))

    pv = _SAFETY_RANK.get(prev.get("safety_rating"))
    cv = _SAFETY_RANK.get((cur.safety_rating or "").upper())
    if pv is not None and cv is not None and cv > pv:
        alerts.append(Alert(mc, name, "SAFETY_DOWNGRADE",
                            f"Safety rating worsened: {prev.get('safety_rating')} -> {cur.safety_rating}."))
    return alerts


def run_watch(db_path: str = AUDIT_DB, *, fetch=fetch_carrier, now_iso: str | None = None) -> list[Alert]:
    """Re-check every watched carrier; return alerts for material changes.

    The first time a carrier is seen, its state is recorded as the baseline (no
    alert). ``fetch`` is injectable so tests run without the network.
    """
    now_iso = now_iso or datetime.now(timezone.utc).isoformat()
    alerts: list[Alert] = []
    for entry in storage.get_watchlist(db_path):
        mc = entry["mc_number"]
        try:
            cur = fetch(mc)
        except Exception as exc:  # noqa: BLE001 - one bad lookup shouldn't abort the run
            alerts.append(Alert(mc, entry.get("legal_name"), "LOOKUP_FAILED",
                                f"Could not re-check carrier: {exc}"))
            continue
        if entry.get("last_checked"):  # baseline exists -> compare
            alerts.extend(_diff(entry, cur))
        storage.update_watch_state(mc, cur, now_iso, db_path)
    return alerts


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:  # noqa: BLE001
        pass

    if argv and argv[0] == "add":
        for mc in argv[1:]:
            storage.add_to_watchlist(mc, AUDIT_DB)
            print(f"added MC {mc} to watchlist")
        return 0

    alerts = run_watch(AUDIT_DB)
    if not alerts:
        print("Watch run complete: no material changes.")
        return 0
    print(f"Watch run complete: {len(alerts)} alert(s):")
    for a in alerts:
        print(f"  [{a.change_code}] MC {a.mc_number} ({a.legal_name or 'Unknown'}): {a.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
