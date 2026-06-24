"""Tests for the policy-driven risk scorer (pure, offline)."""

from core.models import Decision, FraudSignal
from core.scorer import score_signals


def _sig(severity, code="X"):
    return FraudSignal(code, severity, f"{severity} issue")


def test_no_signals_approves():
    r = score_signals([])
    assert r.decision == Decision.APPROVE
    assert r.score == 0


def test_single_high_rejects():
    r = score_signals([_sig("HIGH")])
    assert r.decision == Decision.REJECT
    assert r.score == 50


def test_single_medium_reviews():
    r = score_signals([_sig("MEDIUM")])
    assert r.decision == Decision.REVIEW
    assert r.score == 20


def test_two_mediums_still_review():
    r = score_signals([_sig("MEDIUM"), _sig("MEDIUM")])
    assert r.score == 40
    assert r.decision == Decision.REVIEW


def test_three_mediums_reject_on_score():
    r = score_signals([_sig("MEDIUM"), _sig("MEDIUM"), _sig("MEDIUM")])
    assert r.score == 60
    assert r.decision == Decision.REJECT


def test_signals_and_reasons_carried_through():
    r = score_signals([_sig("HIGH", "AUTHORITY_INACTIVE")])
    assert r.reasons
    assert r.signals[0].code == "AUTHORITY_INACTIVE"
