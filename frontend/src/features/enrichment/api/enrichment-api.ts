"use client";

import { apiRequest } from "@/lib/api/client";

export type EnrichmentProfile = "quick" | "standard" | "deep";
export type EnrichmentLanguage = "de" | "en";

export type EnrichmentMutationInput = {
  product_id: number;
  field_name: string;
  current_value?: unknown;
  proposed_value?: unknown;
  confidence?: number;
  provenance?: Record<string, unknown>;
};

export type EnrichmentStartRequest = {
  supplier_code: string;
  supplier_verified: boolean;
  mapping_version?: number;
  alt_text_policy: "preserve" | "approved_overwrite";
  run_profile: EnrichmentProfile;
  target_language: EnrichmentLanguage;
  dry_run_ttl_minutes: number;
  mutations: EnrichmentMutationInput[];
};

export type EnrichmentDecisionRow = {
  item_id?: number;
  product_id: number | null;
  field_name: string;
  field_group: string;
  before_value: unknown;
  after_value: unknown;
  policy_version: number;
  mapping_version: number | null;
  reason_codes: string[];
  requires_user_action: boolean;
  is_blocked: boolean;
  is_protected_column: boolean;
  alt_text_preserved: boolean;
  confidence: number | null;
  provenance: Record<string, unknown> | null;
  decision_state?: string;
};

export type EnrichmentLifecycleResponse = {
  run_id: number;
  status: string;
  run_profile: EnrichmentProfile;
  target_language: EnrichmentLanguage;
  policy_version: number;
  mapping_version: number | null;
  alt_text_policy: string;
  protected_columns: string[];
  dry_run_expires_at: string | null;
  is_stale: boolean;
  oracle_decision: string;
  capability_audit?: {
    supplier_code: string;
    supplier_verified: boolean;
    policy_version: number;
    mapping_version: number | null;
    alt_text_policy: string;
    protected_columns: string[];
    generated_at: string;
  };
  write_plan: {
    allowed: EnrichmentDecisionRow[];
    blocked: EnrichmentDecisionRow[];
    counts: {
      allowed: number;
      blocked: number;
      approved?: number;
      total: number;
    };
  };
  metadata: Record<string, unknown>;
};

export type EnrichmentApplyResponse = {
  run_id: number;
  status: string;
  job_id: number;
  task_id: string;
  queue: string;
  stream_url: string;
  results_url: string;
  target_language: EnrichmentLanguage;
};

export async function startEnrichmentRun(
  payload: EnrichmentStartRequest,
): Promise<EnrichmentLifecycleResponse> {
  return apiRequest<EnrichmentLifecycleResponse, EnrichmentStartRequest>("/api/v1/products/enrichment/runs/start", {
    method: "POST",
    body: payload,
  });
}

export async function fetchEnrichmentReview(runId: number): Promise<EnrichmentLifecycleResponse> {
  return apiRequest<EnrichmentLifecycleResponse>(`/api/v1/products/enrichment/runs/${runId}/review`);
}

export async function approveEnrichmentRun(
  runId: number,
  payload: {
    approve_all: boolean;
    approved_item_ids?: number[];
    rejected_item_ids?: number[];
    reviewer_note?: string;
  },
): Promise<EnrichmentLifecycleResponse> {
  return apiRequest<EnrichmentLifecycleResponse>(`/api/v1/products/enrichment/runs/${runId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function applyEnrichmentRun(
  runId: number,
  payload: { apply_mode: "immediate" | "scheduled"; confirm_apply: boolean },
): Promise<EnrichmentApplyResponse> {
  return apiRequest<EnrichmentApplyResponse>(`/api/v1/products/enrichment/runs/${runId}/apply`, {
    method: "POST",
    body: payload,
  });
}
