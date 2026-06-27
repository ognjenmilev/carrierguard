"""CarrierGuard live demo service (Cloud Run).

Serves the demo UI and a thin /api/vet endpoint that runs the REAL CarrierGuard
core pipeline (FMCSA fetch -> fraud heuristics -> policy score) for ANY MC
number. No LLM. The FMCSA WebKey is read from the environment (injected from
Secret Manager in production) and never leaves the server. A small cache and a
light rate limit protect the key; FMCSA errors degrade gracefully.
"""
import os
import sys
import time
import threading
from pathlib import Path
from datetime import date

# Make the `core` package importable whether it sits beside this file
# (container image) or one directory up (repo layout: webdemo/main.py).
_HERE = Path(__file__).resolve().parent
for _cand in (str(_HERE), str(_HERE.parent)):
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse, FileResponse

from core.fmcsa.client import fetch_carrier
from core.fraud import detect_fraud
from core.scorer import score_signals

app = FastAPI(title="CarrierGuard demo")

_cache = {}
_CACHE_TTL = 3600
_hits = []
_RL_MAX = 60
_RL_WINDOW = 60
_lock = threading.Lock()


def _thousands(raw, key):
    """FMCSA reports BIPD amounts in $1000 units, as strings."""
    try:
        return int(str(raw.get(key) or "0").strip())
    except (TypeError, ValueError):
        return 0


def _build(mc):
    c = fetch_carrier(mc)
    r = score_signals(detect_fraud(c, today=date.today()))
    raw = c.raw or {}
    domicile = ", ".join(p for p in (raw.get("phyCity"), raw.get("phyState")) if p)
    return {
        "mc": mc,
        "dot": c.dot_number,
        "legal": c.legal_name,
        "dba": c.dba_name,
        "authority_status": c.authority_status,
        "insurance_on_file": c.insurance_on_file,
        "insurance_required": c.insurance_required,
        "bipd_on_file": _thousands(raw, "bipdInsuranceOnFile"),
        "bipd_required": _thousands(raw, "bipdRequiredAmount"),
        "safety_rating": c.safety_rating,
        "out_of_service": c.out_of_service,
        "oos_date": raw.get("oosDate"),
        "domicile": domicile,
        "decision": r.decision.value,
        "score": r.score,
        "signals": [{"sev": s.severity, "code": s.code, "detail": s.detail} for s in r.signals],
    }


@app.get("/api/vet")
def vet(mc: str = ""):
    digits = "".join(ch for ch in str(mc).upper().replace("MC", "") if ch.isdigit())
    if not digits:
        return JSONResponse({"error": "Enter an MC number."}, status_code=400)
    now = time.time()
    with _lock:
        global _hits
        _hits = [t for t in _hits if now - t < _RL_WINDOW]
        cached = _cache.get(digits)
        if cached and now - cached[0] < _CACHE_TTL:
            return cached[1]
        if len(_hits) >= _RL_MAX:
            return JSONResponse({"error": "Busy right now - try again in a moment."}, status_code=429)
        _hits.append(now)
    try:
        payload = _build(digits)
    except Exception:
        return JSONResponse(
            {"error": "Couldn't retrieve that carrier from FMCSA. Check the MC number, or try one of the examples."},
            status_code=502,
        )
    if not payload.get("legal") and not payload.get("dot"):
        return JSONResponse(
            {"error": "No active carrier found for MC " + digits + ". Check the number, or try one of the examples."},
            status_code=404,
        )
    with _lock:
        _cache[digits] = (now, payload)
    return payload


@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)


@app.get("/")
def index():
    return FileResponse(_HERE / "live.html")
