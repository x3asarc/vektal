import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ResolutionRuleSuggestion, StrategyQuizState } from "@/shared/contracts/resolution";

const {
  saveStrategyQuizMock,
  fetchRuleSuggestionsMock,
  acceptRuleSuggestionMock,
  declineRuleSuggestionMock,
} = vi.hoisted(() => ({
  saveStrategyQuizMock: vi.fn<(input: StrategyQuizState, supplierCode?: string) => Promise<void>>(),
  fetchRuleSuggestionsMock: vi.fn<() => Promise<ResolutionRuleSuggestion[]>>(),
  acceptRuleSuggestionMock: vi.fn<(input: ResolutionRuleSuggestion, expiryDays?: number) => Promise<void>>(),
  declineRuleSuggestionMock: vi.fn<(id: string) => Promise<void>>(),
}));

vi.mock("@/features/resolution/api/resolution-api", () => ({
  saveStrategyQuiz: saveStrategyQuizMock,
  fetchRuleSuggestions: fetchRuleSuggestionsMock,
  acceptRuleSuggestion: acceptRuleSuggestionMock,
  declineRuleSuggestion: declineRuleSuggestionMock,
}));

import { StrategyQuiz } from "@/features/settings/components/StrategyQuiz";
import { RuleSuggestionsInbox } from "@/features/settings/components/RuleSuggestionsInbox";

describe("strategy quiz contract", () => {
  beforeEach(() => {
    saveStrategyQuizMock.mockReset().mockResolvedValue(undefined);
    fetchRuleSuggestionsMock.mockReset().mockResolvedValue([
      {
        id: "s-1",
        supplierCode: "PENTART",
        fieldGroup: "pricing",
        action: "auto_apply",
        reason: "You approved pricing updates 5 times.",
        suggestedExpiryDays: 30,
      },
    ]);
    acceptRuleSuggestionMock.mockReset().mockResolvedValue(undefined);
    declineRuleSuggestionMock.mockReset().mockResolvedValue(undefined);
  });

  it("captures constrained quiz inputs and saves", async () => {
    render(<StrategyQuiz supplierCode="PENTART" />);

    expect(
      screen.getByRole("option", { name: /Create as draft/i }),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByLabelText(/New variants when matched SKU/i),
      { target: { value: "ask_every_time" } },
    );
    fireEvent.click(screen.getByRole("button", { name: /save strategy quiz/i }));

    await waitFor(() => expect(saveStrategyQuizMock).toHaveBeenCalledTimes(1));
    expect(saveStrategyQuizMock.mock.calls[0][1]).toBe("PENTART");
  });

  it("shows rule suggestions and supports accept/decline actions", async () => {
    render(<RuleSuggestionsInbox />);
    expect(await screen.findByText(/You approved pricing updates 5 times/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /accept suggestion/i }));
    await waitFor(() => expect(acceptRuleSuggestionMock).toHaveBeenCalledTimes(1));

    fetchRuleSuggestionsMock.mockResolvedValue([
      {
        id: "s-2",
        supplierCode: "PENTART",
        fieldGroup: "text",
        action: "require_approval",
        reason: "Description edits repeatedly overridden.",
      },
    ]);
    render(<RuleSuggestionsInbox />);
    expect(await screen.findByText(/Description edits repeatedly overridden/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /decline/i }));
    await waitFor(() => expect(declineRuleSuggestionMock).toHaveBeenCalledTimes(1));
  });
});
