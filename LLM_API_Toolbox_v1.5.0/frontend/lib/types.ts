export type ProviderStatus = {
  name: string;
  display_name: string;
  status: "available" | "unavailable";
  reason_code: string | null;
  capabilities: ("text" | "streaming")[];
};

export type ModelInfo = {
  id: string;
  display_name: string;
  provider: string;
  capabilities: ("text" | "streaming")[];
  default: boolean;
  max_output_tokens: number | null;
};

export type ProviderConfig = {
  provider: "openai" | "anthropic" | "deepseek";
  display_name: string;
  api_key_configured: boolean;
  base_url: string;
  models: string[];
  persistence: "environment" | "runtime";
};

export type ProviderConfigUpdate = {
  api_key?: string | null;
  clear_api_key: boolean;
  base_url: string;
  models: string[];
};

export type ProviderConnectionTestResult = {
  success: true;
  provider: string;
  model: string;
  latency_ms: number;
};

export type ApiMessage = { role: "user" | "assistant"; content: string };

export type ChatRequest = {
  provider: string;
  model: string;
  messages: ApiMessage[];
  system_prompt: string | null;
  parameters: { temperature: number; max_output_tokens: number; web_search_enabled: boolean };
};

export type Usage = {
  input_tokens: number | null;
  output_tokens: number | null;
  total_tokens: number | null;
};

export type ChatResult = {
  output_text: string;
  provider: string;
  model: string;
  finish_reason: string;
  usage: Usage;
};

export type ErrorDetail = {
  code: string;
  message: string;
  provider?: string | null;
  retryable: boolean;
};

export type ConversationMessage = ApiMessage & {
  id: string;
  status?: "streaming" | "complete" | "cancelled" | "error";
  meta?: { provider: string; model: string; finishReason?: string; usage?: Usage };
};

export type ApplicationMeta = {
  name: string;
  version: string;
  api_compatibility_version: string;
};

export type ConversationSummary = {
  id: string;
  title: string;
  provider: string;
  model: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type StoredMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  status: "complete" | "cancelled" | "error";
  provider: string | null;
  model: string | null;
  finish_reason: string | null;
  usage: Usage | null;
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  system_prompt: string | null;
  temperature: number;
  max_output_tokens: number;
  web_search_enabled: boolean;
  messages: StoredMessage[];
};
