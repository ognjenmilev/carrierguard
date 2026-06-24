"""Tests for the FMCSA client's parse layer.

Runs fully offline against recorded real QCMobile responses (fixtures), so it
needs no network and no WebKey.
"""

import json
import pathlib

from core.fmcsa.client import parse_carrier
from core.models import CarrierData

FIX = pathlib.Path(__file__).resolve().parents[2] / "core" / "fmcsa" / "fixtures"


def _payload(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def test_parse_active_carrier():
    c = parse_carrier(_payload("active_carrier.json"))
    assert isinstance(c, CarrierData)
    assert c.legal_name == "OLD DOMINION FREIGHT LINE INC"
    assert c.authority_status == "ACTIVE"        # allowedToOperate == "Y"
    assert c.insurance_on_file is True           # bipdInsuranceOnFile "1000"
    assert c.out_of_service is False             # oosDate null
    assert c.safety_rating == "SATISFACTORY"     # code "S"
    assert c.dot_number == "90849"


def test_parse_revoked_carrier():
    c = parse_carrier(_payload("revoked_carrier.json"))
    assert c.legal_name == "B SWIFT TRANSPORTATION LLC"
    assert c.authority_status == "INACTIVE"      # allowedToOperate == "N"
    assert c.insurance_on_file is False          # bipdInsuranceOnFile "0"
    assert c.out_of_service is True              # oosDate "2021-11-30"


def test_parse_passes_through_mc_number():
    c = parse_carrier(_payload("active_carrier.json"), mc_number="123456")
    assert c.mc_number == "123456"


def test_parse_retains_raw_payload_for_audit():
    c = parse_carrier(_payload("active_carrier.json"))
    assert c.raw.get("dotNumber") == 90849       # raw carrier dict kept for the audit trail
