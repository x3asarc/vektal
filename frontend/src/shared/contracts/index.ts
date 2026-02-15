export type Scope = {
  storeId: string;
  userId?: string;
};

export type GuardState = {
  A: boolean;
  V: boolean;
  S: boolean;
};

export type NormalizedApiError = {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance?: string;
  fieldErrors: Record<string, string[]>;
  extensions?: Record<string, unknown>;
  scope: "field" | "page" | "global";
  severity: "blocking" | "degrading" | "info";
  canRetry: boolean;
};

export type JobTerminalState = "success" | "error" | "cancelled";

export type JobLifecycleState =
  | "idle"
  | "submitting"
  | "accepted"
  | "in_progress"
  | JobTerminalState;

export * from "@/shared/contracts/chat";
export * from "@/shared/contracts/resolution";
