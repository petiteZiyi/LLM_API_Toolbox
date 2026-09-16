import { parseSSEStream } from "./sse";
import type { ApplicationMeta, ChatRequest, ChatResult, ConversationDetail, ConversationSummary, ErrorDetail, ModelInfo, ProviderConfig, ProviderConfigUpdate, ProviderConnectionTestResult, ProviderStatus, StoredMessage, Usage } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public detail: ErrorDetail, public requestId?: string) {
    super(detail.message);
  }
}

async function requireOk(response: Response): Promise<Response> {
  if (response.ok) return response;
  const body = await response.json().catch(() => null);
  throw new ApiError(
    body?.error ?? { code: "NETWORK_ERROR", message: "请求失败。", retryable: false },
    body?.request_id,
  );
}

export async function fetchProviders(): Promise<ProviderStatus[]> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/providers`, { cache: "no-store" }));
  return (await response.json()).providers;
}

export async function fetchApplicationMeta(): Promise<ApplicationMeta> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/meta`, { cache: "no-store" }));
  return response.json();
}

export async function fetchModels(provider: string): Promise<ModelInfo[]> {
  const response = await requireOk(
    await fetch(`${API_BASE}/api/v1/models?provider=${encodeURIComponent(provider)}`, { cache: "no-store" }),
  );
  return (await response.json()).models;
}

export async function fetchProviderConfigs(): Promise<ProviderConfig[]> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/settings/providers`, { cache: "no-store" }));
  return (await response.json()).providers;
}

export async function updateProviderConfig(
  provider: string,
  payload: ProviderConfigUpdate,
): Promise<ProviderConfig> {
  const response = await requireOk(
    await fetch(`${API_BASE}/api/v1/settings/providers/${encodeURIComponent(provider)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
  return (await response.json()).provider;
}

export async function testProviderConnection(
  provider: string,
  payload: { api_key?: string | null; base_url: string; model: string },
): Promise<ProviderConnectionTestResult> {
  const response = await requireOk(
    await fetch(`${API_BASE}/api/v1/settings/providers/${encodeURIComponent(provider)}/test`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  );
  return response.json();
}

export async function fetchConversations(query = ""): Promise<ConversationSummary[]> {
  const suffix = query ? `?query=${encodeURIComponent(query)}` : "";
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations${suffix}`, { cache: "no-store" }));
  return (await response.json()).conversations;
}

export async function createConversation(payload: {
  provider: string;
  model: string;
  system_prompt: string | null;
  temperature: number;
  max_output_tokens: number;
  web_search_enabled: boolean;
}): Promise<ConversationDetail> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  return (await response.json()).conversation;
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations/${encodeURIComponent(id)}`, { cache: "no-store" }));
  return (await response.json()).conversation;
}

export async function renameConversation(id: string, title: string): Promise<ConversationDetail> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  }));
  return (await response.json()).conversation;
}

export async function updateConversationSettings(id: string, payload: {
  provider: string;
  model: string;
  system_prompt: string | null;
  temperature: number;
  max_output_tokens: number;
  web_search_enabled: boolean;
}): Promise<ConversationDetail> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  return (await response.json()).conversation;
}

export async function deleteConversation(id: string): Promise<void> {
  await requireOk(await fetch(`${API_BASE}/api/v1/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }));
}

export async function appendConversationMessage(
  conversationId: string,
  payload: {
    role: "user" | "assistant";
    content: string;
    status?: "complete" | "cancelled" | "error";
    provider?: string | null;
    model?: string | null;
    finish_reason?: string | null;
    usage?: Usage | null;
  },
): Promise<StoredMessage> {
  const response = await requireOk(await fetch(`${API_BASE}/api/v1/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  return (await response.json()).message;
}

export async function sendChat(payload: ChatRequest, signal: AbortSignal): Promise<ChatResult> {
  const response = await requireOk(
    await fetch(`${API_BASE}/api/v1/chat/completions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    }),
  );
  return (await response.json()).data;
}

export async function streamChat(
  payload: ChatRequest,
  signal: AbortSignal,
  callbacks: {
    onMeta: (data: { request_id: string; provider: string; model: string; seq: number }) => void;
    onDelta: (delta: string) => void;
    onDone: (data: { finish_reason: string; usage: Usage }) => void;
  },
): Promise<void> {
  const response = await requireOk(
    await fetch(`${API_BASE}/api/v1/chat/completions/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    }),
  );
  if (!response.body) {
    throw new ApiError({ code: "EMPTY_STREAM", message: "服务器没有返回数据流。", retryable: true });
  }
  for await (const item of parseSSEStream(response.body)) {
    const data = item.data as Record<string, unknown>;
    if (item.event === "meta") callbacks.onMeta(data as never);
    else if (item.event === "delta") callbacks.onDelta(String(data.delta ?? ""));
    else if (item.event === "done") callbacks.onDone(data as never);
    else if (item.event === "error") throw new ApiError(data.error as ErrorDetail);
  }
}
