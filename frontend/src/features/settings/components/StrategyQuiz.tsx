"use client";

import { FormEvent, useState } from "react";
import { saveStrategyQuiz } from "@/features/resolution/api/resolution-api";
import { StrategyQuizState } from "@/shared/contracts/resolution";
import { ApiClientError } from "@/lib/api/client";

const INITIAL_STATE: StrategyQuizState = {
  variantMismatchPolicy: "create_draft",
  scrapeVariantPolicy: "scrape_all",
  firstBatchExecution: "immediate",
  saveFirstBatchChoice: true,
  consentAutoCreateVariants: false,
  consentFieldGroups: ["pricing"],
  notes: "",
};

type StrategyQuizProps = {
  supplierCode?: string;
};

export function StrategyQuiz({ supplierCode = "*" }: StrategyQuizProps) {
  const [state, setState] = useState<StrategyQuizState>(INITIAL_STATE);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  function toggleFieldGroup(group: "images" | "text" | "pricing" | "ids") {
    setState((prev) => ({
      ...prev,
      consentFieldGroups: prev.consentFieldGroups.includes(group)
        ? prev.consentFieldGroups.filter((item) => item !== group)
        : [...prev.consentFieldGroups, group],
    }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await saveStrategyQuiz(state, supplierCode);
      setMessage("Strategy quiz saved.");
    } catch (error: unknown) {
      if (error instanceof ApiClientError) {
        setMessage(error.normalized.detail);
      } else if (error instanceof Error) {
        setMessage(error.message);
      } else {
        setMessage("Unable to save strategy quiz.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
      <h2 style={{ margin: 0 }}>Supplier Strategy Quiz</h2>
      <p className="muted" style={{ margin: 0 }}>
        Structured onboarding rules for supplier behavior and dry-run defaults.
      </p>

      <label>
        New variants when matched SKU has missing options:
        <select
          value={state.variantMismatchPolicy}
          onChange={(event) =>
            setState((prev) => ({
              ...prev,
              variantMismatchPolicy: event.currentTarget.value as StrategyQuizState["variantMismatchPolicy"],
            }))
          }
        >
          <option value="create_draft">Create as draft</option>
          <option value="ignore">Ignore</option>
          <option value="ask_every_time">Ask every time</option>
        </select>
      </label>

      <label>
        Supplier scraping policy:
        <select
          value={state.scrapeVariantPolicy}
          onChange={(event) =>
            setState((prev) => ({
              ...prev,
              scrapeVariantPolicy: event.currentTarget.value as StrategyQuizState["scrapeVariantPolicy"],
            }))
          }
        >
          <option value="scrape_all">Scrape all variants automatically</option>
          <option value="base_only">Only scrape base product</option>
        </select>
      </label>

      <label>
        First batch execution mode:
        <select
          value={state.firstBatchExecution}
          onChange={(event) =>
            setState((prev) => ({
              ...prev,
              firstBatchExecution: event.currentTarget.value as StrategyQuizState["firstBatchExecution"],
            }))
          }
        >
          <option value="immediate">Immediate</option>
          <option value="scheduled">Scheduled</option>
        </select>
      </label>

      <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          type="checkbox"
          checked={state.saveFirstBatchChoice}
          onChange={(event) =>
            setState((prev) => ({ ...prev, saveFirstBatchChoice: event.currentTarget.checked }))
          }
        />
        Save first-batch execution choice for future batches
      </label>

      <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          type="checkbox"
          checked={state.consentAutoCreateVariants}
          onChange={(event) =>
            setState((prev) => ({ ...prev, consentAutoCreateVariants: event.currentTarget.checked }))
          }
        />
        Consent to auto-create missing variants (safe defaults only)
      </label>

      <fieldset style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 10 }}>
        <legend>Field-group consent scope</legend>
        {(["images", "text", "pricing", "ids"] as const).map((group) => (
          <label key={group} style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              type="checkbox"
              checked={state.consentFieldGroups.includes(group)}
              onChange={() => toggleFieldGroup(group)}
            />
            {group}
          </label>
        ))}
      </fieldset>

      <label>
        Notes
        <textarea
          value={state.notes ?? ""}
          onChange={(event) =>
            setState((prev) => ({ ...prev, notes: event.currentTarget.value }))
          }
          rows={3}
        />
      </label>

      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save strategy quiz"}
      </button>
      {message && <p className="muted">{message}</p>}
    </form>
  );
}
