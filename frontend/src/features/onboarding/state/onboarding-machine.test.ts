import { describe, expect, it } from "vitest";
import {
  chooseIngestPath,
  connectShopify,
  INITIAL_ONBOARDING_STATE,
  startImport,
} from "@/features/onboarding/state/onboarding-machine";

describe("onboarding machine", () => {
  it("advances through connect -> choose -> preview -> progress", () => {
    const s1 = connectShopify(INITIAL_ONBOARDING_STATE);
    expect(s1.step).toBe("choose_ingest");

    const s2 = chooseIngestPath(s1, "sync_store");
    expect(s2.step).toBe("preview_start_import");
    expect(s2.ingestPath).toBe("sync_store");

    const s3 = startImport(s2);
    expect(s3.step).toBe("import_progress");
  });

  it("rejects invalid transition order", () => {
    const invalid = startImport(INITIAL_ONBOARDING_STATE);
    expect(invalid.step).toBe("connect_shopify");
  });
});
