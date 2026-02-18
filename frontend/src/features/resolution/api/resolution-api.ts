"use client";

import { apiRequest, ApiClientError } from "@/lib/api/client";
import {
  ResolutionActivityItem,
  ResolutionDryRunBatch,
  ResolutionLineageEntry,
  ResolutionRuleSuggestion,
  StrategyQuizState,
} from "@/shared/contracts/resolution";

type RuleDto = {
  id: number;
  supplier_code: string;
  field_group: "images" | "text" | "pricing" | "ids";
  rule_type: "auto_apply" | "exclude" | "variant_create" | "quiz_default";
  action: string;
  consented: boolean;
  enabled: boolean;
  expires_at?: string | null;
  config?: Record<string, unknown> | null;
  notes?: string | null;
};

export async function createDryRun(payload: {
  supplier_code: string;
  supplier_verified: boolean;
  apply_mode?: "immediate" | "scheduled";
  scheduled_for?: string;
  rows: Array<Record<string, unknown>>;
}) {
  return apiRequest<{
    batch_id: number;
    status: string;
    apply_mode: string;
    supplier_code: string;
    counts: Record<string, unknown>;
  }, typeof payload>("/api/v1/resolution/dry-runs", {
    method: "POST",
    body: payload,
  });
}

export async function fetchDryRun(batchId: number, requireLock = false) {
  return apiRequest<ResolutionDryRunBatch>(
    `/api/v1/resolution/dry-runs/${batchId}${requireLock ? "?require_lock=true" : ""}`,
  );
}

export async function fetchDryRunLineage(batchId: number) {
  const payload = await apiRequest<{
    batch_id: number;
    entries: ResolutionLineageEntry[];
  }>(`/api/v1/resolution/dry-runs/${batchId}/lineage`);
  return payload.entries;
}

export async function getBatchLock(batchId: number) {
  return apiRequest<{
    batch_id: number;
    locked: boolean;
    lock_owner_user_id?: number | null;
    lock_expires_at?: string | null;
    lock_heartbeat_at?: string | null;
    granted?: boolean;
  }>(`/api/v1/resolution/locks/${batchId}`);
}

export async function acquireBatchLock(batchId: number, leaseSeconds = 300) {
  return apiRequest<{
    batch_id: number;
    locked: boolean;
    lock_owner_user_id?: number | null;
    lock_expires_at?: string | null;
    lock_heartbeat_at?: string | null;
    granted?: boolean;
  }, { lease_seconds: number }>(`/api/v1/resolution/locks/${batchId}/acquire`, {
    method: "POST",
    body: { lease_seconds: leaseSeconds },
  });
}

export async function heartbeatBatchLock(batchId: number, leaseSeconds = 300) {
  return apiRequest<{
    batch_id: number;
    locked: boolean;
    lock_owner_user_id?: number | null;
    lock_expires_at?: string | null;
    lock_heartbeat_at?: string | null;
    granted?: boolean;
  }, { lease_seconds: number }>(`/api/v1/resolution/locks/${batchId}/heartbeat`, {
    method: "POST",
    body: { lease_seconds: leaseSeconds },
  });
}

export async function releaseBatchLock(batchId: number) {
  return apiRequest<{ released: boolean; batch_id: number }, Record<string, never>>(
    `/api/v1/resolution/locks/${batchId}/release`,
    { method: "POST", body: {} },
  );
}

export async function fetchResolutionActivity(): Promise<{
  currentlyHappening: ResolutionActivityItem[];
  comingUpNext: ResolutionActivityItem[];
}> {
  const payload = await apiRequest<{
    currently_happening: ResolutionActivityItem[];
    coming_up_next: ResolutionActivityItem[];
  }>("/api/v1/resolution/activity");
  return {
    currentlyHappening: payload.currently_happening,
    comingUpNext: payload.coming_up_next,
  };
}

export async function listResolutionRules(supplierCode?: string) {
  const qs = supplierCode ? `?supplier_code=${encodeURIComponent(supplierCode)}` : "";
  return apiRequest<{ rules: RuleDto[]; total: number }>(
    `/api/v1/resolution/rules${qs}`,
  );
}

export async function createResolutionRule(input: Omit<RuleDto, "id">) {
  return apiRequest<RuleDto, Omit<RuleDto, "id">>("/api/v1/resolution/rules", {
    method: "POST",
    body: input,
  });
}

export async function saveStrategyQuiz(input: StrategyQuizState, supplierCode = "*") {
  const requests = [
    createResolutionRule({
      supplier_code: supplierCode,
      field_group: "ids",
      rule_type: "quiz_default",
      action: input.variantMismatchPolicy,
      consented: input.consentAutoCreateVariants,
      enabled: true,
      config: {
        scrape_variant_policy: input.scrapeVariantPolicy,
        first_batch_execution: input.firstBatchExecution,
        save_first_batch_choice: input.saveFirstBatchChoice,
        consent_field_groups: input.consentFieldGroups,
      },
      notes: input.notes ?? null,
      expires_at: null,
    }),
  ];
  await Promise.all(requests);
}

export async function fetchRuleSuggestions(): Promise<ResolutionRuleSuggestion[]> {
  try {
    const payload = await apiRequest<{ suggestions: ResolutionRuleSuggestion[] }>(
      "/api/v1/resolution/suggestions",
    );
    return payload.suggestions;
  } catch (error) {
    if (error instanceof ApiClientError && error.normalized.status === 404) {
      return [];
    }
    throw error;
  }
}

export async function acceptRuleSuggestion(input: ResolutionRuleSuggestion, expiryDays = 30) {
  const expiresAt = new Date();
  expiresAt.setDate(expiresAt.getDate() + expiryDays);
  return createResolutionRule({
    supplier_code: input.supplierCode,
    field_group: input.fieldGroup,
    rule_type: "auto_apply",
    action: input.action,
    consented: true,
    enabled: true,
    expires_at: expiresAt.toISOString(),
    config: { suggestion_id: input.id, reason: input.reason },
    notes: "Accepted from rule suggestion inbox",
  });
}

export async function declineRuleSuggestion(id: string) {
  try {
    await apiRequest<{ declined: boolean }, { suggestion_id: string }>(
      "/api/v1/resolution/suggestions/decline",
      {
        method: "POST",
        body: { suggestion_id: id },
      },
    );
  } catch (error) {
    if (error instanceof ApiClientError && error.normalized.status === 404) {
      return;
    }
    throw error;
  }
}
