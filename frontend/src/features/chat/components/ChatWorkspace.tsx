"use client";

import { FormEvent, useMemo, useState } from "react";
import { ActionCard } from "@/features/chat/components/ActionCard";
import { MessageBlockRenderer } from "@/features/chat/components/MessageBlockRenderer";
import { useChatSession } from "@/features/chat/hooks/useChatSession";

function parseSkuCsv(input: string): string[] {
  return input
    .split(/[,\n]/g)
    .map((part) => part.trim())
    .filter(Boolean);
}

export function ChatWorkspace() {
  const chat = useChatSession();
  const [messageInput, setMessageInput] = useState("");
  const [bulkSkuInput, setBulkSkuInput] = useState("");

  const activeSessionLabel = useMemo(() => {
    if (!chat.session) return "No session";
    const title = chat.session.title ?? `Session ${chat.session.id}`;
    return `${title} (#${chat.session.id})`;
  }, [chat.session]);

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
    <section className="panel chat-workspace" data-testid="chat-workspace">
      <header className="chat-workspace-header">
        <h1>chat</h1>
        <p className="muted">
          Session: <strong>{activeSessionLabel}</strong>
        </p>
        <p className="muted">
          Context state: <strong>{chat.session?.state ?? "at_door"}</strong>
        </p>
        <p className="muted">
          Stream mode: <strong>{chat.streamMode}</strong>
          {chat.streamDegraded ? " (degraded)" : ""}
        </p>
        {chat.streamError && <p className="chat-error">{chat.streamError}</p>}
        <p className="muted">
          One stream per session view is enforced with polling fallback when stream health degrades.
        </p>
      </header>

      {chat.loading ? (
        <p className="muted">Loading chat session…</p>
      ) : (
        <>
          <section className="chat-timeline" data-testid="chat-timeline">
            {chat.messages.length === 0 ? (
              <p className="muted">Start by describing a SKU or bulk SKU list.</p>
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
                  <p>{message.content}</p>
                  {message.role !== "user" && message.blocks.length > 0 && (
                    <MessageBlockRenderer blocks={message.blocks} />
                  )}
                </article>
              ))
            )}
          </section>

          <form className="chat-composer" onSubmit={handleSendMessage}>
            <label htmlFor="chat-message-input">Message</label>
            <textarea
              id="chat-message-input"
              rows={3}
              value={messageInput}
              onChange={(event) => setMessageInput(event.target.value)}
              placeholder="Example: update SKU-100 price to 12.99"
            />
            <button type="submit" disabled={chat.submitting || !messageInput.trim()}>
              {chat.submitting ? "Sending…" : "Send"}
            </button>
          </form>

          <form className="chat-bulk-form" onSubmit={handleBulkSubmit}>
            <label htmlFor="chat-bulk-input">Bulk SKUs (comma/newline separated)</label>
            <textarea
              id="chat-bulk-input"
              rows={4}
              value={bulkSkuInput}
              onChange={(event) => setBulkSkuInput(event.target.value)}
              placeholder={"SKU-100\nSKU-200\nSKU-300"}
            />
            <button type="submit" disabled={chat.submitting || parseSkuCsv(bulkSkuInput).length === 0}>
              {chat.submitting ? "Submitting bulk…" : "Create bulk action"}
            </button>
          </form>

          <section className="chat-actions" data-testid="chat-actions">
            <h2>Action Controls</h2>
            {chat.actions.length === 0 ? (
              <p className="muted">No actions yet.</p>
            ) : (
              chat.actions.map((action) => (
                <ActionCard
                  key={action.id}
                  action={action}
                  submitting={chat.submitting}
                  onApprove={chat.approveAction}
                  onApply={chat.applyAction}
                />
              ))
            )}
          </section>
        </>
      )}
      {chat.error && <p className="chat-error">{chat.error}</p>}
    </section>
  );
}
