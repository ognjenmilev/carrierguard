"""Tests for the CarrierGuard core data models."""

from core.models import CarrierData, Decision, FraudSignal, RiskResult, VettingRecord


def test_carrierdata_requires_only_mc_and_has_safe_defaults():
    c = CarrierData(mc_number="123456")
    assert c.mc_number == "123456"
    # Safe defaults: assume not-insured / authority-required until proven otherwise.
    assert c.insurance_on_file is False
    assert c.insurance_required is True
    assert c.out_of_service is False
    assert c.raw == {}


def test_decision_enum_values():
    assert Decision.APPROVE.value == "APPROVE"
    assert Decision.REVIEW.value == "REVIEW"
    assert Decision.REJECT.value == "REJECT"


def test_fraud_signal_holds_code_severity_detail():
    s = FraudSignal(code="AUTHORITY_REVOKED", severity="HIGH", detail="Authority is revoked")
    assert s.code == "AUTHORITY_REVOKED"
    assert s.severity == "HIGH"
    assert "revoked" in s.detail


def test_risk_result_defaults_to_empty_lists():
    r = RiskResult(decision=Decision.APPROVE, score=0)
    assert r.reasons == []
    assert r.signals == []


def test_vetting_record_composes_carrier_and_risk():
    carrier = CarrierData(mc_number="123456", legal_name="ACME TRUCKING LLC")
    risk = RiskResult(decision=Decision.REJECT, score=50, reasons=["revoked"])
    rec = VettingRecord(
        mc_number="123456",
        checked_at="2026-06-24T12:00:00Z",
        carrier=carrier,
        risk=risk,
        policy_version="v1",
    )
    assert rec.mc_number == "123456"
    assert rec.carrier.legal_name == "ACME TRUCKING LLC"
    assert rec.risk.decision is Decision.REJECT
