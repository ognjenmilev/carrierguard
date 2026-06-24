"""FMCSA QCMobile client.

Two layers, deliberately split so the logic is testable without a network:

* ``parse_carrier`` — pure: maps a raw QCMobile JSON payload to ``CarrierData``.
  FMCSA encodes things tersely, so this is where we normalize them:
    - ``allowedToOperate``  "Y"/"N"        -> authority_status ACTIVE/INACTIVE
    - ``bipdInsuranceOnFile`` "$1000"/"0"  -> insurance_on_file bool (>$0)
    - ``safetyRating``      "S"/"C"/"U"    -> SATISFACTORY/CONDITIONAL/UNSATISFACTORY
    - ``oosDate``           null/date      -> out_of_service bool
* ``fetch_carrier`` — the thin network call that pulls a payload by MC/docket
  number, then hands it to ``parse_carrier``.
"""

from __future__ import annotations

import os

import requests

from core.models import CarrierData

QC_BASE = "https://mobile.fmcsa.dot.gov/qc/services"
_SAFETY = {"S": "SATISFACTORY", "C": "CONDITIONAL", "U": "UNSATISFACTORY"}


def _extract_carrier(payload: dict) -> dict:
    """Pull the carrier dict out of a QCMobile response.

    Handles the by-DOT shape ``{"content": {"carrier": {...}}}``, the
    name/docket search shape ``{"content": [{"carrier": {...}}, ...]}``, and a
    bare carrier dict.
    """
    content = payload.get("content", payload)
    if isinstance(content, list):
        content = content[0] if content else {}
    return content.get("carrier", content)


def _to_int(value: object) -> int:
    """Best-effort int from FMCSA's string-or-null numeric fields."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 0


def parse_carrier(payload: dict, mc_number: str = "") -> CarrierData:
    """Map a raw QCMobile payload to a normalized ``CarrierData``."""
    c = _extract_carrier(payload)

    allowed = (c.get("allowedToOperate") or "").strip().upper()
    rating = c.get("safetyRating")
    address = ", ".join(
        p for p in (c.get("phyStreet"), c.get("phyCity"), c.get("phyState"), c.get("phyZipcode")) if p
    )

    return CarrierData(
        mc_number=mc_number,
        dot_number=str(c["dotNumber"]) if c.get("dotNumber") is not None else None,
        legal_name=c.get("legalName"),
        dba_name=c.get("dbaName"),
        authority_status="ACTIVE" if allowed == "Y" else "INACTIVE",
        authority_granted_date=None,  # not in the snapshot; /authority endpoint provides it if needed
        insurance_on_file=_to_int(c.get("bipdInsuranceOnFile")) > 0,
        insurance_required=(c.get("bipdInsuranceRequired") or "").strip().upper() == "Y",
        safety_rating=_SAFETY.get(rating, rating),
        out_of_service=c.get("oosDate") is not None,
        phone=c.get("telephone"),
        email=None,
        physical_address=address or None,
        raw=c,
    )


def fetch_carrier(
    mc_number: str,
    *,
    webkey: str | None = None,
    timeout: float = 15.0,
    session: requests.Session | None = None,
) -> CarrierData:
    """Fetch a carrier by MC/docket number from the live QCMobile API.

    The WebKey is read from the ``FMCSA_WEBKEY`` env var if not passed in. It is
    never logged.
    """
    webkey = webkey or os.environ.get("FMCSA_WEBKEY")
    if not webkey:
        raise RuntimeError("FMCSA_WEBKEY is not set (pass webkey= or set the env var).")

    mc = str(mc_number).strip().upper().removeprefix("MC").strip().lstrip("-").strip()
    url = f"{QC_BASE}/carriers/docket-number/{mc}"
    http = session or requests
    resp = http.get(url, params={"webKey": webkey}, timeout=timeout)
    resp.raise_for_status()
    return parse_carrier(resp.json(), mc_number=str(mc_number))
