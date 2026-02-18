import { normalizeProblemDetails } from "@/lib/api/problem-details";
import { NormalizedApiError } from "@/shared/contracts";

type ApiMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type RequestConfig<TBody> = {
  method?: ApiMethod;
  body?: TBody;
  headers?: HeadersInit;
  signal?: AbortSignal;
};

export class ApiClientError extends Error {
  readonly normalized: NormalizedApiError;

  constructor(normalized: NormalizedApiError) {
    super(normalized.detail);
    this.name = "ApiClientError";
    this.normalized = normalized;
  }
}

function resolveBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  // Default to same-origin so Next.js rewrites can proxy /api/* in development.
  return "";
}

async function parseResponseBody(response: Response): Promise<unknown> {
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    return response.json();
  }
  return response.text();
}

export async function apiRequest<TResponse, TBody = unknown>(
  path: string,
  config: RequestConfig<TBody> = {},
): Promise<TResponse> {
  const baseUrl = resolveBaseUrl();
  let response: Response;

  try {
    response = await fetch(`${baseUrl}${path}`, {
      method: config.method ?? "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(config.headers ?? {}),
      },
      body: config.body === undefined ? undefined : JSON.stringify(config.body),
      signal: config.signal,
    });
  } catch (error) {
    throw new ApiClientError(
      normalizeProblemDetails(
        {
          type: "urn:frontend:network-error",
          title: "Network error",
          status: 0,
          detail: `Cannot reach backend API at ${baseUrl || "(same-origin)"}${path}.`,
          errors: {
            _global: [error instanceof Error ? error.message : "Network request failed"],
          },
        },
        0,
      ),
    );
  }

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    throw new ApiClientError(normalizeProblemDetails(payload, response.status));
  }

  return payload as TResponse;
}
