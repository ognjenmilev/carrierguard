"""Tests for Watch mode change detection (offline, injected fetch)."""

from core import storage
from core.models import CarrierData
from core.watch import run_watch


def _carrier(**overrides) -> CarrierData:
    base = dict(
        mc_number="55",
        legal_name="ACME TRUCKING LLC",
        authority_status="ACTIVE",
        insurance_on_file=True,
        insurance_required=True,
        safety_rating="SATISFACTORY",
        out_of_service=False,
    )
    base.update(overrides)
    return CarrierData(**base)


def _prime_baseline(db: str, carrier: CarrierData) -> None:
    storage.add_to_watchlist("55", db)
    run_watch(db, fetch=lambda mc: carrier, now_iso="t1")  # records baseline, no alerts


def test_first_run_sets_baseline_without_alerting(tmp_path):
    db = str(tmp_path / "a.db")
    storage.add_to_watchlist("55", db)
    # Even a bad carrier on the very first run is just the baseline.
    alerts = run_watch(db, fetch=lambda mc: _carrier(authority_status="INACTIVE"), now_iso="t1")
    assert alerts == []


def test_no_change_no_alerts(tmp_path):
    db = str(tmp_path / "a.db")
    good = _carrier()
    _prime_baseline(db, good)
    assert run_watch(db, fetch=lambda mc: good, now_iso="t2") == []


def test_authority_loss_alerts(tmp_path):
    db = str(tmp_path / "a.db")
    _prime_baseline(db, _carrier())
    alerts = run_watch(db, fetch=lambda mc: _carrier(authority_status="INACTIVE"), now_iso="t2")
    assert [a.change_code for a in alerts] == ["AUTHORITY_LOST"]


def test_insurance_lapse_alerts(tmp_path):
    db = str(tmp_path / "a.db")
    _prime_baseline(db, _carrier())
    alerts = run_watch(db, fetch=lambda mc: _carrier(insurance_on_file=False), now_iso="t2")
    assert any(a.change_code == "INSURANCE_LAPSED" for a in alerts)


def test_out_of_service_alerts(tmp_path):
    db = str(tmp_path / "a.db")
    _prime_baseline(db, _carrier())
    alerts = run_watch(db, fetch=lambda mc: _carrier(out_of_service=True), now_iso="t2")
    assert any(a.change_code == "OUT_OF_SERVICE" for a in alerts)


def test_safety_downgrade_alerts(tmp_path):
    db = str(tmp_path / "a.db")
    _prime_baseline(db, _carrier())
    alerts = run_watch(db, fetch=lambda mc: _carrier(safety_rating="CONDITIONAL"), now_iso="t2")
    assert any(a.change_code == "SAFETY_DOWNGRADE" for a in alerts)
