"""Build, (de)serialize, and render the dated Carrier Vetting Record.

The VettingRecord is the defensibility artifact: a timestamped account of what
was checked, what was found, and the decision. ``record_to_dict`` /
``record_from_dict`` give a JSON-safe round-trip for the audit log.
"""

from __future__ import annotations

from dataclasses import asdict

from core.models import CarrierData, Decision, FraudSignal, RiskResult, VettingRecord

DISCLAIMER = (
    "This record supports a broker's carrier due-diligence process. "
    "It is informational and is not legal advice."
)


def build_record(
    carrier: CarrierData,
    risk: RiskResult,
    *,
    now_iso: str,
    policy_version: str,
) -> VettingRecord:
    return VettingRecord(
        mc_number=carrier.mc_number,
        checked_at=now_iso,
        carrier=carrier,
        risk=risk,
        policy_version=policy_version,
    )


def record_to_dict(rec: VettingRecord) -> dict:
    """JSON-safe dict (Decision enum -> its string value)."""
    return {
        "mc_number": rec.mc_number,
        "checked_at": rec.checked_at,
        "policy_version": rec.policy_version,
        "carrier": asdict(rec.carrier),
        "risk": {
            "decision": rec.risk.decision.value,
            "score": rec.risk.score,
            "reasons": list(rec.risk.reasons),
            "signals": [
                {"code": s.code, "severity": s.severity, "detail": s.detail}
                for s in rec.risk.signals
            ],
        },
    }


def record_from_dict(d: dict) -> VettingRecord:
    risk = d["risk"]
    return VettingRecord(
        mc_number=d["mc_number"],
        checked_at=d["checked_at"],
        policy_version=d["policy_version"],
        carrier=CarrierData(**d["carrier"]),
        risk=RiskResult(
            decision=Decision(risk["decision"]),
            score=risk["score"],
            reasons=list(risk["reasons"]),
            signals=[FraudSignal(**s) for s in risk["signals"]],
        ),
    )


def render_record(rec: VettingRecord) -> str:
    """Human-readable report (used in agent output and the audit log)."""
    c, r = rec.carrier, rec.risk
    lines = [
        "CARRIER VETTING RECORD",
        f"MC {rec.mc_number or '—'}  |  DOT {c.dot_number or '—'}  |  {rec.checked_at}",
        f"Carrier: {c.legal_name or 'Unknown'}",
        f"Decision: {r.decision.value}   (risk score {r.score}/100, policy {rec.policy_version})",
        "Findings:",
    ]
    if r.signals:
        lines += [f"  - [{s.severity}] {s.detail}" for s in r.signals]
    else:
        lines.append("  - None. Authority active, insurance on file, no adverse flags.")
    lines += ["", DISCLAIMER]
    return "\n".join(lines)
