"""Tests for the fraud/risk heuristics (pure, offline)."""

from datetime import date

from core.fraud import detect_fraud
from core.models import CarrierData

TODAY = date(2026, 6, 24)


def _codes(signals):
    return {s.code for s in signals}


def _clean() -> CarrierData:
    return CarrierData(
        mc_number="107478",
        legal_name="OLD DOMINION FREIGHT LINE INC",
        authority_status="ACTIVE",
        insurance_on_file=True,
        insurance_required=True,
        safety_rating="SATISFACTORY",
        out_of_service=False,
        authority_granted_date="2010-01-01",
        physical_address="500 OLD DOMINION WAY, THOMASVILLE, NC 27360",
    )


def test_clean_carrier_has_no_signals():
    assert detect_fraud(_clean(), ratecon_name="Old Dominion Freight Line", today=TODAY) == []


def test_inactive_authority_is_high():
    c = _clean()
    c.authority_status = "INACTIVE"
    assert "AUTHORITY_INACTIVE" in _codes(detect_fraud(c, today=TODAY))


def test_out_of_service_is_high():
    c = _clean()
    c.out_of_service = True
    assert "OUT_OF_SERVICE" in _codes(detect_fraud(c, today=TODAY))


def test_missing_required_insurance_is_high():
    c = _clean()
    c.insurance_on_file = False
    assert "NO_INSURANCE" in _codes(detect_fraud(c, today=TODAY))


def test_unsatisfactory_safety_is_high():
    c = _clean()
    c.safety_rating = "UNSATISFACTORY"
    assert "UNSATISFACTORY_SAFETY" in _codes(detect_fraud(c, today=TODAY))


def test_brand_new_authority_flags_double_broker_risk():
    c = _clean()
    c.authority_granted_date = "2026-05-20"  # ~35 days before TODAY
    assert "AUTHORITY_TOO_NEW" in _codes(detect_fraud(c, today=TODAY))


def test_name_mismatch_is_high():
    c = _clean()
    sigs = detect_fraud(c, ratecon_name="Speedy Freight Inc", today=TODAY)
    assert "NAME_MISMATCH" in _codes(sigs)


def test_cmra_address_is_medium():
    c = _clean()
    c.physical_address = "1234 MAIN ST, THE UPS STORE #221, MIAMI, FL"
    assert "ADDRESS_CMRA" in _codes(detect_fraud(c, today=TODAY))
