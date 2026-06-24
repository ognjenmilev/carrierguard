# CarrierGuard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Framework-specific tasks (ADK agents, MCP server, deploy) reference the `google-agents-cli-*` skills — load those at the relevant step and confirm exact API signatures against the installed ADK version before writing final code.

**Goal:** A multi-agent ADK system that vets a freight carrier from its MC#/DOT# against live FMCSA data + fraud heuristics, returns Approve/Review/Reject with a dated audit record, and re-checks active carriers on a schedule.

**Architecture:** Pure-Python core (data model, FMCSA client, fraud heuristics, risk scoring, record writer) wrapped by an ADK multi-agent pipeline (Data-Gatherer → Fraud-Sleuth → Risk-Scorer → Record-Writer). FMCSA access is exposed as an MCP server the agent calls. A scheduled "Watch" job re-runs the pipeline over a stored watchlist and diffs results.

**Tech Stack:** Python 3.13, Google ADK, Gemini (personal AI Studio key), MCP, `httpx`, `pytest`, SQLite/JSON storage, Cloud Run + Cloud Scheduler (deploy).

## Global Constraints

- **Python 3.13** (NOT system 3.14 — pin for ADK/litellm compatibility, per prior expense-agent lab learning).
- **No secrets in code.** All keys via `.env` (git-ignored) locally, Secret Manager on deploy. `.env.example` documents required vars.
- **Model:** Gemini via personal Google AI Studio key (`GOOGLE_API_KEY`). Never company credentials/infrastructure.
- **TDD for all pure logic.** Every core-logic task: failing test → run → implement → pass → commit.
- **Human-in-the-loop:** REJECT/REVIEW decisions are advisory; never auto-act.
- **Disclaimer:** "Supports due diligence; not legal advice" in UI + README.
- **Test runner:** `pytest`. **Commit** after every green task.

---

## File Structure

```
carrierguard/
  pyproject.toml            # deps + tool config
  .env.example              # GOOGLE_API_KEY=, FMCSA_WEBKEY=
  README.md                 # Phase 3
  docs/
    DESIGN.md               # done
    plans/2026-06-23-carrierguard-implementation.md  # this file
  carrierguard/
    __init__.py
    models.py               # CarrierData, FraudSignal, RiskResult, VettingRecord, Decision
    fmcsa/
      __init__.py
      client.py             # FMCSA QCMobile client (httpx) -> CarrierData
      fixtures/             # recorded sample JSON for tests + demo fallback
    fraud.py                # pure fraud heuristics over CarrierData
    policy.py               # scoring weights + thresholds (configurable)
    scorer.py               # signals -> RiskResult
    record.py               # RiskResult+CarrierData -> VettingRecord (+ render)
    storage.py              # audit log + watchlist persistence (SQLite)
    mcp_server/
      server.py             # MCP server exposing FMCSA lookups as tools
    agents/
      __init__.py
      gatherer.py           # ADK agent: calls FMCSA MCP tool
      sleuth.py             # ADK agent: runs fraud.py
      scorer_agent.py       # ADK agent: runs scorer.py
      recorder.py           # ADK agent: runs record.py + storage
      orchestrator.py       # ADK root agent / SequentialAgent pipeline
    watch/
      monitor.py            # scheduled re-check + diff + alert
  tests/
    test_models.py
    test_fmcsa_client.py
    test_fraud.py
    test_policy_scorer.py
    test_record.py
    test_storage.py
    test_watch.py
```

---

## PHASE 0 — Setup

### Task 0: Project scaffold, deps, env

**Files:**
- Create: `pyproject.toml`, `.env.example`, `carrierguard/__init__.py`, `tests/__init__.py`

**Steps:**

- [ ] **Step 1: Create venv (Python 3.13) and project metadata**

```bash
cd /c/dev/carrierguard
py -3.13 -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/pip install google-adk httpx pytest pydantic mcp
```

- [ ] **Step 2: Write `pyproject.toml`** (deps + pytest config)

```toml
[project]
name = "carrierguard"
version = "0.1.0"
requires-python = ">=3.13,<3.14"
dependencies = ["google-adk", "httpx", "pydantic", "mcp"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write `.env.example`**

```
GOOGLE_API_KEY=your-google-ai-studio-key
FMCSA_WEBKEY=your-free-fmcsa-qcmobile-webkey
```

- [ ] **Step 4: Verify install**

Run: `.venv/Scripts/python -c "import google.adk, httpx, mcp; print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .env.example carrierguard/__init__.py tests/__init__.py
git commit -m "chore: project scaffold, deps, env template"
```

> **Ogi action (parallel):** request the free **FMCSA QCMobile web key** and put it in a local `.env` (never commit). Confirm exact request URL via FMCSA developer portal at this step.

---

## PHASE 1 — Vet (core demo)

### Task 1: Data models

**Files:**
- Create: `carrierguard/models.py`
- Test: `tests/test_models.py`

**Interfaces — Produces:** `Decision` (enum APPROVE/REVIEW/REJECT), `CarrierData`, `FraudSignal(code, severity, detail)`, `RiskResult(decision, score, reasons, signals)`, `VettingRecord(mc_number, checked_at, carrier, risk, policy_version)`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py
from carrierguard.models import CarrierData, Decision, FraudSignal

def test_carrierdata_defaults():
    c = CarrierData(mc_number="123456")
    assert c.mc_number == "123456"
    assert c.insurance_on_file is False
    assert c.raw == {}

def test_decision_enum():
    assert Decision.REJECT.value == "REJECT"
```

- [ ] **Step 2: Run, expect fail** — `.venv/Scripts/pytest tests/test_models.py -v` → FAIL (no module).

- [ ] **Step 3: Implement `models.py`**

```python
from dataclasses import dataclass, field
from enum import Enum

class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"

@dataclass
class CarrierData:
    mc_number: str
    dot_number: str | None = None
    legal_name: str | None = None
    dba_name: str | None = None
    authority_status: str | None = None        # ACTIVE / INACTIVE / REVOKED
    authority_granted_date: str | None = None  # ISO date
    insurance_on_file: bool = False
    insurance_required: bool = True
    safety_rating: str | None = None           # SATISFACTORY / CONDITIONAL / UNSATISFACTORY
    out_of_service: bool = False
    phone: str | None = None
    email: str | None = None
    physical_address: str | None = None
    raw: dict = field(default_factory=dict)

@dataclass
class FraudSignal:
    code: str
    severity: str   # LOW / MEDIUM / HIGH
    detail: str

@dataclass
class RiskResult:
    decision: Decision
    score: int
    reasons: list[str] = field(default_factory=list)
    signals: list[FraudSignal] = field(default_factory=list)

@dataclass
class VettingRecord:
    mc_number: str
    checked_at: str
    carrier: CarrierData
    risk: RiskResult
    policy_version: str
```

- [ ] **Step 4: Run, expect pass.** - [ ] **Step 5: Commit** `feat: core data models`

### Task 2: FMCSA client (with fixtures)

**Files:**
- Create: `carrierguard/fmcsa/client.py`, `carrierguard/fmcsa/__init__.py`, `carrierguard/fmcsa/fixtures/active_carrier.json`, `carrierguard/fmcsa/fixtures/revoked_carrier.json`
- Test: `tests/test_fmcsa_client.py`

**Interfaces — Consumes:** `CarrierData`. **Produces:** `fetch_carrier(mc_number: str, *, webkey: str, client: httpx.Client | None = None) -> CarrierData`; `parse_carrier(payload: dict) -> CarrierData`.

> The QCMobile field names below are the *expected* shape — confirm against a real API response when the webkey is in hand, then update fixtures + `parse_carrier`.

- [ ] **Step 1: Save two fixture JSONs** (record real QCMobile responses once webkey exists; until then, hand-write representative payloads with fields: `legalName`, `dotNumber`, `carrierOperation`, `allowedToOperate`, `bipdInsuranceOnFile`, `safetyRating`, `phyStreet`, etc.).

- [ ] **Step 2: Write failing test** (parse only — no network)

```python
# tests/test_fmcsa_client.py
import json, pathlib
from carrierguard.fmcsa.client import parse_carrier
from carrierguard.models import CarrierData

FIX = pathlib.Path(__file__).parent.parent / "carrierguard/fmcsa/fixtures"

def test_parse_active_carrier():
    payload = json.loads((FIX / "active_carrier.json").read_text())
    c = parse_carrier(payload)
    assert isinstance(c, CarrierData)
    assert c.authority_status == "ACTIVE"
    assert c.insurance_on_file is True

def test_parse_revoked_carrier():
    payload = json.loads((FIX / "revoked_carrier.json").read_text())
    c = parse_carrier(payload)
    assert c.authority_status in {"REVOKED", "INACTIVE"}
```

- [ ] **Step 3: Run, expect fail.**
- [ ] **Step 4: Implement `parse_carrier` + `fetch_carrier`** (httpx GET to QCMobile `/carriers/{mc}?webKey=...`; map fields → `CarrierData`; `fetch_carrier` falls back to fixture if `CARRIERGUARD_OFFLINE=1`). Confirm endpoint/fields via FMCSA docs + context7 at this step.
- [ ] **Step 5: Run, expect pass.** - [ ] **Step 6: Commit** `feat: FMCSA client + fixtures`

### Task 3: Fraud heuristics

**Files:**
- Create: `carrierguard/fraud.py`
- Test: `tests/test_fraud.py`

**Interfaces — Consumes:** `CarrierData`, `FraudSignal`. **Produces:** `detect_fraud(carrier: CarrierData, *, ratecon_name: str | None = None, today: date) -> list[FraudSignal]`.

- [ ] **Step 1: Write failing tests** (one per heuristic)

```python
# tests/test_fraud.py
from datetime import date
from carrierguard.models import CarrierData
from carrierguard.fraud import detect_fraud

def codes(signals): return {s.code for s in signals}

def test_revoked_authority_is_high():
    c = CarrierData(mc_number="1", authority_status="REVOKED")
    sig = detect_fraud(c, today=date(2026,6,23))
    assert "AUTHORITY_REVOKED" in codes(sig)

def test_no_insurance_is_high():
    c = CarrierData(mc_number="1", authority_status="ACTIVE", insurance_on_file=False, insurance_required=True)
    assert "NO_INSURANCE" in codes(detect_fraud(c, today=date(2026,6,23)))

def test_brand_new_authority_flags_double_broker_risk():
    c = CarrierData(mc_number="1", authority_status="ACTIVE", insurance_on_file=True,
                    authority_granted_date="2026-05-20")
    assert "AUTHORITY_TOO_NEW" in codes(detect_fraud(c, today=date(2026,6,23)))

def test_name_mismatch_flags():
    c = CarrierData(mc_number="1", authority_status="ACTIVE", insurance_on_file=True, legal_name="ACME TRUCKING LLC")
    assert "NAME_MISMATCH" in codes(detect_fraud(c, ratecon_name="Speedy Freight Inc", today=date(2026,6,23)))

def test_clean_carrier_has_no_signals():
    c = CarrierData(mc_number="1", authority_status="ACTIVE", insurance_on_file=True,
                    authority_granted_date="2015-01-01", safety_rating="SATISFACTORY", legal_name="ACME TRUCKING LLC")
    assert detect_fraud(c, ratecon_name="ACME TRUCKING LLC", today=date(2026,6,23)) == []
```

- [ ] **Step 2: Run, expect fail.**
- [ ] **Step 3: Implement `detect_fraud`** (each heuristic appends a `FraudSignal`: AUTHORITY_REVOKED/INACTIVE→HIGH; NO_INSURANCE→HIGH; OUT_OF_SERVICE→HIGH; UNSATISFACTORY safety→HIGH, CONDITIONAL→MEDIUM; AUTHORITY_TOO_NEW <90 days→MEDIUM; NAME_MISMATCH via case-insensitive normalized compare→HIGH; address CMRA keyword match→MEDIUM).
- [ ] **Step 4: Run, expect pass.** - [ ] **Step 5: Commit** `feat: fraud heuristics`

### Task 4: Policy + risk scorer

**Files:**
- Create: `carrierguard/policy.py`, `carrierguard/scorer.py`
- Test: `tests/test_policy_scorer.py`

**Interfaces — Consumes:** `FraudSignal`, `RiskResult`, `Decision`. **Produces:** `POLICY_VERSION: str`; `score_signals(signals: list[FraudSignal]) -> RiskResult` (HIGH=50, MEDIUM=20, LOW=5; total ≥50 or any HIGH → REJECT; 20–49 → REVIEW; <20 → APPROVE).

- [ ] **Step 1: Write failing tests**

```python
from carrierguard.models import FraudSignal, Decision
from carrierguard.scorer import score_signals

def test_high_signal_rejects():
    r = score_signals([FraudSignal("AUTHORITY_REVOKED","HIGH","x")])
    assert r.decision == Decision.REJECT

def test_no_signals_approves():
    assert score_signals([]).decision == Decision.APPROVE

def test_medium_only_reviews():
    r = score_signals([FraudSignal("AUTHORITY_TOO_NEW","MEDIUM","x")])
    assert r.decision == Decision.REVIEW
```

- [ ] **Step 2–4: Run-fail → implement → run-pass.** - [ ] **Step 5: Commit** `feat: policy + risk scorer`

### Task 5: Vetting record + audit storage

**Files:**
- Create: `carrierguard/record.py`, `carrierguard/storage.py`
- Test: `tests/test_record.py`, `tests/test_storage.py`

**Interfaces — Produces:** `build_record(carrier, risk, *, now_iso: str) -> VettingRecord`; `render_record(rec) -> str` (human-readable report w/ disclaimer); `save_record(rec, db_path) -> int` (append-only audit log); `get_record(record_id, db_path) -> VettingRecord`.

- [ ] **Step 1: Failing tests** — record contains mc/decision/timestamp; render includes "not legal advice"; save→get round-trips.
- [ ] **Step 2–4: run-fail → implement (SQLite append-only table) → run-pass.** - [ ] **Step 5: Commit** `feat: vetting record + audit log`

### Task 6: FMCSA MCP server

**Files:**
- Create: `carrierguard/mcp_server/server.py`

**Interfaces — Produces:** MCP server exposing tool `lookup_carrier(mc_number: str) -> dict` (returns serialized `CarrierData`) backed by `fmcsa.client.fetch_carrier`.

- [ ] **Step 1:** Load `google-agents-cli-adk-code` + MCP docs; confirm the MCP server stub for the installed `mcp` version.
- [ ] **Step 2:** Implement server: register `lookup_carrier` tool → calls `fetch_carrier` → returns dict.
- [ ] **Step 3: Verify** — run the MCP server locally and call `lookup_carrier` with a fixture MC#; confirm JSON returns.
- [ ] **Step 4: Commit** `feat: FMCSA MCP server`

### Task 7: ADK agents + orchestrator (end-to-end Vet)

**Files:**
- Create: `carrierguard/agents/gatherer.py`, `sleuth.py`, `scorer_agent.py`, `recorder.py`, `orchestrator.py`, `agents/__init__.py`

**Interfaces — Produces:** `root_agent` (ADK) that, given an MC# (+ optional rate-con name), runs Gatherer (MCP `lookup_carrier`) → Sleuth (`detect_fraud`) → Scorer (`score_signals`) → Recorder (`build_record`+`save_record`) and returns the rendered Vetting Record.

- [ ] **Step 1:** Load `google-agents-cli-adk-code`; confirm ADK agent + SequentialAgent API for the installed version.
- [ ] **Step 2:** Implement each sub-agent as an ADK agent wrapping the corresponding pure function as a tool; compose with a SequentialAgent pipeline behind a root orchestrator agent.
- [ ] **Step 3: Verify end-to-end** — run via `adk run` (or agents-cli) on the clean fixture MC# → APPROVE record; on the revoked fixture MC# → REJECT record. This is the Phase-1 demo.
- [ ] **Step 4: Commit** `feat: ADK multi-agent vetting pipeline (end-to-end)`

---

## PHASE 2 — Watch (the differentiator)

### Task 8: Watchlist + change detection

**Files:**
- Modify: `carrierguard/storage.py` (add watchlist table)
- Create: `carrierguard/watch/monitor.py`
- Test: `tests/test_watch.py`

**Interfaces — Produces:** `add_to_watchlist(mc)`, `run_watch(db_path, fetch=fetch_carrier) -> list[Alert]` where `Alert(mc, change, old, new)` is emitted only on material change (authority→revoked, insurance true→false, safety downgrade).

- [ ] **Step 1: Failing test** — seed a watchlist carrier with a stored prior state; inject a `fetch` stub returning a now-revoked carrier; assert one `AUTHORITY_REVOKED` alert; assert no alert when unchanged.
- [ ] **Step 2–4: run-fail → implement diff → run-pass.** - [ ] **Step 5: Commit** `feat: watchlist + change detection`

### Task 9: Scheduled monitor entrypoint

**Files:**
- Modify: `carrierguard/watch/monitor.py` (CLI entrypoint `python -m carrierguard.watch.monitor`)

- [ ] **Step 1:** Implement entrypoint that runs `run_watch` and prints/sends alerts (stdout + optional webhook).
- [ ] **Step 2: Verify** — run manually against a watchlist incl. the revoked fixture → prints the alert. (Cloud Scheduler wiring is Phase 3.)
- [ ] **Step 3: Commit** `feat: scheduled watch entrypoint`

---

## PHASE 3 — Ship

### Task 10: README + architecture diagram
- [ ] Write `README.md` (problem, solution, architecture, setup, run, **reproduce-the-deploy**, disclaimer, "no keys in code"). Reuse DESIGN.md. Add a simple architecture diagram (draw + export PNG to `docs/`). Commit `docs: README + architecture`.

### Task 11: Deploy + reproduce docs
- [ ] Load `google-agents-cli-deploy`; deploy to Cloud Run (or Agent Engine) using your personal GCP project; Cloud Scheduler triggers the Watch monitor daily; secrets via Secret Manager. Document exact repro steps in README. Commit `chore: deployment + repro docs`.

### Task 12: 5-minute video
- [ ] Storyboard + record per DESIGN.md §11 (hook → Approve demo → Reject demo → Watch alert → architecture + why-agents + build). Optional Antigravity cameo for the 6th concept.

---

## Self-Review (completed by author)

- **Spec coverage:** every DESIGN.md section maps to a task — problem/value (README/video), architecture (Tasks 1–7), data (Task 2), concepts: multi-agent (7), MCP (6), security (Global Constraints + Task 5 audit log + .gitignore), deployability (11), agents-cli (0/7/11); watch mode (8–9); demo (12); risks (fixtures fallback in Task 2, HITL in scorer/record).
- **Placeholders:** core-logic tasks (1–5, 8) have complete test+impl code. Framework tasks (6,7,11) intentionally defer *exact* ADK/MCP/deploy signatures to the `google-agents-cli-*` skills + live docs at execution — flagged explicitly, not silent TODOs.
- **Type consistency:** `CarrierData`/`FraudSignal`/`RiskResult`/`VettingRecord`/`Decision` defined in Task 1 and used consistently in Tasks 2–9.
