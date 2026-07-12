// Thin API client. In dev, Vite proxies /api to the backend; in prod set
// VITE_API_BASE to your API Gateway URL at build time.
const BASE = import.meta.env.VITE_API_BASE ?? "";

export type Priority = "P0" | "P1" | "P2" | "P3";

export interface InboxItem {
  id: string;
  channel: "email" | "slack" | "task";
  sender: string;
  sender_email: string;
  subject: string;
  body: string;
  received_at: string;
  triaged: boolean;
  priority: Priority | null;
  category: string | null;
  needs_response: boolean | null;
  summary: string | null;
  reasoning: string | null;
}

export interface Action {
  id: string;
  type: string;
  status: "pending" | "approved" | "rejected" | "executed" | "failed";
  title: string;
  payload: Record<string, string>;
  rationale: string;
  source_item_id: string | null;
  created_at: string;
  result: string | null;
}

export interface Briefing {
  request: string;
  summary: string;
  talking_points: string[];
  context_used: string[];
  proposed_actions: Action[];
}

export interface Stats {
  total_items: number;
  needs_attention: number;
  pending_actions: number;
  auto_handled: number;
}

export interface Memory {
  id: string;
  kind: string;
  text: string;
  created_at: string;
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  stats: () => req<Stats>("/api/stats"),
  seed: () => req("/api/seed", { method: "POST" }),
  inbox: () => req<InboxItem[]>("/api/inbox"),
  attention: () => req<InboxItem[]>("/api/attention"),
  actions: (status?: string) =>
    req<Action[]>("/api/actions" + (status ? `?status=${status}` : "")),
  approve: (id: string, edited_payload?: Record<string, string>) =>
    req<Action>(`/api/actions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ edited_payload: edited_payload ?? null }),
    }),
  reject: (id: string) =>
    req<Action>(`/api/actions/${id}/reject`, { method: "POST" }),
  chat: (message: string) =>
    req<Briefing>("/api/chat", { method: "POST", body: JSON.stringify({ message }) }),
  runNudges: () => req<Action[]>("/api/nudges/run", { method: "POST" }),
  memory: () => req<Memory[]>("/api/memory"),
};
