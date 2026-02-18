import { NormalizedApiError } from "@/shared/contracts";

type ProblemLike = Record<string, unknown> & {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  message?: string;
  error?: string;
  instance?: string;
  errors?: Record<string, string[] | string>;
  violations?: Array<{
    field?: string;
    pointer?: string;
    reason?: string;
    message?: string;
  }>;
};

function normalizeFieldErrors(problem: ProblemLike): Record<string, string[]> {
  const result: Record<string, string[]> = {};

  if (problem.errors && typeof problem.errors === "object") {
    for (const [field, value] of Object.entries(problem.errors)) {
      if (Array.isArray(value)) {
        result[field] = value.map(String);
      } else {
        result[field] = [String(value)];
      }
    }
  }

  if (Array.isArray(problem.violations)) {
    for (const violation of problem.violations) {
      const field = violation.field ?? violation.pointer ?? "_global";
      const message = violation.reason ?? violation.message ?? "Invalid value";
      result[field] = [...(result[field] ?? []), message];
    }
  }

  return result;
}

function classifyScope(fieldErrors: Record<string, string[]>): NormalizedApiError["scope"] {
  const fields = Object.keys(fieldErrors).filter((field) => field !== "_global");
  if (fields.length > 0) return "field";
  if (fieldErrors._global) return "page";
  return "global";
}

function classifySeverity(status: number): NormalizedApiError["severity"] {
  if (status >= 500) return "degrading";
  if (status >= 400) return "blocking";
  return "info";
}

function inferDetailFromRawText(raw: string, status: number): string {
  const trimmed = raw.trim();
  if (!trimmed) return "The request could not be completed.";

  const lower = trimmed.toLowerCase();
  if (
    status === 401 ||
    status === 403 ||
    lower.includes("login") ||
    lower.includes("unauthorized")
  ) {
    return "Authentication is required. Sign in to the backend session and retry.";
  }
  if (status === 404) {
    return "Endpoint not found. Check backend route availability and API base URL.";
  }
  if (lower.includes("<html") || lower.includes("<!doctype")) {
    return `Received non-JSON error response (HTTP ${status}).`;
  }

  return trimmed.slice(0, 240);
}

export function normalizeProblemDetails(
  input: unknown,
  fallbackStatus = 500,
): NormalizedApiError {
  const rawText = typeof input === "string" ? input : null;
  const problem: ProblemLike =
    typeof input === "object" && input ? (input as ProblemLike) : {};

  const status = typeof problem.status === "number" ? problem.status : fallbackStatus;
  const fieldErrors = normalizeFieldErrors(problem);
  const detail =
    typeof problem.detail === "string"
      ? problem.detail
      : typeof problem.message === "string"
        ? problem.message
        : typeof problem.error === "string"
          ? problem.error
          : rawText
            ? inferDetailFromRawText(rawText, status)
            : "The request could not be completed.";

  const reservedKeys = new Set([
    "type",
    "title",
    "status",
    "detail",
    "message",
    "error",
    "instance",
    "errors",
    "violations",
  ]);
  const extensions = Object.fromEntries(
    Object.entries(problem).filter(([key]) => !reservedKeys.has(key)),
  );

  return {
    type:
      typeof problem.type === "string"
        ? problem.type
        : "about:blank",
    title:
      typeof problem.title === "string"
        ? problem.title
        : typeof problem.error === "string"
          ? problem.error
          : "Request failed",
    status,
    detail,
    instance: typeof problem.instance === "string" ? problem.instance : undefined,
    fieldErrors,
    extensions: Object.keys(extensions).length > 0 ? extensions : undefined,
    scope: classifyScope(fieldErrors),
    severity: classifySeverity(status),
    canRetry: status >= 500 || status === 429,
  };
}
