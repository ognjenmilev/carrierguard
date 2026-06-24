# CarrierGuard — Design Spec

- **Capstone:** Google × Kaggle "AI Agents Intensive (Vibe Coding)" 2026
- **Track:** Agents for Business
- **Date:** 2026-06-23
- **Status:** Draft for review

---

## 1. Problem

On **May 14, 2026**, the U.S. Supreme Court ruled in *Montgomery v. Caribe Transport* that state negligent-hiring claims against freight brokers are **not preempted** — a broker can now be sued when a carrier it selected causes a crash. Overnight, ~**17,000** small/mid U.S. freight brokerages became legally exposed for *who they hire to haul freight* — during an active freight-**fraud** wave (double-brokering, identity theft, hundreds of millions in losses).

Brokers' counsel now say every broker needs "a written policy/protocol governing how a broker onboards and **monitors the ongoing eligibility** of each carrier" — but note that only the largest brokers have data-analyst teams to do this. Small brokers are stuck with manual spreadsheets and fragmented checks.

**The gap:** existing tools (Carrier411, Highway, DAT CarrierWatch) are carrier-flagging *databases* — some disputed as unvetted "hearsay" blacklists. Per counsel, **no single tool** does end-to-end onboarding vetting **+** continuous re-verification **+** a defensible, documented decision trail. That hole is what CarrierGuard fills.

*Sources: SCOTUSblog (Montgomery ruling, May 2026); Benesch Law, "Freight Brokers in a Post-Montgomery World."*

## 2. Users & value

- **User:** a dispatcher/owner at a small freight brokerage with no compliance or data team.
- **Value:** vet a carrier in seconds instead of by hand; never haul with a carrier whose authority or insurance has lapsed; and keep a **defensible audit record** of every booking decision — the exact artifact that limits negligent-hiring exposure.

## 3. Why an agent (not a chatbot or a script)

A single prompt cannot: pull live FMCSA authority/insurance/safety data, cross-check the carrier named on the rate confirmation against the FMCSA entity, apply fraud heuristics, **and re-run all of it on a schedule** across every active carrier while logging a dated decision each time. CarrierGuard needs live multi-source data + multi-step reasoning + scheduled autonomy + a persistent audit trail — i.e., an agent.

## 4. Solution overview

Two modes:

- **Vet (on-demand):** input an MC#/DOT# (+ optional rate-confirmation details) → CarrierGuard returns **Approve / Review / Reject** with reasons, plus a timestamped **Carrier Vetting Record**.
- **Watch (scheduled):** nightly, re-check the broker's active-carrier watchlist and alert on material changes (authority revoked, insurance lapsed, safety-score drop).

## 5. Architecture (multi-agent, ADK)

A root **Orchestrator** coordinates specialist agents in a pipeline:

1. **Data-Gatherer** (tool-using) → calls the **FMCSA MCP server** for: operating-authority status, insurance-on-file (coverage + active/lapsed), SMS/safety BASIC scores, crash & inspection history, legal name / DBA / address / phone.
2. **Fraud-Sleuth** → flags double-brokering / identity tells: authority brand-new or recently reactivated; address is a CMRA / UPS-Store; phone or email domain mismatched vs. the entity; rate-con carrier name ≠ FMCSA legal name.
3. **Risk-Scorer** → fuses the signals into **Approve / Review / Reject** against a **configurable policy** (this policy *is* the "written protocol" counsel requires), with explicit reasons.
4. **Record-Writer** → produces the dated **Carrier Vetting Record** (inputs, data values, signals, score, decision, timestamp) and appends it to the audit log.

**Watch mode** wraps the same pipeline behind a scheduled trigger over a stored watchlist, diffs against the last run, and emits change alerts.

**Data flow:** `MC# → Data-Gatherer (FMCSA MCP) → Fraud-Sleuth → Risk-Scorer → Record-Writer → Vetting Record + audit log`

## 6. Data sources (free / public)

- **FMCSA QCMobile API** (free web key) — primary carrier data.
- **FMCSA SAFER** company snapshot + **Licensing & Insurance (L&I)** — authority + insurance.
- Demo uses real MC#s: one clean carrier (Approve) and one revoked/sketchy (Reject). Cached fixtures as a fallback so the live demo never depends on API uptime.

## 7. Course concepts demonstrated (need ≥ 3 of 6)

| Concept | How | Where |
|---|---|---|
| **Multi-agent system (ADK)** | Gatherer → Fraud-Sleuth → Risk-Scorer → Record-Writer pipeline | Code |
| **MCP Server** | FMCSA data access wrapped as a reusable MCP server the agent calls | Code |
| **Security features** | secrets via env/Secret Manager (never in code), input validation, human-in-the-loop on Reject, audit log as a governance control | Code/Video |
| **Deployability** | Cloud Run / Agent Engine + Cloud Scheduler for the nightly Watch | Video |
| **Agent skills / Agents CLI** | scaffold / build / deploy via agents-cli | Code/Video |
| *(optional 6th)* **Antigravity** | build a component on camera | Video |

→ Comfortably 5 of 6.

## 8. Security & governance

- **No API keys/passwords in code** — `.env` locally (git-ignored), Secret Manager on deploy.
- **Human-in-the-loop:** Reject / borderline decisions require human confirmation before action.
- The **Vetting Record** is timestamped and append-only — it is the defensibility artifact.
- **Not legal advice:** CarrierGuard supports a broker's due-diligence process; it does not replace counsel. (Stated in the UI and README.)

## 9. Tech stack

- **Python**, **Google ADK**, **Gemini** (via personal Google AI Studio key).
- **MCP** server for FMCSA access; `httpx` for API calls.
- **agents-cli** for scaffold / build / deploy.
- Deploy: **Cloud Run** (or Agent Engine); **Cloud Scheduler** for Watch.
- Storage: lightweight (SQLite or JSON) for watchlist + audit log in v1.

## 10. Build phases

- **Phase 0 — Setup:** scaffold ADK project (agents-cli); free FMCSA web key; env/secrets; repo hygiene.
- **Phase 1 — Vet (core demo):** MC# in → FMCSA MCP fetch → Fraud + Score → Vetting Record out. *(A complete demo on its own.)*
- **Phase 2 — Watch (differentiator):** scheduled watchlist re-check + change alerts.
- **Phase 3 — Ship:** README + architecture diagram, deploy, record the 5-minute video (optional Antigravity cameo).

## 11. Demo plan (5-minute video)

1. **Hook:** "Six weeks ago the Supreme Court made 17,000 brokers liable for the carriers they hire."
2. Vet a **clean** carrier → Approve + Vetting Record.
3. Vet a **revoked / fraud-flagged** carrier → Reject with reasons.
4. **Watch** mode catches an overnight insurance lapse → alert.
5. Architecture diagram + "why an agent" + the build (ADK, MCP, Gemini, deploy).

## 12. Risks & mitigations

- **FMCSA API flakiness / rate limits** → cache fixtures for the demo; graceful fallback.
- **Fraud heuristics are demo-grade** → frame as signals/aids, human-confirmed, never automatic verdicts.
- **Scope creep** → Phase 1 is independently shippable; Phases 2–3 are additive.
- **Liability framing** → "supports due diligence, not legal advice" disclaimer throughout.

## 13. Out of scope (v1)

- Live integration with broker TMS / load boards.
- Auto-rejecting or auto-booking without human confirmation.
- Carriers outside FMCSA jurisdiction (non-US).

## 14. Assumptions

- Targeting **Phase 1 + 2** for the capstone; Phase 3 polish if time allows.
- Personal Google AI Studio key + free FMCSA key only — **zero company resources.**
