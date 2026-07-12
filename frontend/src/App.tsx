import { useEffect, useState } from "react";
import { api, Action, Briefing, InboxItem, Memory, Stats } from "./api";

function Badge({ p }: { p: string | null }) {
  if (!p) return null;
  return <span className={`badge ${p}`}>{p}</span>;
}

function ItemView({ item }: { item: InboxItem }) {
  return (
    <div className="item">
      <div className="row">
        <Badge p={item.priority} />
        <span className="subj">{item.subject}</span>
        {item.category && <span className="chip">{item.category}</span>}
      </div>
      <div className="from">
        {item.sender} · {item.channel}
        {item.needs_response && <span className="needs"> · needs reply</span>}
      </div>
      {item.summary && <div className="sum">{item.summary}</div>}
      {item.reasoning && <div className="why">Aide: {item.reasoning}</div>}
    </div>
  );
}

function ActionCard({ action, onDone }: { action: Action; onDone: () => void }) {
  const [body, setBody] = useState(action.payload.body ?? "");
  const [busy, setBusy] = useState(false);
  const resolved = action.status !== "pending";

  async function approve() {
    setBusy(true);
    try {
      await api.approve(action.id, body !== action.payload.body ? { body } : undefined);
      onDone();
    } finally {
      setBusy(false);
    }
  }
  async function reject() {
    setBusy(true);
    try {
      await api.reject(action.id);
      onDone();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="item action">
      <div className="row">
        <span className="type-tag">{action.type}</span>
        <span className="title" style={{ flex: 1 }}>{action.title}</span>
        {resolved && <span className={`status ${action.status}`}>{action.status}</span>}
      </div>
      <div className="why">{action.rationale}</div>
      {action.payload.to && <div className="meta">To: {action.payload.to}</div>}
      {!resolved ? (
        <>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} />
          <div className="actions">
            <button className="btn ok" onClick={approve} disabled={busy}>
              ✓ Approve & send
            </button>
            <button className="btn danger" onClick={reject} disabled={busy}>
              ✕ Veto
            </button>
          </div>
        </>
      ) : (
        action.result && <div className="meta">{action.result}</div>
      )}
    </div>
  );
}

interface ChatMsg { role: "me" | "aide"; text: string; brief?: Briefing; }

function Chat({ onAction }: { onAction: () => void }) {
  const [log, setLog] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  async function send() {
    const msg = input.trim();
    if (!msg || busy) return;
    setInput("");
    setLog((l) => [...l, { role: "me", text: msg }]);
    setBusy(true);
    try {
      const brief = await api.chat(msg);
      setLog((l) => [...l, { role: "aide", text: brief.summary, brief }]);
      if (brief.proposed_actions.length) onAction();
    } catch {
      setLog((l) => [...l, { role: "aide", text: "Something went wrong reaching the agent." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel chat">
      <h2>💬 Ask your Chief-of-Staff</h2>
      <div className="log">
        {log.length === 0 && (
          <div className="empty">
            Try: “Prep me for the Series A follow-up and draft an email”.
          </div>
        )}
        {log.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
            {m.brief && m.brief.talking_points.length > 0 && (
              <ul>{m.brief.talking_points.map((t, j) => <li key={j}>{t}</li>)}</ul>
            )}
            {m.brief && m.brief.context_used.length > 0 && (
              <div className="ctx">Context: {m.brief.context_used.join(" · ")}</div>
            )}
            {m.brief && m.brief.proposed_actions.length > 0 && (
              <div className="ctx">
                ↳ Drafted {m.brief.proposed_actions.length} action for your approval →
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="composer">
        <input
          value={input}
          placeholder="Ask Aide to prep, draft, or follow up…"
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn primary" onClick={send} disabled={busy}>
          {busy ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [attention, setAttention] = useState<InboxItem[]>([]);
  const [inbox, setInbox] = useState<InboxItem[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [memory, setMemory] = useState<Memory[]>([]);
  const [tab, setTab] = useState<"attention" | "all">("attention");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    const [s, at, ib, ac, me] = await Promise.all([
      api.stats(), api.attention(), api.inbox(), api.actions(), api.memory(),
    ]);
    setStats(s); setAttention(at); setInbox(ib); setActions(ac); setMemory(me);
    setLoading(false);
  }

  useEffect(() => {
    (async () => {
      try {
        const s = await api.stats();
        if (s.total_items === 0) await api.seed();
      } catch { /* backend may seed lazily */ }
      refresh();
    })();
  }, []);

  async function reseed() {
    setLoading(true);
    await api.seed();
    await refresh();
  }
  async function runNudges() {
    await api.runNudges();
    await refresh();
  }

  const pending = actions.filter((a) => a.status === "pending");
  const resolved = actions.filter((a) => a.status !== "pending");

  return (
    <div className="app">
      <header className="top">
        <div className="brand">
          <div className="logo">A</div>
          <div>
            <h1>Aide</h1>
            <p>Your AI Chief-of-Staff · triage · prep · proactive nudges</p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn" onClick={runNudges}>Run nudge scan</button>
          <button className="btn primary" onClick={reseed}>Reseed demo</button>
        </div>
      </header>

      <div className="banner">
        Aide read your inbox, handled the routine, and surfaced only what needs you.
        Nothing is sent without your approval — review the drafts on the right.
      </div>

      <div className="stats">
        <div className="stat"><div className="n">{stats?.total_items ?? "–"}</div><div className="l">Items processed</div></div>
        <div className="stat attention"><div className="n">{stats?.needs_attention ?? "–"}</div><div className="l">Need your attention</div></div>
        <div className="stat pending"><div className="n">{stats?.pending_actions ?? "–"}</div><div className="l">Drafts awaiting approval</div></div>
        <div className="stat handled"><div className="n">{stats?.auto_handled ?? "–"}</div><div className="l">Auto-handled</div></div>
      </div>

      <div className="grid">
        <div>
          <div className="panel">
            <div className="tabs">
              <div className={`tab ${tab === "attention" ? "active" : ""}`} onClick={() => setTab("attention")}>
                Needs attention ({attention.length})
              </div>
              <div className={`tab ${tab === "all" ? "active" : ""}`} onClick={() => setTab("all")}>
                All inbox ({inbox.length})
              </div>
            </div>
            {loading && <div className="empty">Loading…</div>}
            {!loading && (tab === "attention" ? attention : inbox).map((i) => (
              <ItemView key={i.id} item={i} />
            ))}
            {!loading && tab === "attention" && attention.length === 0 && (
              <div className="empty">Inbox zero. Aide handled everything.</div>
            )}
          </div>

          <div className="panel">
            <h2>🧠 What Aide remembers <span className="count">{memory.length}</span></h2>
            {memory.slice(0, 8).map((m) => (
              <div key={m.id} className="mem"><span className="k">{m.kind}</span>{m.text}</div>
            ))}
            {memory.length === 0 && <div className="empty">No memories yet.</div>}
          </div>
        </div>

        <div>
          <Chat onAction={refresh} />

          <div className="panel">
            <h2>📝 Drafts awaiting approval <span className="count">{pending.length}</span></h2>
            {pending.length === 0 && <div className="empty">No pending drafts.</div>}
            {pending.map((a) => <ActionCard key={a.id} action={a} onDone={refresh} />)}
          </div>

          {resolved.length > 0 && (
            <div className="panel">
              <h2>✅ Recently resolved <span className="count">{resolved.length}</span></h2>
              {resolved.slice(0, 6).map((a) => <ActionCard key={a.id} action={a} onDone={refresh} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
