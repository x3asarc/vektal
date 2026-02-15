"use client";

import { apiRequest } from "@/lib/api/client";
import { ChatAction, ChatMessage, ChatSession } from "@/shared/contracts/chat";

type ChatSessionListResponse = {
  sessions: ChatSession[];
  total: number;
};

type ChatMessageListResponse = {
  messages: ChatMessage[];
  total: number;
};

type ChatMessageCreateResponse = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  action?: ChatAction | null;
};

type BulkActionRequest = {
  content: string;
  skus: string[];
  operation?: "add_product" | "update_product";
  idempotency_key?: string;
  action_hints?: Record<string, unknown>;
  requested_chunk_size?: number;
  admin_concurrency_cap?: number;
  mode?: "immediate" | "scheduled";
};

export async function listChatSessions(limit = 25) {
  const qs = `?limit=${encodeURIComponent(String(limit))}`;
  return apiRequest<ChatSessionListResponse>(`/api/v1/chat/sessions${qs}`);
}

export async function createChatSession(title = "Chat Workspace") {
  return apiRequest<ChatSession, { title: string }>(
    "/api/v1/chat/sessions",
    {
      method: "POST",
      body: { title },
    },
  );
}

export async function listChatMessages(sessionId: number, limit = 100) {
  const qs = `?limit=${encodeURIComponent(String(limit))}`;
  return apiRequest<ChatMessageListResponse>(
    `/api/v1/chat/sessions/${sessionId}/messages${qs}`,
  );
}

export async function sendChatMessage(
  sessionId: number,
  input: {
    content: string;
    idempotency_key?: string;
    action_hints?: Record<string, unknown>;
  },
) {
  return apiRequest<ChatMessageCreateResponse, typeof input>(
    `/api/v1/chat/sessions/${sessionId}/messages`,
    {
      method: "POST",
      body: input,
    },
  );
}

export async function createChatBulkAction(sessionId: number, input: BulkActionRequest) {
  return apiRequest<ChatMessageCreateResponse, BulkActionRequest>(
    `/api/v1/chat/sessions/${sessionId}/bulk/actions`,
    {
      method: "POST",
      body: input,
    },
  );
}

export async function getChatAction(sessionId: number, actionId: number) {
  return apiRequest<ChatAction>(`/api/v1/chat/sessions/${sessionId}/actions/${actionId}`);
}

export async function approveChatAction(
  sessionId: number,
  actionId: number,
  input: {
    selected_change_ids?: number[];
    overrides?: Array<{ change_id: number; after_value: unknown }>;
    comment?: string;
  },
) {
  return apiRequest<ChatAction, typeof input>(
    `/api/v1/chat/sessions/${sessionId}/actions/${actionId}/approve`,
    {
      method: "POST",
      body: input,
    },
  );
}

export async function applyChatAction(
  sessionId: number,
  actionId: number,
  input: { mode?: "immediate" | "scheduled" } = {},
) {
  return apiRequest<ChatAction, typeof input>(
    `/api/v1/chat/sessions/${sessionId}/actions/${actionId}/apply`,
    {
      method: "POST",
      body: input,
    },
  );
}
