import { describe, expect, it } from "vitest";
import { normalizeProblemDetails } from "@/lib/api/problem-details";

describe("normalizeProblemDetails", () => {
  it("supports legacy errors map", () => {
    const normalized = normalizeProblemDetails(
      {
        type: "/problems/validation",
        title: "Validation failed",
        status: 400,
        detail: "Input was invalid",
        errors: {
          email: ["Invalid email"],
        },
      },
      500,
    );

    expect(normalized.status).toBe(400);
    expect(normalized.scope).toBe("field");
    expect(normalized.fieldErrors.email).toEqual(["Invalid email"]);
  });

  it("supports violations list format", () => {
    const normalized = normalizeProblemDetails({
      status: 422,
      violations: [{ field: "sku", reason: "Required" }],
    });

    expect(normalized.status).toBe(422);
    expect(normalized.fieldErrors.sku).toEqual(["Required"]);
  });

  it("marks 5xx errors as retryable and degrading", () => {
    const normalized = normalizeProblemDetails({ status: 503, detail: "Outage" }, 500);
    expect(normalized.canRetry).toBe(true);
    expect(normalized.severity).toBe("degrading");
  });

  it("derives a useful detail from raw html text error payload", () => {
    const normalized = normalizeProblemDetails("<html>Login required</html>", 401);
    expect(normalized.detail).toContain("Authentication is required");
  });
});
