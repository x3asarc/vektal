import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import {
  EnrichmentLifecycleResponse,
  applyEnrichmentRun,
  approveEnrichmentRun,
  fetchEnrichmentReview,
  startEnrichmentRun,
} from "@/features/enrichment/api/enrichment-api";
import { EnrichmentWorkspace } from "@/features/enrichment/components/EnrichmentWorkspace";

vi.mock("@/features/enrichment/api/enrichment-api", async () => {
  const actual = await vi.importActual<typeof import("@/features/enrichment/api/enrichment-api")>(
    "@/features/enrichment/api/enrichment-api",
  );
  return {
    ...actual,
    startEnrichmentRun: vi.fn(),
    fetchEnrichmentReview: vi.fn(),
    approveEnrichmentRun: vi.fn(),
    applyEnrichmentRun: vi.fn(),
  };
});

const lifecycleResponse: EnrichmentLifecycleResponse = {
  run_id: 55,
  status: "dry_run_ready",
  run_profile: "standard",
  target_language: "de",
  policy_version: 3,
  mapping_version: 1,
  alt_text_policy: "preserve",
  protected_columns: ["id"],
  dry_run_expires_at: "2026-02-16T10:00:00+00:00",
  is_stale: false,
  oracle_decision: "pending",
  capability_audit: {
    supplier_code: "PENTART",
    supplier_verified: true,
    policy_version: 3,
    mapping_version: 1,
    alt_text_policy: "preserve",
    protected_columns: ["id"],
    generated_at: "2026-02-16T09:00:00+00:00",
  },
  write_plan: {
    allowed: [
      {
        item_id: 900,
        product_id: 100,
        field_name: "title",
        field_group: "text",
        before_value: "old",
        after_value: "new",
        policy_version: 3,
        mapping_version: 1,
        reason_codes: ["allowed"],
        requires_user_action: true,
        is_blocked: false,
        is_protected_column: false,
        alt_text_preserved: true,
        confidence: 0.9,
        provenance: { source: "ai_inferred" },
        decision_state: "suggested",
      },
    ],
    blocked: [],
    counts: { allowed: 1, blocked: 0, approved: 0, total: 1 },
  },
  metadata: { oracle_decision: "pending" },
};

describe("EnrichmentWorkspace", () => {
  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.mocked(startEnrichmentRun).mockReset();
    vi.mocked(fetchEnrichmentReview).mockReset();
    vi.mocked(approveEnrichmentRun).mockReset();
    vi.mocked(applyEnrichmentRun).mockReset();
  });

  it("starts run and renders review controls", async () => {
    vi.mocked(startEnrichmentRun).mockResolvedValue(lifecycleResponse);

    render(<EnrichmentWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Start dry-run" }));

    await waitFor(() => {
      expect(startEnrichmentRun).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId("enrichment-run-summary")).toBeInTheDocument();
    expect(screen.getByTestId("enrichment-run-summary")).toHaveTextContent("Run #55");
    expect(screen.getByTestId("enrichment-review-table")).toBeInTheDocument();
  });

  it("approves and applies selected run", async () => {
    vi.mocked(startEnrichmentRun).mockResolvedValue(lifecycleResponse);
    vi.mocked(approveEnrichmentRun).mockResolvedValue({
      ...lifecycleResponse,
      status: "approved",
      write_plan: {
        ...lifecycleResponse.write_plan,
        counts: { allowed: 1, blocked: 0, approved: 1, total: 1 },
      },
    });
    vi.mocked(applyEnrichmentRun).mockResolvedValue({
      run_id: 55,
      status: "applied",
      job_id: 88,
      task_id: "task-1",
      queue: "batch.t2",
      stream_url: "/api/v1/jobs/88/stream",
      results_url: "/jobs/88?tab=results",
      target_language: "de",
    });
    vi.mocked(fetchEnrichmentReview).mockResolvedValue({
      ...lifecycleResponse,
      status: "applied",
      oracle_decision: "execution_queued",
    });

    render(<EnrichmentWorkspace />);
    fireEvent.click(screen.getByRole("button", { name: "Start dry-run" }));
    await waitFor(() => expect(startEnrichmentRun).toHaveBeenCalled());

    fireEvent.click(screen.getByRole("button", { name: /approve selection/i }));
    await waitFor(() => expect(approveEnrichmentRun).toHaveBeenCalledWith(55, expect.any(Object)));

    fireEvent.click(screen.getByRole("button", { name: /apply approved/i }));
    await waitFor(() => expect(applyEnrichmentRun).toHaveBeenCalledWith(55, expect.any(Object)));
    await waitFor(() => expect(fetchEnrichmentReview).toHaveBeenCalledWith(55));
    expect(screen.getByTestId("enrichment-apply-result")).toHaveTextContent("Job #88 queued on");
  });
});
