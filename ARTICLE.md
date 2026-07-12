# Weekend Productivity Challenge: Aide — Your AI Chief-of-Staff

**Tag:** `productivity`

**Live demo:** http://aide-web-818515814116.s3-website-us-east-1.amazonaws.com
· **Live API:** https://h8m79exwpc.execute-api.us-east-1.amazonaws.com/health
· **Repo:** https://github.com/suryansh639/Weekend-Productivity-Challenge-Aide-Your-AI-Chief-of-Staff

---

## Vision & What the App Does

Every productivity tool I've used has the same blind spot: it helps me *track* work, but it never does the work of deciding what matters. The real tax on my day isn't the to-do list — it's the triage before the list. Reading every email and message, judging what's urgent, drafting the same kinds of replies, and remembering to chase the thread that went quiet last week. That sorting is where the hours quietly disappear, and it sits between me and the handful of decisions only I can actually make.

**Aide** is my attempt to flip that around. Instead of a list I feed by hand, it's an assistant that reads my incoming inbox for me, classifies every item by urgency (P0 to P3), decides whether a human reply is genuinely needed, drafts that reply, and then surfaces only the small slice that actually needs my attention. Everything routine — newsletters, automated alerts, FYIs — gets handled and tucked away so it isn't in my face.

From the user's point of view, it works like this. You open the dashboard and see four numbers: how many items were processed, how many need you, how many drafts are waiting, and how many Aide handled on its own. Below that is a "Needs your attention" queue with the important items on top, each tagged with a priority, a one-line summary, and Aide's reasoning for why it landed there. On the right is a chat box where you can ask something open-ended like *"Prep me for the Series A follow-up and draft an email,"* and Aide plans the steps itself — it finds the relevant thread, recalls what it already knows about you, writes a short brief with talking points, and drafts the email.

The rule that makes this safe to actually use: **Aide never sends anything on its own.** Every action that touches the outside world — a reply, a follow-up, a nudge — is staged as a *pending draft* you approve or veto with one click, and you can edit the text before approving. When you veto something, Aide records that so it learns what you don't want sent. It also runs a scheduled scan that notices threads which have gone quiet and drafts a nudge before you even remember the thread existed. Reactive assistants wait to be asked; Aide tries to notice first.

## How You Built It

I built Aide in clean layers, and one early decision shaped everything else: the agent logic depends only on small interfaces, never on a specific model, database, or integration. There's an LLM interface (`complete` + `embed`), a store interface, and a connector interface. In production those resolve to Amazon Bedrock, DynamoDB, and real connectors. For development they resolve to a deterministic mock LLM and a local JSON store.

That one choice is why I could ship in a weekend. I built and tested the entire product — triage, multi-step prep, memory recall, proactive nudges, and the approve/veto flow — completely offline, with fast deterministic tests, and only pointed it at AWS once the behavior was right.

The agent layer is a supervisor/worker pattern. A triage worker classifies each item and drafts replies. A Chief-of-Staff supervisor takes a free-form request, breaks it into steps, and delegates to retrieval workers (an inbox search and a semantic memory lookup) before composing a brief. A nudge agent runs on a timer. The trickiest part to get right was the human-in-the-loop gate. I modeled it as a small state machine: an action moves `pending → approved → executed`, or `pending → rejected`, and only the service layer, after your approval, is ever allowed to call a connector to actually perform it.

I hit two real challenges. The first was the demo itself: I didn't want to require live Gmail OAuth just to see the thing work, so I built a seeded "demo connector" — a realistic inbox of investor emails, an outage alert, an overdue invoice, newsletters, a stale thread — plus the mock LLM, so anyone can run the whole flow end-to-end in two commands. The Gmail connector is a clearly-marked interface, ready for real credentials, so the swap is trivial later.

The second challenge showed up at deployment. My machine had no SAM CLI and no Docker, and the backend depends on `pydantic-core`, a compiled library that has to be the Linux build to run on Lambda. I solved it by downloading the correct Linux (`manylinux`, cp312) wheels directly with pip and deploying the SAM template through `aws cloudformation package` and `deploy`, which understand the SAM transform natively. No Docker required. I also hit a nice surprise mid-build — the Claude model I'd planned on had just reached end-of-life — so I pivoted the whole app to **Amazon Nova**, which turned out to be a cleaner, fully-Amazon story anyway.

## AWS Services Used / Architecture Overview

- **Amazon Bedrock** — Amazon Nova (via the Converse API) powers triage, meeting prep, and nudge drafting; Amazon Titan Text Embeddings power semantic memory recall.
- **AWS Lambda** — runs the FastAPI backend (through Mangum) and a separate scheduled nudge worker.
- **Amazon API Gateway (HTTP API)** — the front door the dashboard talks to.
- **Amazon DynamoDB** — a single-table store for inbox items, actions, and memory.
- **Amazon EventBridge Scheduler** — a cron that fires the proactive nudge scan on a schedule.
- **Amazon S3** — static website hosting for the React dashboard.

The flow: the React SPA on S3 calls API Gateway, which invokes a Lambda running FastAPI. That Lambda runs the agent layer, which calls Bedrock (Nova + Titan) and persists everything to DynamoDB. A second Lambda fires on an EventBridge schedule to draft nudges for stale threads. It's fully serverless and pay-per-use, so it idles at essentially zero cost and stays well inside the Free Tier — a personal-assistant workload is a handful of cents of Bedrock tokens and almost nothing else.

## What You Learned

Two lessons stuck with me. First, **interfaces are what make an agentic app shippable.** Hiding Bedrock and DynamoDB behind tiny protocols meant I developed against a mock, wrote fast and deterministic tests, and treated AWS as a deployment target rather than a development dependency. When the Claude model went end-of-life, switching to Nova was a one-line config change because nothing above the LLM interface knew or cared which model was underneath.

Second, **the approval experience *is* the product.** For an assistant that can send email on your behalf, the entire difference between "helpful" and "terrifying" lives in how actions are staged, previewed, edited, and reversed. I ended up spending as much care on the pending-action gate and the veto-teaches-memory loop as on the prompts themselves.

Along the way I also got hands-on with the Bedrock Converse API (one clean call shape across models), Titan embeddings for semantic recall, EventBridge Scheduler for proactive behavior, and a Docker-free way to package compiled Python dependencies for Lambda. The biggest takeaway: a small, well-layered serverless footprint can carry a genuinely "agentic" product a surprisingly long way.

## Link to App or Repo

- **Live app:** http://aide-web-818515814116.s3-website-us-east-1.amazonaws.com
- **Live API health check:** https://h8m79exwpc.execute-api.us-east-1.amazonaws.com/health
- **Source code (public):** https://github.com/suryansh639/Weekend-Productivity-Challenge-Aide-Your-AI-Chief-of-Staff

The repo runs locally in two commands (see the README) — fully offline with a mock LLM and a seeded inbox — and deploys to AWS with the steps in `docs/DEPLOY.md`.
