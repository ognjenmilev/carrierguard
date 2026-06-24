# CarrierGuard — 5-Minute Video Script

Teleprompter-style. **Bold** = what's on screen; plain = what you say. Target ~5:00. Aim for a calm, confident pace (~150 words/min).

---

### 0:00–0:35 · Hook + problem
**On screen:** you talking, then a headline/slide: "Montgomery v. Caribe Transport — May 14, 2026."

> "Six weeks ago, the Supreme Court changed the freight industry overnight. In *Montgomery v. Caribe*, it ruled that freight brokers can be sued when a carrier they hired causes a crash. Suddenly seventeen thousand small brokerages are legally on the hook for *who they hand freight to* — right as carrier fraud is spiking. Their lawyers say they now need to vet every carrier and keep monitoring it. The big brokers have data teams for that. The small ones have a spreadsheet. So I built CarrierGuard."

### 0:35–1:05 · Why an agent
**On screen:** slide — "Live data · on a schedule · many tools · audit trail."

> "Why an agent, and not just ChatGPT? Because this isn't a one-shot question. It needs *live* government data, pulled on a *schedule*, across *multiple tools*, with a *paper trail* that holds up later. A chatbot can't watch a carrier overnight or prove what it checked. That's exactly what an agent does — and CarrierGuard keeps the risk *decision* deterministic in code, so the model never guesses a verdict."

### 1:05–1:50 · Architecture
**On screen:** the README's Vet-flow Mermaid diagram.

> "Here's how it works. A single ADK agent, running Gemini, orchestrates two tools. The first, `lookup_carrier`, is served by an MCP server I built that wraps the FMCSA — the federal carrier database. The second, `assess_carrier`, runs fraud checks and a versioned scoring policy, then writes a dated record to an append-only audit log. The whole risk engine is a pure, fully-tested Python package — the agent just orchestrates and explains."

### 1:50–3:30 · Demo (the centerpiece — screen recording)
**On screen:** terminal. Run each command; let the output show.

> "Let's vet a real carrier — Old Dominion, a clean national carrier."

**Run:** `agents-cli run "Vet carrier MC 107478"` → point at **APPROVE**.

> "The agent calls the MCP tool, pulls Old Dominion's live FMCSA record — active authority, a million in insurance, satisfactory safety — and returns APPROVE, risk score zero, with an audit record."

> "Now a bad one — B Swift Transportation."

**Run:** `agents-cli run "Vet carrier MC 1217040"` → point at **REJECT** + the three findings.

> "REJECT — risk one hundred. Three high-severity flags: inactive authority, out-of-service, and no insurance on file. Exactly the carrier the new ruling says you must not book."

**On screen:** run the Watch alert command (the primed-baseline demo).

> "And this is the part a chatbot can't do. CarrierGuard keeps watching your active carriers. Here, B Swift looked fine when it was booked — overnight the agent re-checks and catches that its authority was pulled, its insurance lapsed, and it went out of service. Three alerts, before the next load moves."

### 3:30–4:30 · The build
**On screen:** quick scroll of the repo / `agents-cli`, optionally a moment in **Antigravity**.

> "I built this with the Agents CLI and the ADK. The risk logic came first, test-driven — thirty-five tests, all passing, with no network needed because I recorded real FMCSA responses as fixtures. Then I wrapped the FMCSA as an MCP server, wired the agent, and added the scheduled watch job. Secrets stay out of the code, every decision is logged, and it's all built on the free, public FMCSA API."

*(Optional: "I did some of the build inside Google Antigravity" — show it briefly.)*

### 4:30–5:00 · Close
**On screen:** you, then a closing slide: "CarrierGuard — vet once, watch always."

> "CarrierGuard turns a brand-new legal liability into a thirty-second check and a watchdog that never sleeps — for the small brokers who need it most. It supports their due diligence; it's not legal advice. Thanks for watching."

---

**Recording tips:** record the three terminal commands first as a clean screen-capture (they each take a few seconds), then narrate over them. Keep the demo segment tight — it's the most persuasive part. If you run long, trim the build section, not the demo.
