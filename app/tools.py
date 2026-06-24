"""Deterministic tools the CarrierGuard agent calls.

Risk scoring is policy, not reasoning — so it lives here, computed exactly, not
left to the LLM. The agent fetches data (via the FMCSA MCP tool) and explains
results; `assess_carrier` makes the APPROVE/REVIEW/REJECT call and writes the
audit record.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

from core.fraud import detect_fraud
from core.models import CarrierData
from core.policy import POLICY_VERSION
from core.record import build_record, render_record
from core.scorer import score_signals
from core.storage import save_record

# Append-only audit log location (git-ignored via data/.gitignore).
AUDIT_DB = os.environ.get("CARRIERGUARD_AUDIT_DB", "data/audit.db")


def _carrier_from_dict(d: dict) -> CarrierData:
    """Rebuild CarrierData from the lookup_carrier tool output, defensively.

    The dict arrives via the LLM, so coerce the types we depend on rather than
    trusting them.
    """
    fields = CarrierData.__dataclass_fields__
    kwargs = {k: d.get(k) for k in fields}
    kwargs["mc_number"] = str(kwargs.get("mc_number") or "")
    kwargs["insurance_on_file"] = bool(kwargs.get("insurance_on_file"))
    kwargs["insurance_required"] = (
        True if kwargs.get("insurance_required") is None else bool(kwargs["insurance_required"])
    )
    kwargs["out_of_service"] = bool(kwargs.get("out_of_service"))
    if not isinstance(kwargs.get("raw"), dict):
        kwargs["raw"] = {}
    return CarrierData(**kwargs)


def assess_carrier(carrier: dict, ratecon_name: str = "") -> dict:
    """Assess a carrier's risk and write the decision to the audit log.

    Args:
        carrier: Normalized carrier data, exactly as returned by the
            `lookup_carrier` tool.
        ratecon_name: Optional carrier name from the rate confirmation, used to
            flag a name mismatch (a double-brokering signal).

    Returns:
        A dict with: decision (APPROVE/REVIEW/REJECT), risk_score (0-100),
        findings (list of {severity, detail}), vetting_record (rendered text),
        and audit_record_id.
    """
    carrier_obj = _carrier_from_dict(carrier)
    signals = detect_fraud(carrier_obj, ratecon_name=ratecon_name or None, today=date.today())
    risk = score_signals(signals)
    record = build_record(
        carrier_obj,
        risk,
        now_iso=datetime.now(timezone.utc).isoformat(),
        policy_version=POLICY_VERSION,
    )

    os.makedirs(os.path.dirname(AUDIT_DB) or ".", exist_ok=True)
    record_id = save_record(record, AUDIT_DB)

    return {
        "decision": risk.decision.value,
        "risk_score": risk.score,
        "findings": [{"severity": s.severity, "detail": s.detail} for s in signals],
        "vetting_record": render_record(record),
        "audit_record_id": record_id,
    }
