import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CommandCenter } from "./CommandCenter";
import { ApiClientError } from "@/lib/api/client";
import type { NormalizedApiError } from "@/shared/contracts";

vi.mock("@/lib/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/client")>("@/lib/api/client");
  return {
    ...actual,
    apiRequest: vi.fn(),
  };
});

const { apiRequest } = await import("@/lib/api/client");

describe("CommandCenter", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows store connection required when dashboard summary returns 409", async () => {
    const normalized: NormalizedApiError = {
      type: "store-not-connected",
      title: "Store Not Connected",
      status: 409,
      detail: "Connect a Shopify store to view dashboard metrics.",
      fieldErrors: {},
      scope: "global",
      severity: "blocking",
      canRetry: false,
    };

    (apiRequest as ReturnType<typeof vi.fn>).mockRejectedValue(
      new ApiClientError(normalized),
    );

    render(<CommandCenter />);

    expect(await screen.findByText("STORE_CONNECTION_REQUIRED")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "OPEN_ONBOARDING" })).toBeInTheDocument();
  });
});
