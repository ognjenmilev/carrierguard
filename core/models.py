"""Core data models for CarrierGuard.

Plain dataclasses with no third-party dependencies. These are the structures
every other module (FMCSA client, fraud heuristics, scorer, record writer)
produces or consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Decision(str, Enum):
    """Final vetting decision for a carrier."""

    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass
class CarrierData:
    """Normalized snapshot of a carrier, mapped from FMCSA data.

    Defaults are deliberately conservative: until proven otherwise we assume a
    carrier has no insurance on file and that insurance is required, so missing
    data fails safe (toward REVIEW/REJECT) rather than silently approving.
    """

    mc_number: str
    dot_number: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    authority_status: str | None = None        # ACTIVE / INACTIVE / REVOKED
    authority_granted_date: str | None = None  # ISO date string, e.g. "2015-01-01"
    insurance_on_file: bool = False
    insurance_required: bool = True
    safety_rating: str | None = None           # SATISFACTORY / CONDITIONAL / UNSATISFACTORY
    out_of_service: bool = False
    phone: str | None = None
    email: str | None = None
    physical_address: str | None = None
    raw: dict = field(default_factory=dict)    # raw FMCSA payload, kept for the audit trail


@dataclass
class FraudSignal:
    """A single risk/fraud indicator detected on a carrier."""

    code: str        # machine code, e.g. "AUTHORITY_REVOKED"
    severity: str    # "LOW" | "MEDIUM" | "HIGH"
    detail: str      # human-readable explanation


@dataclass
class RiskResult:
    """Outcome of scoring a carrier's fraud signals against the policy."""

    decision: Decision
    score: int                                  # 0-100, higher = riskier
    reasons: list[str] = field(default_factory=list)
    signals: list[FraudSignal] = field(default_factory=list)


@dataclass
class VettingRecord:
    """The dated, defensible record of a single vetting decision (audit trail)."""

    mc_number: str
    checked_at: str                             # ISO timestamp
    carrier: CarrierData
    risk: RiskResult
    policy_version: str
