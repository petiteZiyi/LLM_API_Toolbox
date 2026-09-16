"use client";

import { FormEvent, useMemo, useState } from "react";
import type { ConversationSummary } from "@/lib/types";
import { CloseIcon, EditIcon, PlusIcon, SearchIcon, SettingsIcon, TrashIcon } from "./icons";

type Props = {
  open: boolean;
  conversations: ConversationSummary[];
  activeId: string | null;
  search: string;
  backendStatus: "connected" | "outdated" | "offline";
  onSearch: (value: string) => void;
  onNew: () => void;
  onSelect: (id: string) => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  onSettings: () => void;
  onClose: () => void;
};

function dayStart(date: Date) { return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime(); }

function groupLabel(timestamp: string) {
  const today = dayStart(new Date());
  const target = dayStart(new Date(timestamp));
  const days = Math.round((today - target) / 86_400_000);
  if (days <= 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 7) return "最近 7 天";
  if (days < 30) return "最近 30 天";
  return "更早";
}

export function HistorySidebar(props: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const groups = useMemo(() => {
    const result = new Map<string, ConversationSummary[]>();
    for (const item of props.conversations) {
      const label = groupLabel(item.updated_at);
      result.set(label, [...(result.get(label) ?? []), item]);
    }
    return [...result.entries()];
  }, [props.conversations]);

  async function submitRename(event: FormEvent, id: string) {
    event.preventDefault();
    const title = draftTitle.trim();
    if (title) await props.onRename(id, title);
    setEditingId(null);
  }

  return (
    <>
      <aside className={`history-sidebar ${props.open ? "open" : ""}`} aria-label="会话历史">
        <div className="sidebar-header"><div className="wordmark"><span>LL</span><strong>LLM Toolbox</strong></div><button className="sidebar-close" type="button" onClick={props.onClose} aria-label="关闭侧栏"><CloseIcon /></button></div>
        <button className="new-chat-button" type="button" onClick={props.onNew}><PlusIcon /><span>新建对话</span></button>
        <label className="history-search"><SearchIcon /><input value={props.search} onChange={(event) => props.onSearch(event.target.value)} placeholder="搜索会话" aria-label="搜索会话" /></label>

        <div className="history-scroll">
          {groups.length === 0 && <div className="history-empty"><span>还没有会话记录</span><small>{props.search ? "没有找到匹配内容" : "发送第一条消息后会自动保存"}</small></div>}
          {groups.map(([label, items]) => (
            <section className="history-group" key={label}><h2>{label}</h2><div className="history-items">
              {items.map((item) => (
                <div className={`history-item ${props.activeId === item.id ? "active" : ""}`} key={item.id}>
                  {editingId === item.id ? (
                    <form className="rename-form" onSubmit={(event) => void submitRename(event, item.id)}><input autoFocus value={draftTitle} onChange={(event) => setDraftTitle(event.target.value)} onBlur={() => setEditingId(null)} maxLength={120} /></form>
                  ) : (
                    <button className="history-select" type="button" onClick={() => props.onSelect(item.id)}><span>{item.title}</span><small>{item.provider} · {item.message_count} 条消息</small></button>
                  )}
                  {editingId !== item.id && <div className="history-actions"><button type="button" title="重命名" onClick={() => { setEditingId(item.id); setDraftTitle(item.title); }}><EditIcon size={15} /></button><button type="button" title="删除" onClick={() => void props.onDelete(item.id)}><TrashIcon size={15} /></button></div>}
                </div>
              ))}
            </div></section>
          ))}
        </div>

        <div className="sidebar-footer">
          <button type="button" onClick={props.onSettings}><SettingsIcon /><span><strong>接口配置</strong><small>API Key 与模型服务</small></span></button>
          <div className={`backend-state ${props.backendStatus}`}><span />{props.backendStatus === "connected" ? "后端 v1.3 已连接" : props.backendStatus === "outdated" ? "后端版本过旧" : "后端未连接"}</div>
        </div>
      </aside>
      {props.open && <button className="sidebar-scrim" type="button" onClick={props.onClose} aria-label="关闭侧栏遮罩" />}
    </>
  );
}
