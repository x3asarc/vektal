"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  applyChatAction,
  approveChatAction,
  createChatBulkAction,
  createChatSession,
  delegateChatAction,
  getChatAction,
  listChatMessages,
  listChatSessions,
  sendChatMessage,
} from "@/features/chat/api/chat-api";
import { ChatStreamEnvelope, useChatStream } from "@/features/chat/hooks/useChatStream";
import { ApiClientError } from "@/lib/api/client";
import { ChatAction, ChatActionStatus, ChatMessage, ChatSession } from "@/shared/contracts/chat";

export type ChatUiMessage = ChatMessage & { pending?: boolean };

type UseChatSessionResult = {
  sessions: ChatSession[];
  session: ChatSession | null;
  messages: ChatUiMessage[];
  actions: ChatAction[];
  loading: boolean;
  submitting: boolean;
  error: string | null;
  streamMode: "sse" | "polling" | "degraded";
  streamDegraded: boolean;
  streamError: string | null;
  sendMessage: (content: string, actionHints?: Record<string, unknown>) => Promise<void>;
  createBulkAction: (input: {
    content: string;
    skus: string[];
    operation?: "add_product" | "update_product";
    mode?: "immediate" | "scheduled";
    actionHints?: Record<string, unknown>;
  }) => Promise<void>;
  approveAction: (actionId: number, comment?: string) => Promise<void>;
  applyAction: (actionId: number, mode?: "immediate" | "scheduled") => Promise<void>;
  delegateAction: (actionId: number, input?: {
    requestedTools?: string[];
    depth?: number;
    fanOut?: number;
  }) => Promise<void>;
  refresh: () => Promise<void>;
};

function formatApiError(error: unknown): string {
  if (error instanceof ApiClientError) {
    return `${error.normalized.detail} (HTTP ${error.normalized.status})`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Chat request failed.";
}

function randomIdempotency(prefix: string): string {
  const part = Math.random().toString(36).slice(2, 10);
  return `${prefix}-${Date.now()}-${part}`;
}

function upsertActionMap(
  map: Map<number, ChatAction>,
  next: ChatAction,
): Map<number, ChatAction> {
  const copy = new Map(map);
  const existing = copy.get(next.id);
  copy.set(next.id, existing ? { ...existing, ...next } : next);
  return copy;
}

function upsertMessage(messages: ChatUiMessage[], message: ChatUiMessage): ChatUiMessage[] {
  const index = messages.findIndex((item) => item.id === message.id);
  if (index >= 0) {
    const copy = [...messages];
    copy[index] = { ...copy[index], ...message, pending: false };
    return copy;
  }
  return [...messages, message];
}

function isChatActionStatus(value: unknown): value is ChatActionStatus {
  return (
    value === "drafted" ||
    value === "dry_run_ready" ||
    value === "awaiting_approval" ||
    value === "approved" ||
    value === "applying" ||
    value === "completed" ||
    value === "failed" ||
    value === "conflicted" ||
    value === "partial" ||
    value === "cancelled"
  );
}

export function useChatSession(): UseChatSessionResult {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatUiMessage[]>([]);
  const [actionsById, setActionsById] = useState<Map<number, ChatAction>>(new Map());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sessionId = session?.id ?? null;

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    const messageList = await listChatMessages(sessionId, 150);
    setMessages((previous) => {
      let next = [...previous];
      for (const msg of messageList.messages) {
        next = upsertMessage(next, msg);
      }
      return next
        .filter((msg) => !msg.pending || msg.id < 0)
        .sort((a, b) => a.id - b.id);
    });

    setActionsById((previous) => {
      let next = new Map(previous);
      const actionIds = new Set<number>();
      for (const msg of messageList.messages) {
        const blocks = msg.blocks ?? [];
        for (const block of blocks) {
          if (block.type !== "action") continue;
          const raw = block.data?.action_id;
          if (typeof raw === "number") actionIds.add(raw);
        }
      }
      for (const actionId of previous.keys()) {
        actionIds.add(actionId);
      }
      return next;
    });
  }, [sessionId]);

  const handleEnvelope = useCallback((eventName: string, envelope: ChatStreamEnvelope) => {
    if (eventName === "chat_message") {
      const payload = envelope.payload;
      const id = typeof payload.message_id === "number" ? payload.message_id : null;
      if (!id) return;
      const role = payload.role === "assistant" || payload.role === "system" ? payload.role : "assistant";
      const content = typeof payload.content === "string" ? payload.content : "";
      const blocks = Array.isArray(payload.blocks) ? payload.blocks as ChatMessage["blocks"] : [];
      const nextMessage: ChatUiMessage = {
        id,
        session_id: envelope.session_id,
        user_id: session?.user_id ?? 0,
        role,
        content,
        blocks,
        intent_type: typeof payload.intent_type === "string" ? payload.intent_type : null,
      };
      setMessages((previous) => upsertMessage(previous, nextMessage).sort((a, b) => a.id - b.id));
      return;
    }

    if (eventName === "chat_action") {
      const payload = envelope.payload;
      const actionId = typeof payload.action_id === "number" ? payload.action_id : null;
      if (!actionId) return;
      setActionsById((previous) => {
        const existing = previous.get(actionId);
        if (!existing) return previous;
        const nextStatus = isChatActionStatus(payload.status) ? payload.status : existing.status;
        return upsertActionMap(previous, {
          ...existing,
          status: nextStatus,
          result: typeof payload.result === "object" && payload.result ? payload.result as Record<string, unknown> : existing.result,
        });
      });
      return;
    }

    if (eventName === "chat_session_state") {
      const payload = envelope.payload;
      const state = payload.state;
      const status = payload.status;
      if ((state === "at_door" || state === "in_house") && (status === "active" || status === "closed")) {
        setSession((previous) => (previous ? { ...previous, state, status } : previous));
      }
    }
  }, [session?.user_id]);

  const stream = useChatStream({
    sessionId,
    onEnvelope: handleEnvelope,
    poll: refresh,
  });

  useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      try {
        setLoading(true);
        const list = await listChatSessions(25);
        if (cancelled) return;
        setSessions(list.sessions);
        let active = list.sessions[0] ?? null;
        if (!active) {
          active = await createChatSession("Chat Workspace");
          if (cancelled) return;
          setSessions([active]);
        }
        setSession(active);
        const messageList = await listChatMessages(active.id, 150);
        if (cancelled) return;
        setMessages(messageList.messages.sort((a, b) => a.id - b.id));
        setError(null);
      } catch (reason: unknown) {
        if (cancelled) return;
        setError(formatApiError(reason));
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  const setAction = useCallback((action: ChatAction | null | undefined) => {
    if (!action) return;
    setActionsById((previous) => upsertActionMap(previous, action));
  }, []);

  const sendMessageWrapper = useCallback(
    async (content: string, actionHints: Record<string, unknown> = {}) => {
      if (!sessionId || !content.trim()) return;
      const tempId = -Date.now();
      const optimistic: ChatUiMessage = {
        id: tempId,
        session_id: sessionId,
        user_id: session?.user_id ?? 0,
        role: "user",
        content,
        blocks: [{ type: "text", text: content }],
        pending: true,
      };
      setMessages((previous) => [...previous, optimistic]);
      setSubmitting(true);
      try {
        const response = await sendChatMessage(sessionId, {
          content,
          action_hints: actionHints,
          idempotency_key: randomIdempotency("chat-msg"),
        });
        setMessages((previous) => {
          const withoutTemp = previous.filter((msg) => msg.id !== tempId);
          return [response.user_message, response.assistant_message, ...withoutTemp]
            .sort((a, b) => a.id - b.id);
        });
        setSession(response.session);
        setAction(response.action ?? null);
        setError(null);
      } catch (reason: unknown) {
        setMessages((previous) => previous.filter((msg) => msg.id !== tempId));
        setError(formatApiError(reason));
      } finally {
        setSubmitting(false);
      }
    },
    [session?.user_id, sessionId, setAction],
  );

  const createBulkActionWrapper = useCallback(
    async (input: {
      content: string;
      skus: string[];
      operation?: "add_product" | "update_product";
      mode?: "immediate" | "scheduled";
      actionHints?: Record<string, unknown>;
    }) => {
      if (!sessionId || input.skus.length === 0) return;
      setSubmitting(true);
      try {
        const response = await createChatBulkAction(sessionId, {
          content: input.content,
          skus: input.skus,
          operation: input.operation ?? "update_product",
          mode: input.mode,
          action_hints: input.actionHints,
          idempotency_key: randomIdempotency("chat-bulk"),
        });
        setMessages((previous) =>
          [...previous, response.user_message, response.assistant_message].sort((a, b) => a.id - b.id),
        );
        setSession(response.session);
        setAction(response.action ?? null);
        setError(null);
      } catch (reason: unknown) {
        setError(formatApiError(reason));
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId, setAction],
  );

  const approve = useCallback(
    async (actionId: number, comment?: string) => {
      if (!sessionId) return;
      setSubmitting(true);
      try {
        const updated = await approveChatAction(sessionId, actionId, { comment });
        setAction(updated);
        setError(null);
      } catch (reason: unknown) {
        setError(formatApiError(reason));
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId, setAction],
  );

  const apply = useCallback(
    async (actionId: number, mode?: "immediate" | "scheduled") => {
      if (!sessionId) return;
      setSubmitting(true);
      try {
        const updated = await applyChatAction(sessionId, actionId, { mode });
        setAction(updated);
        setError(null);
      } catch (reason: unknown) {
        setError(formatApiError(reason));
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId, setAction],
  );

  const delegate = useCallback(
    async (
      actionId: number,
      input: {
        requestedTools?: string[];
        depth?: number;
        fanOut?: number;
      } = {},
    ) => {
      if (!sessionId) return;
      setSubmitting(true);
      try {
        const delegated = await delegateChatAction(sessionId, actionId, {
          requested_tools: input.requestedTools ?? [],
          depth: input.depth ?? 1,
          fan_out: input.fanOut ?? 1,
        });
        setActionsById((previous) => {
          const current = previous.get(actionId);
          if (!current) return previous;
          const result = {
            ...(current.result ?? {}),
            delegation: delegated,
          };
          const payload = {
            ...(current.payload ?? {}),
            delegation_trace: delegated,
          };
          return upsertActionMap(previous, { ...current, result, payload });
        });
        setError(null);
      } catch (reason: unknown) {
        setError(formatApiError(reason));
      } finally {
        setSubmitting(false);
      }
    },
    [sessionId],
  );

  useEffect(() => {
    if (!sessionId) return;
    const activeSessionId = sessionId;
    const ids = [...actionsById.keys()];
    if (ids.length === 0) return;
    if (stream.mode === "sse") return;

    let cancelled = false;
    async function refreshActions() {
      for (const actionId of ids) {
        try {
          const latest = await getChatAction(activeSessionId, actionId);
          if (cancelled) return;
          setActionsById((previous) => upsertActionMap(previous, latest));
        } catch {
          // Best-effort refresh while degraded.
        }
      }
    }

    void refreshActions();
    return () => {
      cancelled = true;
    };
  }, [actionsById, sessionId, stream.mode]);

  const actions = useMemo(
    () => [...actionsById.values()].sort((a, b) => a.id - b.id),
    [actionsById],
  );

  return {
    sessions,
    session,
    messages,
    actions,
    loading,
    submitting,
    error,
    streamMode: stream.mode,
    streamDegraded: stream.degraded,
    streamError: stream.error,
    sendMessage: sendMessageWrapper,
    createBulkAction: createBulkActionWrapper,
    approveAction: approve,
    applyAction: apply,
    delegateAction: delegate,
    refresh,
  };
}
