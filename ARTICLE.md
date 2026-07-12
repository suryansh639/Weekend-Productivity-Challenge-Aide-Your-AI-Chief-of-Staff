# Weekend Productivity Challenge: Aide — Your AI Chief-of-Staff

**Tag:** `productivity`

---

## Vision & What the App Does

Most productivity tools are just to-do lists you have to feed by hand. The problem
was never *tracking* the work — it's the constant triage: reading every email and
message, deciding what actually matters, drafting the same kinds of replies, and
remembering to follow up on the thread that went quiet last Tuesday. That busywork
sits between you and the 10% of decisions only you can make.

**Aide** is an agentic AI Chief-of-Staff that does that triage for you. It reads
your incoming inbox, classifies each item by urgency (P0–P3), decides whether a
human reply is genuinely needed, drafts that reply, and surfaces only what needs
your attention. You ask it things like *"prep me for the Series A follow-up and
draft an email,"* and it pulls the relevant thread, recalls what it knows about you,
writes a brief with talking points, and stages a draft — all in one step.

The rule that makes it trustworthy: **Aide never sends anything on its own.** Every
side-effecting action is staged as a *pending draft* that you approve or veto with
one click. When you veto something, it remembers why, so it improves over time. On a
schedule, it also scans for threads that have gone quiet and proactively drafts a
nudge — reactive assistants wait to be asked; Aide notices first.

## How You Built It

I structured Aide in clean layers so the agent logic never depends on any specific
LLM, database, or integration. There's an LLM interface (`complete` + `embed`), a
store interface, and a connector interface. In production those resolve to Amazon
Bedrock, DynamoDB, and real connectors; for local development they resolve to a
deterministic mock LLM and a JSON store. That single decision paid off enormously:
I could build and test the entire product — triage, multi-step prep, memory recall,
proactive nudges, and the approve/veto flow — completely offline, then flip to AWS
by changing environment variables.

The agent layer is a supervisor/worker pattern: a triage worker classifies items, a
Chief-of-Staff supervisor plans a request and delegates to retrieval workers (inbox
search + semantic memory) before composing a brief, and a nudge agent runs on a
timer. The trickiest design question was the human-in-the-loop gate. I modeled it as
a state machine — actions move `pending → approved → executed` (or `rejected`) — and
only the service layer, after your approval, is allowed to call a connector's
`execute()`. This is conceptually a LangGraph `interrupt()` before an execute node; I
implemented it directly to keep the Lambda bundle small and cold starts fast.

The biggest challenge was making the demo convincing without live Gmail OAuth. I
solved it with a seeded demo connector plus the mock LLM, so anyone can run the whole
thing end-to-end in two commands — while the Gmail connector interface sits ready for
real credentials.

## AWS Services Used / Architecture Overview

- **Amazon Bedrock** — Claude (via the Converse API) powers triage, prep, and nudge
  drafting; Titan Text Embeddings power semantic memory recall.
- **AWS Lambda** — hosts the FastAPI backend (through Mangum) and a separate
  scheduled nudge worker.
- **Amazon API Gateway (HTTP API)** — the front door for the React SPA.
- **Amazon DynamoDB** — a single-table store for inbox items, actions, and memory.
- **Amazon EventBridge Scheduler** — a weekday cron that triggers the proactive
  nudge scan.
- **Amazon S3 + CloudFront** — static hosting for the dashboard.

Flow: the SPA calls API Gateway → a Lambda running FastAPI → the agent layer, which
calls Bedrock and persists to DynamoDB. A second Lambda fires on a schedule to draft
nudges. Everything is serverless and pay-per-use, so idle cost is zero and it stays
inside the Free Tier.

## What You Learned

Two things stuck with me. First, **interfaces are what make agentic apps shippable.**
Hiding Bedrock and DynamoDB behind small protocols meant I could develop against a
mock, write fast deterministic tests, and treat AWS as a deployment target rather than
a development dependency. Second, **the approval UX *is* the product.** The difference
between "helpful" and "terrifying" for an agent that can send email is entirely in how
actions are staged, previewed, edited, and reversed. I spent as much care on the
pending-action gate as on the prompts. I also got hands-on with the Bedrock Converse
API and EventBridge Scheduler for the first time, and came away appreciating how far a
small serverless footprint can go.

## Link to App or Repo

Source code: **<add your public GitHub repo URL here>**

Run it locally in two commands (see the README) — it works fully offline with a mock
LLM and seeded inbox, then deploys to AWS with `sam deploy --guided`.
