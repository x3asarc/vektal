"use client";

import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api/client";
import { SearchScopeMode } from "@/features/search/api/search-api";

export type BulkOperation =
  | "set"
  | "replace"
  | "add"
  | "remove"
  | "clear"
  | "increase"
  | "decrease"
  | "conditional_set";

export type BulkActionBlock = {
  operation: BulkOperation;
  field_name: string;
  value?: string | number | boolean | null;
  values?: Array<string | number | boolean>;
  delta?: number;
  if_blank?: boolean;
};

export type BulkSelectionSnapshot = {
  scope_mode: SearchScopeMode;
  total_matching: number;
  selection_token: string;
  selected_ids: number[];
};

export type BulkStageRequest = {
  supplier_code: string;
  supplier_verified: boolean;
  selection: BulkSelectionSnapshot;
  action_blocks: BulkActionBlock[];
  apply_mode?: "immediate" | "scheduled";
  alt_text_policy?: "preserve" | "approved_overwrite";
  mapping_version?: number;
};

export type BulkStageResponse = {
  batch_id: number;
  status: string;
  apply_mode: string;
  admission: {
    schema_ok: boolean;
    policy_ok: boolean;
    conflict_state: "none" | "warning" | "blocked";
    eligible_to_apply: boolean;
    reasons: string[];
  };
  mapping_version: number;
  action_blocks: Array<Record<string, unknown>>;
  counts: {
    selected_products: number;
    staged_rows: number;
  };
};

export function useBulkStaging() {
  return useMutation({
    mutationFn: async (payload: BulkStageRequest) => {
      return apiRequest<BulkStageResponse, BulkStageRequest>("/api/v1/products/bulk/stage", {
        method: "POST",
        body: payload,
      });
    },
  });
}
