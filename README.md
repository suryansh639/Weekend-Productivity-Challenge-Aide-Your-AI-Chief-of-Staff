# Aide — Your AI Chief-of-Staff

> An agentic productivity assistant that watches your inbox, triages what matters,
> drafts responses, preps you for meetings, and nudges stale follow-ups — while you
> stay in control with a one-click **approve / veto** on every action.

Built for the **AWS Builder Center — Build a Productivity App Weekend Challenge**.

**Live demo:** http://aide-web-818515814116.s3-website-us-east-1.amazonaws.com
· **API:** https://h8m79exwpc.execute-api.us-east-1.amazonaws.com/health

---

## Why it's *agentic*, not just "AI-assisted"

| Capability | What Aide does |
|---|---|
| **Autonomous triage** | Reads every inbox item, classifies urgency (P0–P3), decides if it needs a reply, drafts one, and surfaces only the ~10% that need *you*. |
| **Multi-step execution** | "Prep me for the investor call" → pulls the relevant thread + context, researches, and drafts talking points without you specifying each sub-step. |
| **Memory across sessions** | Remembers tone, recurring contacts, and who you deprioritize — recall is semantic (Bedrock Titan embeddings). |
| **Proactive nudges** | Notices a thread you haven't answered in N days and drafts the nudge itself (scheduled, not on-demand). |
| **Human-in-the-loop** | Nothing is sent or scheduled without your approval. Every action is staged as `pending`. |

## Architecture (AWS serverless)

```
                 ┌──────────────┐     approve / veto      ┌───────────────┐
  React SPA ───► │ API Gateway  │ ──────────────────────► │   DynamoDB    │
 (S3+CloudFront) │  (HTTP API)  │                          │ single table  │
                 └──────┬───────┘                          └──────┬────────┘
                        │ Lambda (FastAPI + Mangum)                │
                        ▼                                          │
              ┌───────────────────┐   Converse / Titan             │
              │  Agent orchestra- │ ─────────────────► Amazon Bedrock (Nova + Titan)
              │  tion (supervisor │
              │  + workers, HITL) │
              └───────────────────┘
                        ▲
        EventBridge Scheduler ──► Nudge Lambda (proactive follow-up detection)
```

See [`ARTICLE.md`](./ARTICLE.md) for the full write-up and [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for detail.

## Quick start (local, no AWS needed)

```bash
# Backend
cd backend
python -m venv .venv
. .venv/Scripts/Activate.ps1        # Windows PowerShell
pip install -e ".[dev]"
python -m app.seed                  # seed the demo inbox
uvicorn app.main:app --reload       # http://localhost:8000/docs

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Runs entirely offline with a deterministic **mock LLM** and a **local JSON store**.
Flip to real AWS by setting environment variables (see `.env.example`).

## Deploy to AWS

```bash
cd infra
sam build && sam deploy --guided
```

Provisions Bedrock access, Lambda, API Gateway, DynamoDB, and the EventBridge nudge
schedule. Frontend deploys to S3 + CloudFront. Full steps in [`docs/DEPLOY.md`](./docs/DEPLOY.md).

## License

MIT
