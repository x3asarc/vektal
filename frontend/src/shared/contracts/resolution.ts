export type ResolutionFieldGroup = "images" | "text" | "pricing" | "ids";

export type ResolutionChangeStatus =
  | "auto_applied"
  | "awaiting_approval"
  | "approved"
  | "rejected"
  | "blocked_exclusion"
  | "structural_conflict"
  | "applied"
  | "failed";

export type ResolutionChange = {
  change_id: number;
  field_group: ResolutionFieldGroup;
  field_name: string;
  before_value: unknown;
  after_value: unknown;
  status: ResolutionChangeStatus;
  reason_sentence?: string;
  reason_factors: Record<string, unknown>;
  confidence_score?: number | null;
  confidence_badge?: string | null;
  applied_rule_id?: number | null;
  blocked_by_rule_id?: number | null;
  approved_by_user_id?: number | null;
};

export type ResolutionProductGroup = {
  item_id: number;
  product_label?: string | null;
  status: string;
  structural_state?: string | null;
  conflict_reason?: string | null;
  source_used?: string | null;
  changes: ResolutionChange[];
};

export type ResolutionDryRunBatch = {
  batch_id: number;
  status: string;
  apply_mode: "immediate" | "scheduled";
  scheduled_for?: string | null;
  read_only: boolean;
  lock_owner_user_id?: number | null;
  groups: ResolutionProductGroup[];
};

export type ResolutionLineageEntry = {
  batch_id: number;
  item_id: number;
  change_id: number;
  field_name: string;
  status: string;
  reason_sentence?: string;
  confidence_score?: number | null;
  confidence_badge?: string | null;
  reason_factors?: Record<string, unknown>;
  applied_rule_id?: number | null;
  blocked_by_rule_id?: number | null;
  approved_by_user_id?: number | null;
  updated_at?: string | null;
};

export type ResolutionActivityItem = {
  batchId: number;
  label: string;
  ownerUserId?: number | null;
  mode: "review" | "apply" | "scheduled";
  scheduledFor?: string | null;
  status: string;
};

export type ResolutionRuleSuggestion = {
  id: string;
  supplierCode: string;
  fieldGroup: ResolutionFieldGroup;
  action: string;
  reason: string;
  suggestedExpiryDays?: number;
};

export type StrategyQuizState = {
  variantMismatchPolicy: "create_draft" | "ignore" | "ask_every_time";
  scrapeVariantPolicy: "scrape_all" | "base_only";
  firstBatchExecution: "immediate" | "scheduled";
  saveFirstBatchChoice: boolean;
  consentAutoCreateVariants: boolean;
  consentFieldGroups: ResolutionFieldGroup[];
  notes?: string;
};
