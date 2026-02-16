"use client";

import { FormEvent, useState } from "react";
import { EnrichmentLanguage, EnrichmentProfile, EnrichmentStartRequest } from "@/features/enrichment/api/enrichment-api";

type EnrichmentRunConfiguratorProps = {
  onStart: (payload: EnrichmentStartRequest) => Promise<void>;
  isSubmitting: boolean;
};

const DEMO_MUTATIONS = [
  {
    product_id: 101,
    field_name: "title",
    current_value: "Old title",
    proposed_value: "New title",
    confidence: 0.91,
    provenance: { source: "ai_inferred" },
  },
  {
    product_id: 101,
    field_name: "alt_text",
    current_value: "old alt",
    proposed_value: "new alt",
    confidence: 0.71,
    provenance: { source: "ai_inferred" },
  },
];

export function EnrichmentRunConfigurator({ onStart, isSubmitting }: EnrichmentRunConfiguratorProps) {
  const [supplierCode, setSupplierCode] = useState("PENTART");
  const [runProfile, setRunProfile] = useState<EnrichmentProfile>("standard");
  const [targetLanguage, setTargetLanguage] = useState<EnrichmentLanguage>("de");
  const [dryRunTtl, setDryRunTtl] = useState(60);
  const [supplierVerified, setSupplierVerified] = useState(true);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await onStart({
      supplier_code: supplierCode.trim(),
      supplier_verified: supplierVerified,
      alt_text_policy: "preserve",
      run_profile: runProfile,
      target_language: targetLanguage,
      dry_run_ttl_minutes: dryRunTtl,
      mutations: DEMO_MUTATIONS,
    });
  }

  return (
    <section className="panel" data-testid="enrichment-run-configurator">
      <h2>Run Configurator</h2>
      <p className="muted">Dry-run first. Apply only after review and explicit confirmation.</p>
      <form onSubmit={handleSubmit} style={{ display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
        <label>
          Supplier code
          <input
            type="text"
            value={supplierCode}
            onChange={(event) => setSupplierCode(event.target.value)}
            aria-label="supplier code"
          />
        </label>
        <label>
          Profile
          <select
            value={runProfile}
            onChange={(event) => setRunProfile(event.target.value as EnrichmentProfile)}
            aria-label="run profile"
          >
            <option value="quick">quick</option>
            <option value="standard">standard</option>
            <option value="deep">deep</option>
          </select>
        </label>
        <label>
          Language
          <select
            value={targetLanguage}
            onChange={(event) => setTargetLanguage(event.target.value as EnrichmentLanguage)}
            aria-label="target language"
          >
            <option value="de">de</option>
            <option value="en">en</option>
          </select>
        </label>
        <label>
          Dry-run TTL (minutes)
          <input
            type="number"
            min={5}
            max={10080}
            value={dryRunTtl}
            onChange={(event) => setDryRunTtl(Number(event.target.value))}
            aria-label="dry run ttl"
          />
        </label>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <input
            type="checkbox"
            checked={supplierVerified}
            onChange={(event) => setSupplierVerified(event.target.checked)}
            aria-label="supplier verified"
          />
          Supplier verified
        </label>
        <div style={{ display: "flex", alignItems: "end" }}>
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Starting..." : "Start dry-run"}
          </button>
        </div>
      </form>
    </section>
  );
}
