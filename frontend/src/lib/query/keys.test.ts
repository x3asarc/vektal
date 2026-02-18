import { describe, expect, it } from "vitest";
import { authKeys, hasScopedKeyShape, jobsKeys, resolutionKeys } from "@/lib/query/keys";

const scope = { storeId: "s1", userId: "u1" };

describe("query keys", () => {
  it("always keeps scope object in key segment 2", () => {
    const key = jobsKeys.detail(scope, "job-1");
    expect(key[1]).toEqual(scope);
    expect(hasScopedKeyShape(key)).toBe(true);
  });

  it("provides stable auth key shape", () => {
    const key = authKeys.me(scope);
    expect(key[0]).toBe("auth");
    expect(key[1]).toEqual(scope);
    expect(key[2]).toBe("me");
  });

  it("exposes scoped resolution key shape", () => {
    const key = resolutionKeys.dryRun(scope, 42);
    expect(key[0]).toBe("resolution");
    expect(hasScopedKeyShape(key)).toBe(true);
  });
});
