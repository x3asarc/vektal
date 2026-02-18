export type BackendJobStatus =
  | "pending"
  | "queued"
  | "running"
  | "cancel_requested"
  | "completed"
  | "failed"
  | "failed_terminal"
  | "cancelled";

export type ObservedLifecycle =
  | "idle"
  | "submitting"
  | "accepted"
  | "in_progress"
  | "success"
  | "error"
  | "cancelled";

export function mapBackendStatusToLifecycle(status: string): ObservedLifecycle {
  switch (status) {
    case "pending":
      return "submitting";
    case "queued":
      return "accepted";
    case "running":
    case "cancel_requested":
      return "in_progress";
    case "completed":
      return "success";
    case "failed":
    case "failed_terminal":
      return "error";
    case "cancelled":
      return "cancelled";
    default:
      return "idle";
  }
}

export function isTerminalLifecycle(state: ObservedLifecycle): boolean {
  return state === "success" || state === "error" || state === "cancelled";
}

export function isActiveBackendStatus(status: string): boolean {
  return status === "pending" || status === "queued" || status === "running" || status === "cancel_requested";
}
