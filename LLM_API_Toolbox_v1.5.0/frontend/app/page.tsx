"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import { GenerationDialog } from "@/components/generation-dialog";
import { HistorySidebar } from "@/components/history-sidebar";
import { ArrowUpIcon, GearIcon, MenuIcon, SlidersIcon, SparkleIcon, StopIcon } from "@/components/icons";
import { ProviderDialog } from "@/components/provider-dialog";
import {
  ApiError,
  appendConversationMessage,
  createConversation,
  deleteConversation,
  fetchApplicationMeta,
  fetchConversation,
  fetchConversations,
  fetchModels,
  fetchProviderConfigs,
  fetchProviders,
  renameConversation,
  sendChat,
  streamChat,
  updateConversationSettings,
} from "@/lib/api";
import { selectModelAfterConfig } from "@/lib/model-selection";
import type { ChatRequest, ConversationMessage, ConversationSummary, ModelInfo, ProviderConfig, ProviderStatus, Usage } from "@/lib/types";

const FRONTEND_COMPATIBILITY = "1.5";

const errorLabels: Record<string, string> = {
  PROVIDER_NOT_CONFIGURED: "该服务尚未配置 API 密钥，请打开接口配置完成设置。",
  PROVIDER_AUTH_FAILED: "API 密钥无效或没有访问权限。",
  PROVIDER_PAYMENT_REQUIRED: "账户余额不足，请充值后再试。",
  RATE_LIMITED: "请求过于频繁，请稍后再试。",
  PROVIDER_TIMEOUT: "模型服务响应超时，请重试。",
  PROVIDER_UPSTREAM_ERROR: "模型服务暂时不可用。",
  PROVIDER_INVALID_REQUEST: "Provider 拒绝了请求，请检查模型名称和接口地址。",
  WEB_SEARCH_FAILED: "联网搜索暂时不可用，请检查网络，或关闭联网搜索后重试。",
  MODEL_NOT_FOUND: "当前模型未在该 Provider 中配置。",
  VALIDATION_ERROR: "请求参数不符合要求，请检查输入。",
};

function newId(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function TokenUsage({ usage }: { usage?: Usage }) {
  if (!usage || (usage.input_tokens == null && usage.output_tokens == null)) return null;
  return <span>输入 {usage.input_tokens ?? "—"} · 输出 {usage.output_tokens ?? "—"} tokens</span>;
}

function LinkifiedText({ text }: { text: string }) {
  return <>{text.split(/(https?:\/\/[^\s]+)/g).map((part, index) => part.startsWith("http://") || part.startsWith("https://")
    ? <a key={`${part}-${index}`} href={part} target="_blank" rel="noreferrer">{part}</a>
    : part)}</>;
}

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendStatus, setBackendStatus] = useState<"connected" | "outdated" | "offline">("offline");
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [provider, setProvider] = useState("mock");
  const [model, setModel] = useState("mock-echo-v1");
  const [systemPrompt, setSystemPrompt] = useState("你是一个简洁、可靠的助手。");
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(1024);
  const [streaming, setStreaming] = useState(true);
  const [webSearchEnabled, setWebSearchEnabled] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [activeTitle, setActiveTitle] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [providerDialogOpen, setProviderDialogOpen] = useState(false);
  const [providerConfigs, setProviderConfigs] = useState<ProviderConfig[]>([]);
  const [configLoading, setConfigLoading] = useState(false);
  const [configError, setConfigError] = useState<string | null>(null);
  const [generationDialogOpen, setGenerationDialogOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const selectedProvider = useMemo(() => providers.find((item) => item.name === provider), [provider, providers]);

  useEffect(() => {
    fetchProviders()
      .then((items) => {
        setProviders(items);
        const preferred = items.find((item) => item.name !== "mock" && item.status === "available") ?? items.find((item) => item.name === "mock") ?? items[0];
        if (preferred) setProvider(preferred.name);
        return fetchApplicationMeta();
      })
      .then((meta) => setBackendStatus(meta.api_compatibility_version === FRONTEND_COMPATIBILITY ? "connected" : "outdated"))
      .catch(() => {
        fetchProviders().then(() => setBackendStatus("outdated")).catch(() => setBackendStatus("offline"));
      });

    fetchConversations().then(setConversations).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!provider) return;
    fetchModels(provider)
      .then((items) => {
        setModels(items);
        setModel((current) => items.some((item) => item.id === current) ? current : items.find((item) => item.default)?.id ?? items[0]?.id ?? "");
      })
      .catch(() => setModels([]));
  }, [provider]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      fetchConversations(search).then(setConversations).catch(() => undefined);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function refreshHistory() {
    setConversations(await fetchConversations(search));
  }

  function newConversation() {
    if (loading) abortRef.current?.abort();
    setActiveConversationId(null);
    setActiveTitle(null);
    setMessages([]);
    setInput("");
    setNotice(null);
    if (window.innerWidth <= 840) setSidebarOpen(false);
  }

  async function selectConversation(id: string) {
    if (loading || id === activeConversationId) return;
    setLoadingConversation(true);
    setNotice(null);
    try {
      const detail = await fetchConversation(id);
      setActiveConversationId(id);
      setActiveTitle(detail.title);
      setProvider(detail.provider);
      setModel(detail.model);
      setSystemPrompt(detail.system_prompt ?? "");
      setTemperature(detail.temperature);
      setMaxTokens(detail.max_output_tokens);
      setWebSearchEnabled(detail.web_search_enabled);
      setMessages(detail.messages.map((item) => ({
        id: item.id,
        role: item.role,
        content: item.content,
        status: item.status,
        meta: item.role === "assistant" && item.provider && item.model
          ? { provider: item.provider, model: item.model, finishReason: item.finish_reason ?? undefined, usage: item.usage ?? undefined }
          : undefined,
      })));
      if (window.innerWidth <= 840) setSidebarOpen(false);
    } catch {
      setNotice("无法加载这条会话，请确认后端仍在运行。");
    } finally {
      setLoadingConversation(false);
    }
  }

  async function handleRename(id: string, title: string) {
    try {
      await renameConversation(id, title);
      if (id === activeConversationId) setActiveTitle(title);
      await refreshHistory();
    } catch {
      setNotice("重命名失败，请检查后端连接。");
    }
  }

  async function handleDelete(id: string) {
    await deleteConversation(id);
    if (activeConversationId === id) newConversation();
    await refreshHistory();
  }

  function openProviderDialog() {
    setProviderDialogOpen(true);
    setConfigLoading(true);
    setConfigError(null);
    fetchProviderConfigs()
      .then((items) => setProviderConfigs(items))
      .catch(() => setConfigError(backendStatus === "outdated" ? "当前运行的是旧版后端，请停止旧进程并从 V1.5.0 的 backend 目录重新启动。" : "无法连接后端，请确认 8000 端口的服务已启动。"))
      .finally(() => setConfigLoading(false));
  }

  async function handleProviderSaved(savedProvider: string) {
    const refreshedProviders = await fetchProviders();
    setProviders(refreshedProviders);
    if (provider !== savedProvider && provider !== "mock") {
      setNotice(`${savedProvider} 配置已保存，当前对话仍使用 ${provider}。`);
      return;
    }
    const refreshedModels = await fetchModels(savedProvider);
    const selection = selectModelAfterConfig(refreshedModels, model);
    setModels(refreshedModels);
    if (provider === "mock") setProvider(savedProvider);
    setModel(selection.model);
    setNotice(selection.preserved
      ? `${savedProvider} 配置已保存，当前模型保持不变。`
      : `${savedProvider} 配置已保存；原模型已不存在，已切换为 ${selection.model || "列表中的第一个模型"}。`);
  }

  function updateAssistant(id: string, updater: (message: ConversationMessage) => ConversationMessage) {
    setMessages((current) => current.map((message) => message.id === id ? updater(message) : message));
  }

  async function handleSubmit(event?: FormEvent) {
    event?.preventDefault();
    const content = input.trim();
    if (!content || loading || !model) return;
    if (backendStatus !== "connected") {
      setNotice(backendStatus === "outdated" ? "前后端版本不匹配，请重新启动 V1.5.0 后端。" : "后端未连接。");
      return;
    }
    if (selectedProvider?.status !== "available") {
      setNotice("当前模型服务尚未配置，请先填写 API Key。");
      openProviderDialog();
      return;
    }

    setNotice(null);
    let conversationId = activeConversationId;
    try {
      if (!conversationId) {
        const created = await createConversation({ provider, model, system_prompt: systemPrompt.trim() || null, temperature, max_output_tokens: maxTokens, web_search_enabled: webSearchEnabled });
        conversationId = created.id;
        setActiveConversationId(created.id);
        setActiveTitle(created.title);
      } else {
        await updateConversationSettings(conversationId, { provider, model, system_prompt: systemPrompt.trim() || null, temperature, max_output_tokens: maxTokens, web_search_enabled: webSearchEnabled });
      }
      await appendConversationMessage(conversationId, { role: "user", content });
      if (!activeConversationId) setActiveTitle(content.trim().replace(/\s+/g, " ").slice(0, 36) || "新对话");
    } catch (error) {
      const detail = error instanceof ApiError ? error.detail : null;
      setNotice(detail ? (errorLabels[detail.code] ?? detail.message) : "无法保存会话，请检查后端连接。");
      return;
    }

    const userMessage: ConversationMessage = { id: newId("user"), role: "user", content, status: "complete" };
    const assistantId = newId("assistant");
    const assistantMessage: ConversationMessage = { id: assistantId, role: "assistant", content: "", status: "streaming", meta: { provider, model } };
    const contextMessages = [...messages.filter((item) => item.status !== "error"), userMessage].map(({ role, content: body }) => ({ role, content: body }));
    const payload: ChatRequest = { provider, model, messages: contextMessages, system_prompt: systemPrompt.trim() || null, parameters: { temperature, max_output_tokens: maxTokens, web_search_enabled: webSearchEnabled } };
    setInput("");
    setMessages((current) => [...current, userMessage, assistantMessage]);
    setLoading(true);
    const controller = new AbortController();
    abortRef.current = controller;
    let assistantText = "";
    let finalUsage: Usage | undefined;
    let finishReason: string | undefined;

    try {
      if (streaming) {
        await streamChat(payload, controller.signal, {
          onMeta: (meta) => updateAssistant(assistantId, (item) => ({ ...item, meta: { provider: meta.provider, model: meta.model } })),
          onDelta: (delta) => { assistantText += delta; updateAssistant(assistantId, (item) => ({ ...item, content: item.content + delta })); },
          onDone: (data) => {
            finalUsage = data.usage;
            finishReason = data.finish_reason;
            updateAssistant(assistantId, (item) => ({ ...item, status: "complete", meta: { ...item.meta!, finishReason, usage: finalUsage } }));
          },
        });
      } else {
        const result = await sendChat(payload, controller.signal);
        assistantText = result.output_text;
        finalUsage = result.usage;
        finishReason = result.finish_reason;
        updateAssistant(assistantId, (item) => ({ ...item, content: assistantText, status: "complete", meta: { provider: result.provider, model: result.model, finishReason, usage: finalUsage } }));
      }
      if (assistantText) await appendConversationMessage(conversationId, { role: "assistant", content: assistantText, provider, model, finish_reason: finishReason, usage: finalUsage });
    } catch (error) {
      if (controller.signal.aborted) {
        const cancelledText = assistantText || "生成已取消。";
        updateAssistant(assistantId, (item) => ({ ...item, content: cancelledText, status: "cancelled" }));
        await appendConversationMessage(conversationId, { role: "assistant", content: cancelledText, status: "cancelled", provider, model });
      } else {
        const detail = error instanceof ApiError ? error.detail : null;
        const errorText = errorLabels[detail?.code ?? ""] ?? "请求失败，请检查模型配置后重试。";
        updateAssistant(assistantId, (item) => ({ ...item, content: errorText, status: "error" }));
        await appendConversationMessage(conversationId, { role: "assistant", content: errorText, status: "error", provider, model });
      }
    } finally {
      abortRef.current = null;
      setLoading(false);
      await refreshHistory().catch(() => undefined);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void handleSubmit(); }
  }

  return (
    <main className={`app-frame ${sidebarOpen ? "" : "sidebar-hidden"}`}>
      <HistorySidebar open={sidebarOpen} conversations={conversations} activeId={activeConversationId} search={search} backendStatus={backendStatus} onSearch={setSearch} onNew={newConversation} onSelect={(id) => void selectConversation(id)} onRename={handleRename} onDelete={async (id) => setPendingDeleteId(id)} onSettings={openProviderDialog} onClose={() => setSidebarOpen(false)} />

      <section className="chat-workspace">
        <header className="chat-header">
          <div className="chat-header-left">{!sidebarOpen && <button className="header-icon-button sidebar-open-button" type="button" onClick={() => setSidebarOpen(true)} aria-label="打开会话列表"><MenuIcon /></button>}<div className="conversation-heading"><strong>{activeTitle ?? "新对话"}</strong><span>{messages.length ? `${messages.length} 条消息` : "开始一段新的对话"}</span></div></div>
          <div className="chat-header-controls">
            <select className="provider-select" value={provider} onChange={(event) => setProvider(event.target.value)} disabled={loading} aria-label="Provider">{providers.map((item) => <option key={item.name} value={item.name}>{item.display_name}{item.status === "unavailable" ? "（未配置）" : ""}</option>)}</select>
            <select className="model-select" value={model} onChange={(event) => setModel(event.target.value)} disabled={loading || models.length === 0} aria-label="模型">{models.map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select>
            <button className="model-manage-button" type="button" onClick={openProviderDialog} disabled={loading} aria-label="管理模型"><GearIcon size={16} /><span>管理模型</span></button>
            <button className="header-icon-button" type="button" onClick={() => setGenerationDialogOpen(true)} disabled={loading} aria-label="生成设置" title="生成设置"><SlidersIcon /></button>
          </div>
        </header>

        <div className="conversation-view" aria-live="polite">
          {notice && <div className="notice-banner"><span>{notice}</span><button type="button" onClick={() => setNotice(null)}>关闭</button></div>}
          {backendStatus !== "connected" && <div className="compatibility-banner"><strong>{backendStatus === "outdated" ? "前后端版本不匹配" : "后端未连接"}</strong><span>{backendStatus === "outdated" ? "当前页面需要 V1.5.0 后端。请停止旧后端并从新版 backend 目录重新启动。" : "请确认 FastAPI 已在 localhost:8000 启动。"}</span></div>}
          {loadingConversation && <div className="center-state"><span className="loading-ring" />正在加载会话</div>}
          {!loadingConversation && messages.length === 0 && (
            <div className="empty-conversation"><div className="empty-mark"><SparkleIcon size={26} /></div><h1>有什么可以帮你？</h1><p>选择已经配置的模型，然后开始一段对话。会话记录只保存在这台电脑上。</p><div className="empty-actions"><button type="button" onClick={openProviderDialog}>管理模型</button><button type="button" onClick={() => setGenerationDialogOpen(true)}>调整生成设置</button></div></div>
          )}
          {!loadingConversation && messages.length > 0 && <div className="message-column">
            {messages.map((message) => (
              <article className={`chat-message ${message.role} ${message.status === "error" ? "error" : ""}`} key={message.id}>
                <div className="message-identity"><span>{message.role === "user" ? "你" : <SparkleIcon size={15} />}</span><strong>{message.role === "user" ? "你" : "助手"}</strong>{message.status === "streaming" && <small>正在生成</small>}{message.status === "cancelled" && <small>已停止</small>}{message.status === "error" && <small>请求失败</small>}</div>
                <div className="message-text">{message.content ? <LinkifiedText text={message.content} /> : <span className="typing-cursor" />}</div>
                {message.meta && (
                  <div className="message-meta">
                    <span>{message.meta.provider} · {message.meta.model}</span>
                    <TokenUsage usage={message.meta.usage} />
                    {message.content && <button type="button" onClick={() => navigator.clipboard.writeText(message.content)}>复制</button>}
                  </div>
                )}
              </article>
            ))}
            <div ref={endRef} />
          </div>}
        </div>

        <div className="composer-area">
          <form className="chat-composer" onSubmit={handleSubmit}>
            <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleKeyDown} placeholder="发送消息…" rows={2} disabled={loading || loadingConversation} aria-label="对话消息" />
            <div className="composer-footer"><span>{selectedProvider?.display_name ?? "未连接"} · {model || "未选择模型"}{webSearchEnabled ? " · 联网" : ""}</span>{loading ? <button className="composer-stop" type="button" onClick={() => abortRef.current?.abort()}><StopIcon size={16} />停止</button> : <button className="composer-send" type="submit" disabled={!input.trim() || backendStatus !== "connected" || selectedProvider?.status !== "available"} aria-label="发送消息"><ArrowUpIcon size={17} /></button>}</div>
          </form>
          <p className="composer-disclaimer">模型可能会生成不准确的信息，请核对重要内容。</p>
        </div>
      </section>

      {providerDialogOpen && <ProviderDialog key={`${configLoading}-${providerConfigs.length}-${configError ?? "ok"}`} configs={providerConfigs} initialProvider={provider === "mock" ? "openai" : provider} loading={configLoading} loadError={configError} onClose={() => setProviderDialogOpen(false)} onSaved={handleProviderSaved} />}
      {generationDialogOpen && <GenerationDialog systemPrompt={systemPrompt} temperature={temperature} maxTokens={maxTokens} streaming={streaming} webSearchEnabled={webSearchEnabled} onSystemPrompt={setSystemPrompt} onTemperature={setTemperature} onMaxTokens={setMaxTokens} onStreaming={setStreaming} onWebSearchEnabled={setWebSearchEnabled} onClose={() => setGenerationDialogOpen(false)} />}
      {pendingDeleteId && (
        <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && setPendingDeleteId(null)}>
          <section className="dialog confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title">
            <h2 id="delete-title">删除这条会话？</h2>
            <p>“{conversations.find((item) => item.id === pendingDeleteId)?.title ?? "未命名会话"}”及其中的所有消息都会从本机永久删除。</p>
            <div className="dialog-actions"><button className="button secondary" type="button" onClick={() => setPendingDeleteId(null)}>取消</button><button className="button danger" type="button" onClick={() => void handleDelete(pendingDeleteId).then(() => setPendingDeleteId(null)).catch(() => setNotice("删除失败，请检查后端连接。"))}>删除</button></div>
          </section>
        </div>
      )}
    </main>
  );
}
