# CarrierGuard — Capstone Writeup

*Google × Kaggle AI Agents Intensive (Vibe Coding) · Track: Agents for Business*

## The problem

On **May 14, 2026**, the U.S. Supreme Court ruled in *Montgomery v. Caribe Transport* that freight brokers can be sued for **negligent hiring** when a carrier they choose causes a crash. In one decision, roughly 17,000 small U.S. freight brokerages became liable for *which carriers they hand freight to* — and this landed in the middle of a freight-fraud wave of double-brokering and carrier-identity theft.

Brokers' attorneys now advise that every broker needs a **written protocol** to vet each carrier at booking *and* monitor it for as long as it's hauling. The catch: the large brokerages have data teams for this; small ones run on spreadsheets. The existing products are carrier-flagging databases — and, per industry counsel, no single tool does end-to-end vetting **plus** continuous re-verification **plus** a defensible, documented decision trail. That is the gap CarrierGuard fills.

## Why an agent

A carrier check is not a one-shot question. It needs **live data** from FMCSA, pulled **on a schedule**, combined across **multiple tools**, and recorded in a **persistent audit trail** that holds up later. A single chatbot prompt can't watch a carrier overnight or prove what it checked. That is precisely the shape of an agent: autonomous, tool-using, stateful. Importantly, CarrierGuard keeps the LLM doing what LLMs are good at — understanding the request, orchestrating tools, explaining the result — while the actual APPROVE/REVIEW/REJECT call is computed deterministically by a versioned policy, never guessed by the model.

## The solution

**Vet (on-demand):** give CarrierGuard a carrier's MC number; it pulls the live FMCSA record, scores the risk, and returns **APPROVE / REVIEW / REJECT** with the reasons and a timestamped audit record.

**Watch (scheduled):** it keeps a watchlist of your active carriers and re-checks them nightly, alerting the moment one's operating authority is revoked, its insurance lapses, it's placed out-of-service, or its safety rating drops.

Verified live against real carriers: **Old Dominion (MC 107478) → APPROVE**; **B Swift (MC 1217040) → REJECT** on three HIGH flags (inactive authority, out-of-service, uninsured). Priming a "looked fine yesterday" baseline for B Swift and running Watch produced three real change alerts.

## Architecture

A single ADK `LlmAgent` (Gemini via Vertex) orchestrates two tools:
1. **`lookup_carrier`**, served by a **FastMCP server** that wraps the FMCSA QCMobile API — real MCP integration the agent calls over stdio.
2. **`assess_carrier`**, a deterministic tool that runs fraud heuristics → a versioned scoring policy → an append-only audit record.

The risk logic lives in a pure **`core/`** package with no ADK or GCP imports, so it's fully unit-tested (35 tests) without a network or credentials; **`app/`** is the thin agent layer. Watch mode reuses the same `core/` engine behind a scheduled CLI entrypoint.

## The build journey

Idea selection was its own exercise. In mid-2026, every burning, agent-shaped *marketing* idea I evaluated already had funded products (AI-search visibility, content fact-checking, competitor monitoring, social crisis-response — all checked and ruled out). The one genuinely unbuilt, urgent opportunity was freight-broker carrier monitoring: a six-week-old Supreme Court trigger, no end-to-end incumbent, and a free public data source.

I built it core-first with test-driven development — data models, FMCSA client (against recorded real responses), fraud heuristics, scoring, audit log — all pure and tested before any agent code. Then I wrapped FMCSA as an MCP server, wired the ADK agent, and added scheduled Watch. Every layer was verified against the live FMCSA API.

## Concepts demonstrated

| Concept | Where |
|---|---|
| Agent (ADK) | `LlmAgent` orchestrating tools, in `app/agent.py` |
| MCP Server | `mcp_server/server.py` (FastMCP), consumed by the agent over stdio |
| Security | secrets in git-ignored `.env`, append-only audit log, advisory decisions + disclaimer |
| Agents CLI | scaffold / run / deploy via `agents-cli` |
| Deployability | Cloud Run / Agent Runtime + Cloud Scheduler |

## Limitations & next steps

Fraud heuristics are decision *signals*, human-confirmed, not automated verdicts; the agent is a due-diligence aid, not legal advice. Natural extensions: pull the FMCSA `/authority` and `/basics` endpoints for richer signals, add a second "advisor" agent for a plain-English recommendation (a true multi-agent system), and wire alert delivery to email/Slack.
