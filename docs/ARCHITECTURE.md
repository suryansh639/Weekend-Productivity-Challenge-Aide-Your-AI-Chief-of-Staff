# Architecture

Aide is built in clean layers so the agent logic never depends on a specific
LLM, database, or integration. That's what lets it run fully offline for demos
and flip to AWS in production by changing environment variables.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          React SPA (S3 + CloudFront)                     │
│   Attention queue · Inbox · Approve/Veto drafts · Chief-of-Staff chat    │
└───────────────────────────────┬──────────────────────────────────────────┘
                                 │ HTTPS (JSON)
                        ┌────────▼─────────┐
                        │   API Gateway    │  (HTTP API, payload v2)
                        │   ANY /{proxy+}  │
                        └────────┬─────────┘
                                 │
                     ┌───────────▼────────────┐        ┌──────────────────┐
                     │  Lambda: FastAPI+Mangum │        │  Lambda: Nudge    │
                     │  (API use-cases)        │        │  (EventBridge     │
                     └───────────┬────────────┘        │   Scheduler cron) │
                                 │                       └─────────┬────────┘
        ┌────────────────────────┼─────────────────────────────────┘
        │                        │
┌───────▼────────┐   ┌───────────▼───────────┐   ┌────────────────────────┐
│  Agent layer   │   │   Store (interface)    │   │   LLM (interface)      │
│  triage /      │   │  DynamoStore (prod)    │   │  BedrockLLM (prod)     │
│  supervisor /  │   │  LocalStore (dev)      │   │  MockLLM (dev/tests)   │
│  nudges        │   └───────────┬───────────┘   └───────────┬────────────┘
└────────────────┘               │                            │
                          Amazon DynamoDB            Amazon Bedrock (Claude + Titan)
```

## Layers

| Layer | Responsibility | Swap points |
|---|---|---|
| **API** (`app/main.py`) | HTTP surface, validation, CORS, Lambda handler | — |
| **Service** (`app/service.py`) | Use-cases + the human-in-the-loop gate | — |
| **Agents** (`app/agents/`) | Triage worker, Chief-of-Staff supervisor, nudge agent | prompts in one place |
| **Memory** (`app/memory.py`) | Durable prefs/contacts + semantic recall | cosine → pgvector later |
| **LLM** (`app/llm/`) | `complete()` + `embed()` | `mock` ↔ `bedrock` |
| **Store** (`app/store/`) | Items, actions, memory persistence | `local` ↔ `dynamo` |
| **Connectors** (`app/connectors/`) | Source ingestion + action execution | `demo` ↔ `gmail` |

## The human-in-the-loop gate

Every side-effecting action an agent produces is written to the store as
`status=pending`. Nothing is executed until the user calls
`POST /api/actions/{id}/approve` (optionally editing the draft first). Only then
does the service invoke a connector's `execute()`. Vetoes are recorded to memory
so Aide learns what the owner does *not* want sent.

This maps directly onto a LangGraph `interrupt()` before an "execute" node; we
implement it in the service layer to keep the Lambda bundle small and cold starts
fast, which matters on Free Tier.

## Data model (DynamoDB single table)

| pk | sk | doc |
|---|---|---|
| `ITEM` | `<item_id>` | serialized `InboxItem` |
| `ACTION` | `<action_id>` | serialized `Action` |
| `MEM` | `<memory_id>` | serialized `MemoryRecord` |

Records are stored as JSON strings so embedding floats survive without Decimal
juggling. Listing is a `Query` on the partition — cheap and Free-Tier-friendly at
personal-assistant scale.

## Why these choices

- **Serverless** keeps idle cost at zero and stays inside the Free Tier.
- **Bedrock Converse API** gives one clean call shape across models.
- **Provider interfaces** make the whole system demoable offline and testable
  deterministically, which was essential for shipping in a weekend.
