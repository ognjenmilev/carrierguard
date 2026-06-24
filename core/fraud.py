"""Fraud / risk heuristics over a CarrierData snapshot.

Pure functions, no I/O. Each heuristic that trips appends a FraudSignal with a
severity (HIGH / MEDIUM / LOW). CarrierData's conservative defaults mean missing
data tends to surface as risk rather than silently passing.

The HIGH signals encode the post-Montgomery must-checks (can they legally
operate? insured? not out-of-service?); the MEDIUM ones encode the classic
double-brokering / identity tells.
"""

from __future__ import annotations

from datetime import date

from core.models import CarrierData, FraudSignal

# Address tokens that usually mean a mail drop / CMRA rather than a real yard.
_CMRA_TOKENS = ("UPS STORE", "MAILBOX", "PMB", "PO BOX", "P O BOX", "POBOX", "PAK MAIL")

# Generic company words stripped before comparing names, so "ACME TRUCKING LLC"
# and "Acme Trucking" are treated as the same carrier.
_NAME_NOISE = {
    "LLC", "INC", "INCORPORATED", "CO", "CORP", "CORPORATION", "LTD", "LP", "LLP",
    "COMPANY", "TRUCKING", "TRANSPORT", "TRANSPORTATION", "LOGISTICS", "FREIGHT",
    "CARRIER", "CARRIERS", "EXPRESS", "LINE", "LINES", "GROUP", "ENTERPRISES",
}


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in name.upper())
    return " ".join(t for t in cleaned.split() if t and t not in _NAME_NOISE)


def _days_since(iso_date: str | None, today: date) -> int | None:
    if not iso_date:
        return None
    try:
        return (today - date.fromisoformat(iso_date[:10])).days
    except ValueError:
        return None


def detect_fraud(
    carrier: CarrierData,
    *,
    ratecon_name: str | None = None,
    today: date,
) -> list[FraudSignal]:
    """Return the risk/fraud signals tripped by this carrier (empty == clean)."""
    signals: list[FraudSignal] = []

    # --- HIGH: legal eligibility to haul ---
    if (carrier.authority_status or "").upper() != "ACTIVE":
        signals.append(FraudSignal(
            "AUTHORITY_INACTIVE", "HIGH",
            f"Operating authority is not active (status: {carrier.authority_status}).",
        ))

    if carrier.out_of_service:
        signals.append(FraudSignal(
            "OUT_OF_SERVICE", "HIGH",
            "Carrier is under an out-of-service order.",
        ))

    if carrier.insurance_required and not carrier.insurance_on_file:
        signals.append(FraudSignal(
            "NO_INSURANCE", "HIGH",
            "No BIPD insurance on file though insurance is required.",
        ))

    rating = (carrier.safety_rating or "").upper()
    if rating == "UNSATISFACTORY":
        signals.append(FraudSignal(
            "UNSATISFACTORY_SAFETY", "HIGH", "FMCSA safety rating is Unsatisfactory.",
        ))
    elif rating == "CONDITIONAL":
        signals.append(FraudSignal(
            "CONDITIONAL_SAFETY", "MEDIUM", "FMCSA safety rating is Conditional.",
        ))

    # --- MEDIUM: double-brokering / identity tells ---
    age = _days_since(carrier.authority_granted_date, today)
    if age is not None and age < 90:
        signals.append(FraudSignal(
            "AUTHORITY_TOO_NEW", "MEDIUM",
            f"Operating authority is only {age} days old (a common double-brokering signal).",
        ))

    if ratecon_name and carrier.legal_name:
        a, b = _normalize_name(ratecon_name), _normalize_name(carrier.legal_name)
        if a and b and a != b and a not in b and b not in a:
            signals.append(FraudSignal(
                "NAME_MISMATCH", "HIGH",
                f"Rate-confirmation name '{ratecon_name}' does not match the FMCSA "
                f"legal name '{carrier.legal_name}'.",
            ))

    addr = (carrier.physical_address or "").upper()
    if any(tok in addr for tok in _CMRA_TOKENS):
        signals.append(FraudSignal(
            "ADDRESS_CMRA", "MEDIUM",
            "Physical address looks like a mail drop / CMRA, not a carrier yard.",
        ))

    return signals
