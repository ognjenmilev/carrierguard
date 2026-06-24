"""Turn fraud signals into a risk decision per the policy."""

from __future__ import annotations

from core.models import Decision, FraudSignal, RiskResult
from core.policy import REJECT_SCORE, REVIEW_SCORE, SEVERITY_WEIGHTS


def score_signals(signals: list[FraudSignal]) -> RiskResult:
    """Score signals into APPROVE / REVIEW / REJECT.

    Any single HIGH signal forces REJECT (a revoked authority or no insurance is
    disqualifying on its own); otherwise the summed score decides.
    """
    score = min(100, sum(SEVERITY_WEIGHTS.get(s.severity.upper(), 0) for s in signals))
    has_high = any(s.severity.upper() == "HIGH" for s in signals)

    if has_high or score >= REJECT_SCORE:
        decision = Decision.REJECT
    elif score >= REVIEW_SCORE:
        decision = Decision.REVIEW
    else:
        decision = Decision.APPROVE

    return RiskResult(
        decision=decision,
        score=score,
        reasons=[s.detail for s in signals],
        signals=list(signals),
    )
