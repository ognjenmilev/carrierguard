# CarrierGuard — Capstone Writeup

*Google × Kaggle AI Agents Intensive (Vibe Coding) · Track: Agents for Business*

Every day, somewhere, a small business owner hands their livelihood to a stranger and hopes they chose well. **CarrierGuard** is for one of those people: the freight broker.

A freight broker is a middleman in trucking. A company has goods to move; the broker finds a trucking company to haul them and takes a cut. Think of them as a matchmaker between cargo and trucks. There are tens of thousands of them in the United States, and most are tiny — a few people, sometimes one person working from a kitchen table.

## What changed

On May 14, 2026, the rules of that job changed. The U.S. Supreme Court ruled, in *Montgomery v. Caribe Transport II*, that if a broker picks a trucking company that then causes a deadly crash, the broker can be sued for it, even though the broker was never behind the wheel. In a single decision, roughly 17,000 small brokerages became legally responsible for who they hire. And it happened during a wave of fraud, where criminals pose as legitimate trucking companies or quietly pass the load to someone else.

So now every broker is expected to deeply check each trucking company before hiring it, and keep monitoring it for as long as it hauls their freight. The big brokerages have data teams who handle this. The small ones have a spreadsheet and a knot in their stomach.

The information is out there. The U.S. government runs a free public database (FMCSA) that holds every trucking company's license status, insurance, and safety record. But reading it by hand, for every company, every day, is impossible for a small team. That is the gap CarrierGuard fills.

## What CarrierGuard does

CarrierGuard is an AI agent that does the checking for you, and never stops. The simplest way to describe it: *a background check on a trucking company that keeps running after you've already hired them.*

It works in two modes.

**Vet, on demand.** You give it a trucking company's ID number. In seconds it pulls that company's live federal record, weighs the risk, and gives you a clear verdict — **APPROVE**, **REVIEW**, or **REJECT** — with the reasons spelled out and a dated record saved as proof that you checked.

**Watch, automatically.** It keeps a list of the trucking companies you already work with and re-checks them every night. The moment one loses its license, lets its insurance lapse, gets pulled off the road, or has its safety rating downgraded, you get a warning, before you hand them your next load.

I tried it on real companies. Old Dominion, a large and well-known carrier, came back **APPROVE**: active license, a million dollars of insurance, a clean safety rating. A company called B Swift came back **REJECT**, flagged three times over: no active license, ordered off the road, and no insurance on record. Watching the agent catch that, using live government data, is the moment this stopped being an idea and started feeling real.

## Why it has to be an agent

This could never be a single question typed into a chatbot. It needs live data, pulled on a schedule, from real sources, and written down in a way that holds up months later if a lawyer ever asks what you knew and when. A chatbot can't watch a company overnight or prove what it checked. That is the whole reason it's an agent: it acts on its own, uses real tools, and remembers.

One choice I'm proud of: the AI never makes the final call. It reads the request, gathers the data, and explains everything in plain language. But the actual approve-or-reject decision is calculated by fixed rules in code, not guessed by the model. A person's legal safety should not depend on a model's mood. *The AI explains. The rules decide.*

## How it's built

Under the hood, the decision logic is pure, self-contained code with no dependence on any cloud or AI framework, so it's covered by 35 automated tests that run in about a second. The AI agent is a thin layer on top, built with Google's ADK and Gemini. The link to the government database is wrapped as an MCP server that the agent calls. Security was a first-class concern: no keys in the code, an unchangeable audit log of every decision, and a clear "this is not legal advice" line on every answer. It runs on Google Cloud, with the nightly monitoring on a scheduler. And the data source is completely free and public, so anyone can run this without paying for anything or touching any company's private systems.

## What it isn't

To be honest about the limits: the fraud checks are signals for a human to confirm, not automatic judgments, and the tool is a due-diligence aid, not a lawyer. Where it goes next: deeper signals from the data, a second agent that writes a plain recommendation in human words, and alerts delivered straight to email or Slack.

I keep thinking about that one person at the kitchen table. They didn't ask for this new risk, and they can't afford a team to manage it. CarrierGuard won't make the decision for them. But it can check what they would never have time to check, watch their carriers while they sleep, and keep the kind of record that, on the worst day of their working life, is the difference between a hard phone call and a business that no longer exists.

Thank you for reading, and for taking the time to understand it.
