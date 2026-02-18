export type OnboardingStep =
  | "connect_shopify"
  | "choose_ingest"
  | "preview_start_import"
  | "import_progress"
  | "completed";

export type IngestPath = "sync_store" | "upload_csv";

export type OnboardingState = {
  step: OnboardingStep;
  ingestPath: IngestPath | null;
  advancedOpen: boolean;
};

export const INITIAL_ONBOARDING_STATE: OnboardingState = {
  step: "connect_shopify",
  ingestPath: null,
  advancedOpen: false,
};

export function connectShopify(state: OnboardingState): OnboardingState {
  if (state.step !== "connect_shopify") return state;
  return { ...state, step: "choose_ingest" };
}

export function chooseIngestPath(
  state: OnboardingState,
  ingestPath: IngestPath,
): OnboardingState {
  if (state.step !== "choose_ingest") return state;
  return { ...state, ingestPath, step: "preview_start_import" };
}

export function startImport(state: OnboardingState): OnboardingState {
  if (state.step !== "preview_start_import") return state;
  return { ...state, step: "import_progress" };
}

export function markComplete(state: OnboardingState): OnboardingState {
  if (state.step !== "import_progress") return state;
  return { ...state, step: "completed" };
}

export function toggleAdvanced(state: OnboardingState): OnboardingState {
  return { ...state, advancedOpen: !state.advancedOpen };
}
