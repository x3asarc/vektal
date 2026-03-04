"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ActionCard } from "@/features/chat/components/ActionCard";
import { MessageBlockRenderer } from "@/features/chat/components/MessageBlockRenderer";
import { useChatSession } from "@/features/chat/hooks/useChatSession";

function parseSkuCsv(input: string): string[] {
  return input
    .split(/[,\n]/g)
    .map((part) => part.trim())
    .filter(Boolean);
}

function hasAssistantTextBlock(message: { role: "user" | "assistant" | "system"; blocks: Array<{ type: string; text?: string | null }> }): boolean {
  if (message.role === "user") return false;
  return message.blocks.some((block) => block.type === "text" && typeof block.text === "string" && block.text.trim().length > 0);
}

export function ChatWorkspace() {
  const chat = useChatSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [messageInput, setMessageInput] = useState("");
  const [bulkSkuInput, setBulkSkuInput] = useState("");
  const [showBulk, setShowBulk] = useState(false);
  const autoSentRef = useRef(false);

  // Auto-send ?q= param arriving from dashboard prompt input
  useEffect(() => {
    if (autoSentRef.current) return;
    const q = searchParams.get("q");
    if (!q || !q.trim()) return;
    if (chat.loading) return; // wait until session is ready
    autoSentRef.current = true;
    void chat.sendMessage(q.trim()).then(() => {
      router.replace("/chat");
    });
  }, [chat.loading, searchParams, chat, router]);

  const activeSessionLabel = useMemo(() => {
    if (!chat.session) return "No session";
    const title = chat.session.title ?? `Session ${chat.session.id}`;
    return `${title} (#${chat.session.id})`;
  }, [chat.session]);

  const latestRouteNotice = useMemo(() => {
    const assistantMessages = [...chat.messages].reverse().filter((message) => message.role !== "user");
    for (const message of assistantMessages) {
      const sourceMetadata = message.source_metadata;
      if (!sourceMetadata || typeof sourceMetadata !== "object") continue;
      const routeSummary = sourceMetadata["route_summary"];
      if (!routeSummary || typeof routeSummary !== "object") continue;
      const fallbackStage =
        typeof (routeSummary as Record<string, unknown>)["fallback_stage"] === "string"
          ? ((routeSummary as Record<string, unknown>)["fallback_stage"] as string)
          : null;
      if (!fallbackStage) continue;
      const suggestedEscalation =
        typeof (routeSummary as Record<string, unknown>)["suggested_escalation"] === "string"
          ? ((routeSummary as Record<string, unknown>)["suggested_escalation"] as string)
          : null;
      return { fallbackStage, suggestedEscalation };
    }
    return null;
  }, [chat.messages]);

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = messageInput.trim();
    if (!value) return;
    await chat.sendMessage(value);
    setMessageInput("");
  }

  async function handleBulkSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const skus = parseSkuCsv(bulkSkuInput);
    if (skus.length === 0) return;
    await chat.createBulkAction({
      content: `Bulk update request (${skus.length} SKUs)`,
      skus,
      operation: "update_product",
    });
    setBulkSkuInput("");
  }

  return (
    <div className="chat-page" data-testid="chat-workspace">
      {/* Header bar */}
      <header className="chat-page-header">
        <h1 className="chat-page-title">
          <span className="material-symbols-rounded filled-icon" style={{ marginRight: 8 }}>auto_awesome</span>
          AI Assistant
        </h1>
        <div className="chat-page-meta">
          <span className="chat-page-badge">
            Session: <strong>&nbsp;{activeSessionLabel}</strong>
          </span>
          <span className="chat-page-badge">
            State: <strong>&nbsp;{chat.session?.state ?? "at_door"}</strong>
          </span>
          <span className="chat-page-badge">
            Stream: <strong>&nbsp;{chat.streamMode}{chat.streamDegraded ? " ⚠" : ""}</strong>
          </span>
        </div>
      </header>

      {/* Route fallback notice */}
      {latestRouteNotice && (
        <div style={{ padding: "0 32px" }}>
          <aside className="chat-fallback-notice" data-testid="safe-tier-fallback">
            <strong>Fallback stage:</strong> {latestRouteNotice.fallbackStage}
            {latestRouteNotice.suggestedEscalation && (
              <span className="muted"> · Suggested: {latestRouteNotice.suggestedEscalation}</span>
            )}
          </aside>
        </div>
      )}

      {/* Timeline */}
      {chat.loading ? (
        <div className="chat-page-timeline">
          <div className="chat-page-empty">
            <span className="material-symbols-rounded">hourglass_empty</span>
            <p>Loading session…</p>
          </div>
        </div>
      ) : (
        <div className="chat-page-timeline" data-testid="chat-timeline">
          {chat.messages.length === 0 ? (
            <div className="chat-page-empty">
              <span className="material-symbols-rounded">chat_bubble_outline</span>
              <p>Start by describing a SKU or bulk SKU list.</p>
            </div>
          ) : (
            chat.messages.map((message) => (
              <article
                key={message.id}
                className="chat-message"
                data-role={message.role}
                data-pending={message.pending ? "true" : "false"}
              >
                <header>
                  <strong>{message.role}</strong>
                  {message.pending && <span className="muted"> pending…</span>}
                </header>
                {(!hasAssistantTextBlock(message) || message.role === "user") && <p>{message.content}</p>}
                {message.role !== "user" && message.blocks.length > 0 && (
                  <MessageBlockRenderer blocks={message.blocks} />
                )}
              </article>
            ))
          )}

          {/* Action cards inside timeline */}
          {!chat.loading && chat.actions.length > 0 && (
            <section className="chat-actions" data-testid="chat-actions">
              <h2 style={{ fontSize: "0.78rem", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em", margin: "8px 0 4px" }}>
                Action Controls
              </h2>
              {chat.actions.map((action) => (
                <ActionCard
                  key={action.id}
                  action={action}
                  submitting={chat.submitting}
                  onApprove={chat.approveAction}
                  onApply={chat.applyAction}
                  onDelegate={(actionId) => chat.delegateAction(actionId)}
                />
              ))}
            </section>
          )}
        </div>
      )}

      {/* Footer: composer + bulk */}
      {!chat.loading && (
        <footer className="chat-page-footer">
          {chat.streamError && <p className="chat-error" style={{ margin: 0 }}>{chat.streamError}</p>}
          {chat.error && <p className="chat-error" style={{ margin: 0 }}>{chat.error}</p>}

          {/* Glass message composer */}
          <form className="chat-glass-composer" onSubmit={(event) => { void handleSendMessage(event); }}>
            <textarea
              id="chat-message-input"
              rows={2}
              value={messageInput}
              onChange={(event) => setMessageInput(event.target.value)}
              placeholder="Describe a SKU update, e.g. set SKU-100 price to 12.99…"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (!messageInput.trim() || chat.submitting) return;
                  void chat.sendMessage(messageInput.trim()).then(() => setMessageInput(""));
                }
              }}
            />
            <div className="chat-glass-toolbar">
              <button
                type="button"
                className="chat-bulk-toggle"
                onClick={() => setShowBulk((v) => !v)}
              >
                <span className="material-symbols-rounded" style={{ fontSize: 16 }}>list_alt</span>
                Bulk SKUs
              </button>
              <button
                className="chat-glass-send"
                type="submit"
                disabled={chat.submitting || !messageInput.trim()}
                title="Send"
              >
                <span className="material-symbols-rounded" style={{ fontSize: 16 }}>arrow_upward</span>
              </button>
            </div>
          </form>

          {/* Bulk form (collapsible) */}
          {showBulk && (
            <form className="chat-glass-composer" onSubmit={(event) => { void handleBulkSubmit(event); }} style={{ gap: 8 }}>
              <label style={{ fontSize: "0.72rem", color: "var(--muted)", fontWeight: 500 }}>
                Bulk SKUs (comma or newline separated)
              </label>
              <textarea
                id="chat-bulk-input"
                rows={3}
                value={bulkSkuInput}
                onChange={(event) => setBulkSkuInput(event.target.value)}
                placeholder={"SKU-100\nSKU-200\nSKU-300"}
              />
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button
                  className="btn-ghost"
                  type="submit"
                  disabled={chat.submitting || parseSkuCsv(bulkSkuInput).length === 0}
                  style={{ fontSize: "0.78rem" }}
                >
                  {chat.submitting ? "Submitting…" : `Create bulk action (${parseSkuCsv(bulkSkuInput).length} SKUs)`}
                </button>
              </div>
            </form>
          )}
        </footer>
      )}
    </div>
  );
}
