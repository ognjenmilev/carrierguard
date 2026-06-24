"""Scoring policy: severity weights, decision thresholds, and version.

This module IS the broker's 'written protocol' — explicit, versioned, and
auditable. Bump POLICY_VERSION whenever the weights or thresholds change so the
audit log records which ruleset produced each decision.
"""

POLICY_VERSION = "v1"

# Points contributed by each signal severity.
SEVERITY_WEIGHTS = {"HIGH": 50, "MEDIUM": 20, "LOW": 5}

# Total-score thresholds. Any single HIGH signal also forces REJECT regardless
# of total (see scorer).
REJECT_SCORE = 50   # >= this -> REJECT
REVIEW_SCORE = 20   # >= this (and < REJECT) -> REVIEW; below -> APPROVE
