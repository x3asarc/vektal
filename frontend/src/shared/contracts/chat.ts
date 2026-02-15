export type ChatBlockType = "text" | "table" | "diff" | "action" | "progress" | "alert";

export type ChatBlock = {
  type: ChatBlockType;
  text?: string | null;
  title?: string | null;
  data?: Record<string, unknown> | null;
};

export type ChatSession = {
  id: number;
  user_id: number;
  store_id?: number | null;
  title?: string | null;
  state: "at_door" | "in_house";
  status: "active" | "closed";
  summary?: string | null;
  last_message_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ChatActionStatus =
  | "drafted"
  | "dry_run_ready"
  | "awaiting_approval"
  | "approved"
  | "applying"
  | "completed"
  | "failed"
  | "conflicted"
  | "partial"
  | "cancelled";

export type ChatAction = {
  id: number;
  session_id: number;
  user_id: number;
  store_id?: number | null;
  message_id?: number | null;
  action_type: string;
  status: ChatActionStatus;
  idempotency_key?: string | null;
  payload?: Record<string, unknown> | null;
  result?: Record<string, unknown> | null;
  error_message?: string | null;
  approved_at?: string | null;
  applied_at?: string | null;
  completed_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ChatMessage = {
  id: number;
  session_id: number;
  user_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  blocks: ChatBlock[];
  source_metadata?: Record<string, unknown> | null;
  intent_type?: string | null;
  classification_method?: string | null;
  confidence?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type ChatSessionList = {
  sessions: ChatSession[];
  total: number;
};

export type ChatMessageList = {
  messages: ChatMessage[];
  total: number;
};

export type ChatMessageCreateResult = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  action?: ChatAction | null;
};

export type ChatStreamEnvelope = {
  session_id: number;
  event: string;
  emitted_at?: string;
  payload: Record<string, unknown>;
};
