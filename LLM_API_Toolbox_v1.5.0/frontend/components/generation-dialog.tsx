"use client";

import { useEffect } from "react";
import { CloseIcon } from "./icons";

type Props = {
  systemPrompt: string;
  temperature: number;
  maxTokens: number;
  streaming: boolean;
  webSearchEnabled: boolean;
  onSystemPrompt: (value: string) => void;
  onTemperature: (value: number) => void;
  onMaxTokens: (value: number) => void;
  onStreaming: (value: boolean) => void;
  onWebSearchEnabled: (value: boolean) => void;
  onClose: () => void;
};

export function GenerationDialog(props: Props) {
  useEffect(() => {
    const escape = (event: KeyboardEvent) => event.key === "Escape" && props.onClose();
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [props]);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && props.onClose()}>
      <section className="dialog generation-dialog" role="dialog" aria-modal="true" aria-labelledby="generation-title">
        <header className="dialog-header"><div><h2 id="generation-title">生成设置</h2><p>这些参数会用于当前对话中的后续请求。</p></div><button className="icon-button" type="button" onClick={props.onClose} aria-label="关闭"><CloseIcon /></button></header>
        <div className="dialog-form">
          <div className="form-field"><label htmlFor="system-prompt">System prompt</label><textarea id="system-prompt" rows={5} value={props.systemPrompt} onChange={(event) => props.onSystemPrompt(event.target.value)} /></div>
          <div className="form-field"><div className="field-title"><label htmlFor="temperature">Temperature</label><output>{props.temperature.toFixed(1)}</output></div><input id="temperature" type="range" min="0" max="2" step="0.1" value={props.temperature} onChange={(event) => props.onTemperature(Number(event.target.value))} /><p>数值越低回答越稳定，数值越高回答越发散。</p></div>
          <div className="form-field"><label htmlFor="max-tokens">最大输出 tokens</label><input id="max-tokens" type="number" min="1" max="8192" value={props.maxTokens} onChange={(event) => props.onMaxTokens(Number(event.target.value))} /></div>
          <label className="setting-row"><span><strong>流式输出</strong><small>逐步显示模型生成内容</small></span><input type="checkbox" checked={props.streaming} onChange={(event) => props.onStreaming(event.target.checked)} /></label>
          <label className="setting-row"><span><strong>允许联网搜索</strong><small>每次提问前搜索公开网页，再将结果交给当前模型</small></span><input type="checkbox" checked={props.webSearchEnabled} onChange={(event) => props.onWebSearchEnabled(event.target.checked)} /></label>
          <footer className="dialog-actions"><button className="button primary" type="button" onClick={props.onClose}>完成</button></footer>
        </div>
      </section>
    </div>
  );
}
