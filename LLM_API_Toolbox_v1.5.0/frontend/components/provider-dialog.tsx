"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiError, testProviderConnection, updateProviderConfig } from "@/lib/api";
import type { ProviderConfig, ProviderConnectionTestResult } from "@/lib/types";
import { CloseIcon, PlusIcon, TrashIcon } from "./icons";

type Props = {
  configs: ProviderConfig[];
  initialProvider: string;
  loading: boolean;
  loadError: string | null;
  onClose: () => void;
  onSaved: (provider: string) => Promise<void>;
};

const testErrorLabels: Record<string, string> = {
  PROVIDER_NOT_CONFIGURED: "请先填写 API Key，再测试连接。",
  PROVIDER_AUTH_FAILED: "API Key 无效或没有访问权限。",
  PROVIDER_PAYMENT_REQUIRED: "账户余额不足，或该账户需要充值后才能调用 API。",
  RATE_LIMITED: "请求频率受限，请稍后再试。",
  PROVIDER_TIMEOUT: "连接超时，请检查网络或 Base URL。",
  PROVIDER_INVALID_REQUEST: "Provider 拒绝了请求，请检查模型名称和 Base URL。",
  PROVIDER_UPSTREAM_ERROR: "无法连接模型服务，请检查网络、代理和 Base URL。",
};

export function ProviderDialog({ configs, initialProvider, loading, loadError, onClose, onSaved }: Props) {
  const first = configs.find((item) => item.provider === initialProvider) ?? configs[0];
  const [active, setActive] = useState<ProviderConfig["provider"]>(first?.provider ?? "openai");
  const selected = configs.find((item) => item.provider === active) ?? first;
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [clearKey, setClearKey] = useState(false);
  const [baseUrl, setBaseUrl] = useState(first?.base_url ?? "");
  const [models, setModels] = useState<string[]>(first?.models ?? [""]);
  const [testModelIndex, setTestModelIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ProviderConnectionTestResult | null>(null);
  const busy = saving || testing;

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !busy) onClose();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [busy, onClose]);

  function resetForm(item: ProviderConfig) {
    setActive(item.provider);
    setApiKey("");
    setShowKey(false);
    setClearKey(false);
    setBaseUrl(item.base_url);
    setModels(item.models.length ? item.models : [""]);
    setTestModelIndex(0);
    setError(null);
    setTestResult(null);
  }

  function updateModel(index: number, value: string) {
    setModels((current) => current.map((model, itemIndex) => itemIndex === index ? value : model));
    setTestResult(null);
  }

  function addModel() {
    setModels((current) => [...current, ""]);
    setTestModelIndex(models.length);
    setTestResult(null);
  }

  function removeModel(index: number) {
    if (models.length === 1) {
      setError("至少需要保留一个模型。");
      return;
    }
    setModels((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setTestModelIndex((current) => current === index ? 0 : current > index ? current - 1 : current);
    setTestResult(null);
  }

  function validModels(): string[] | null {
    const normalized = models.map((item) => item.trim());
    if (!baseUrl.trim() || normalized.some((item) => !item)) {
      setError("请填写接口地址，并确保每一行都有模型名称。");
      return null;
    }
    if (new Set(normalized).size !== normalized.length) {
      setError("模型名称不能重复。");
      return null;
    }
    return normalized;
  }

  async function testConnection() {
    const normalized = validModels();
    if (!normalized) return;
    if (clearKey) {
      setError("已选择删除密钥，无法测试连接。请取消勾选或填写新密钥。");
      return;
    }
    setTesting(true);
    setError(null);
    setTestResult(null);
    try {
      const result = await testProviderConnection(active, {
        api_key: apiKey.trim() || null,
        base_url: baseUrl.trim(),
        model: normalized[Math.min(testModelIndex, normalized.length - 1)],
      });
      setTestResult(result);
    } catch (reason) {
      const detail = reason instanceof ApiError ? reason.detail : null;
      setError(testErrorLabels[detail?.code ?? ""] ?? detail?.message ?? "测试失败，请检查后端连接。");
    } finally {
      setTesting(false);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    const normalized = validModels();
    if (!normalized) return;
    setSaving(true);
    setError(null);
    try {
      await updateProviderConfig(active, {
        api_key: apiKey.trim() || null,
        clear_api_key: clearKey,
        base_url: baseUrl.trim(),
        models: normalized,
      });
      await onSaved(active);
      onClose();
    } catch (reason) {
      const detail = reason instanceof ApiError ? reason.detail : null;
      setError(detail?.message ?? "保存失败，请检查后端连接。");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && !busy && onClose()}>
      <section className="dialog provider-dialog" role="dialog" aria-modal="true" aria-labelledby="provider-dialog-title">
        <header className="dialog-header">
          <div><h2 id="provider-dialog-title">管理模型</h2><p>随时修改服务连接和模型列表；保存后用于当前对话的后续消息。</p></div>
          <button className="icon-button" type="button" onClick={onClose} disabled={busy} aria-label="关闭"><CloseIcon /></button>
        </header>

        {loading && <div className="dialog-state"><span className="loading-ring" /><strong>正在读取模型配置</strong><p>窗口已经打开，请稍候。</p></div>}
        {!loading && loadError && <div className="dialog-state error-state-card"><strong>无法读取模型配置</strong><p>{loadError}</p><code>需要后端版本 1.5.x</code></div>}

        {!loading && !loadError && selected && (
          <>
            <div className="provider-tabs" role="tablist">
              {configs.map((item) => (
                <button key={item.provider} type="button" role="tab" aria-selected={active === item.provider} className={active === item.provider ? "active" : ""} onClick={() => resetForm(item)} disabled={busy}>
                  <span>{item.display_name}</span><small className={item.api_key_configured ? "ready" : "empty"}>{item.api_key_configured ? "已配置" : "未配置"}</small>
                </button>
              ))}
            </div>
            <form className="dialog-form" onSubmit={save}>
              <div className="form-field"><label htmlFor="api-key">API Key</label><div className="secret-field"><input id="api-key" type={showKey ? "text" : "password"} value={apiKey} onChange={(event) => { setApiKey(event.target.value); setClearKey(false); setTestResult(null); }} placeholder={selected.api_key_configured ? "已配置，留空使用现有密钥" : "粘贴 API Key"} autoComplete="off" disabled={busy || clearKey} /><button type="button" onClick={() => setShowKey((value) => !value)} disabled={busy}>{showKey ? "隐藏" : "显示"}</button></div>{selected.api_key_configured && <label className="remove-key"><input type="checkbox" checked={clearKey} onChange={(event) => { setClearKey(event.target.checked); setTestResult(null); }} disabled={busy} />删除现有密钥</label>}</div>
              <div className="form-field"><label htmlFor="base-url">Base URL</label><input id="base-url" value={baseUrl} onChange={(event) => { setBaseUrl(event.target.value); setTestResult(null); }} disabled={busy} /><p>使用官方 API 时保留默认值；兼容网关需要填写其完整接口地址。</p></div>
              <div className="form-field model-editor">
                <div className="model-editor-heading"><div><label>模型名称</label><p>选择其中一个模型用于连接测试。</p></div><button type="button" onClick={addModel} disabled={busy}><PlusIcon size={15} />添加模型</button></div>
                <div className="model-rows">
                  {models.map((item, index) => (
                    <div className="model-row" key={`${active}-${index}`}>
                      <input className="model-test-radio" type="radio" name="test-model" checked={testModelIndex === index} onChange={() => setTestModelIndex(index)} disabled={busy} aria-label={`使用模型 ${index + 1} 测试`} />
                      <input value={item} onChange={(event) => updateModel(index, event.target.value)} placeholder="例如 deepseek-flash" disabled={busy} aria-label={`模型名称 ${index + 1}`} />
                      <button type="button" onClick={() => removeModel(index)} disabled={busy || models.length === 1} aria-label={`删除模型 ${index + 1}`}><TrashIcon size={16} /></button>
                    </div>
                  ))}
                </div>
              </div>
              <div className="info-strip"><strong>仅在当前运行期间保存</strong><span>后端重启后密钥会被清除；测试连接不会保存配置或创建聊天记录，但会发出一次最小模型请求，可能产生少量 API 费用。</span></div>
              {testResult && <div className="connection-result"><span>连接成功</span><strong>{selected.display_name} · {testResult.model}</strong><small>{testResult.latency_ms} ms</small></div>}
              {error && <div className="form-error">{error}</div>}
              <footer className="dialog-actions split-actions"><button className="button test-button" type="button" onClick={() => void testConnection()} disabled={busy}>{testing ? "测试中…" : "测试连接"}</button><div><button className="button secondary" type="button" onClick={onClose} disabled={busy}>取消</button><button className="button primary" type="submit" disabled={busy}>{saving ? "保存中…" : "保存配置"}</button></div></footer>
            </form>
          </>
        )}
      </section>
    </div>
  );
}
