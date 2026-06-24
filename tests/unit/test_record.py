"""Tests for the vetting record, its serialization, and the audit log."""

from datetime import date

from core.fraud import detect_fraud
from core.models import CarrierData
from core.policy import POLICY_VERSION
from core.record import build_record, record_from_dict, record_to_dict, render_record
from core.scorer import score_signals
from core.storage import get_record, save_record


def _revoked() -> CarrierData:
    return CarrierData(
        mc_number="999999",
        dot_number="3592058",
        legal_name="B SWIFT TRANSPORTATION LLC",
        authority_status="INACTIVE",
        insurance_on_file=False,
        insurance_required=True,
        out_of_service=True,
        safety_rating="SATISFACTORY",
    )


def _record_for(carrier: CarrierData):
    signals = detect_fraud(carrier, today=date(2026, 6, 24))
    risk = score_signals(signals)
    return build_record(carrier, risk, now_iso="2026-06-24T12:00:00Z", policy_version=POLICY_VERSION)


def test_build_record_composes_fields():
    rec = _record_for(_revoked())
    assert rec.mc_number == "999999"
    assert rec.policy_version == POLICY_VERSION
    assert rec.risk.decision.value == "REJECT"  # inactive + OOS + no insurance


def test_render_includes_decision_and_disclaimer():
    text = render_record(_record_for(_revoked()))
    assert "REJECT" in text
    assert "not legal advice" in text.lower()


def test_dict_roundtrip_preserves_signals():
    rec = _record_for(_revoked())
    back = record_from_dict(record_to_dict(rec))
    assert back.mc_number == rec.mc_number
    assert back.risk.decision == rec.risk.decision
    assert [s.code for s in back.risk.signals] == [s.code for s in rec.risk.signals]


def test_audit_log_roundtrip(tmp_path):
    db = str(tmp_path / "audit.db")
    rec = _record_for(_revoked())
    rid = save_record(rec, db)
    got = get_record(rid, db)
    assert got.mc_number == rec.mc_number
    assert got.risk.decision == rec.risk.decision
    assert got.risk.score == rec.risk.score
