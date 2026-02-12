import { NormalizedApiError } from "@/shared/contracts";

export type PresentedError = {
  scope: "field" | "page" | "global";
  fieldErrors: Record<string, string[]>;
  pageMessages: string[];
  diagnostics: string[];
};

type PresentOptions = {
  knownFields?: string[];
};

export function presentError(
  error: NormalizedApiError,
  options: PresentOptions = {},
): PresentedError {
  const known = new Set(options.knownFields ?? []);
  const diagnostics: string[] = [];
  const fieldErrors: Record<string, string[]> = {};
  const pageMessages: string[] = [];

  for (const [field, messages] of Object.entries(error.fieldErrors)) {
    if (field === "_global") {
      pageMessages.push(...messages);
      continue;
    }
    if (known.size > 0 && !known.has(field)) {
      diagnostics.push(`unknown_field:${field}`);
      pageMessages.push(...messages);
      continue;
    }
    fieldErrors[field] = messages;
  }

  if (error.scope === "page" || error.scope === "global") {
    pageMessages.push(error.detail);
  }

  if (diagnostics.length > 0) {
    // Unknown field errors should be surfaced and logged, never silently dropped.
    console.warn("Unknown API field errors surfaced at page scope", diagnostics);
  }

  if (error.scope === "field" && Object.keys(fieldErrors).length === 0) {
    return {
      scope: "page",
      fieldErrors: {},
      pageMessages: pageMessages.length > 0 ? pageMessages : [error.detail],
      diagnostics,
    };
  }

  return {
    scope: error.scope,
    fieldErrors,
    pageMessages,
    diagnostics,
  };
}
