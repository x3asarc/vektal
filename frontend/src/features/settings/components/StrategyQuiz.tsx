"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
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

type MessageTone = "ok" | "error";

export function StrategyQuiz({ supplierCode = "*" }: StrategyQuizProps) {
  const [state, setState] = useState<StrategyQuizState>(INITIAL_STATE);
  const [lastSavedState, setLastSavedState] = useState<StrategyQuizState>(INITIAL_STATE);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [tone, setTone] = useState<MessageTone>("ok");

  const hasUnsavedChanges = useMemo(
    () => JSON.stringify(state) !== JSON.stringify(lastSavedState),
    [lastSavedState, state],
  );

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!hasUnsavedChanges) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasUnsavedChanges]);

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
      setLastSavedState(state);
      setTone("ok");
      setMessage("Strategy quiz saved.");
    } catch (error: unknown) {
      setTone("error");
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
    <form className="panel strategy-grid" onSubmit={(event) => { void onSubmit(event); }}>
      <h2 className="forensic-card-title">Supplier Strategy Quiz</h2>
      <p className="forensic-card-copy">
        Structured onboarding rules for supplier behavior and dry-run defaults.
      </p>

      <label className="forensic-field">
        <span className="forensic-field-label">New variants when matched SKU has missing options:</span>
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

      <label className="forensic-field">
        <span className="forensic-field-label">Supplier scraping policy:</span>
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

      <label className="forensic-field">
        <span className="forensic-field-label">First batch execution mode:</span>
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

      <label className="forensic-field strategy-row-inline">
        <input
          type="checkbox"
          checked={state.saveFirstBatchChoice}
          onChange={(event) =>
            setState((prev) => ({ ...prev, saveFirstBatchChoice: event.currentTarget.checked }))
          }
        />
        Save first-batch execution choice for future batches
      </label>

      <label className="forensic-field strategy-row-inline">
        <input
          type="checkbox"
          checked={state.consentAutoCreateVariants}
          onChange={(event) =>
            setState((prev) => ({ ...prev, consentAutoCreateVariants: event.currentTarget.checked }))
          }
        />
        Consent to auto-create missing variants (safe defaults only)
      </label>

      <fieldset className="forensic-fieldset">
        <legend>Field-group consent scope</legend>
        {(["images", "text", "pricing", "ids"] as const).map((group) => (
          <label key={group} className="forensic-field strategy-row-inline">
            <input
              type="checkbox"
              checked={state.consentFieldGroups.includes(group)}
              onChange={() => toggleFieldGroup(group)}
            />
            {group}
          </label>
        ))}
      </fieldset>

      <label className="forensic-field">
        <span className="forensic-field-label">Notes</span>
        <textarea
          value={state.notes ?? ""}
          onChange={(event) =>
            setState((prev) => ({ ...prev, notes: event.currentTarget.value }))
          }
          rows={3}
        />
      </label>

      <div className="forensic-actions">
        <button className="btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save strategy quiz"}
        </button>
        <button
          className="btn-ghost"
          type="button"
          onClick={() => setState(lastSavedState)}
          disabled={!hasUnsavedChanges}
        >
          Reset changes
        </button>
        {hasUnsavedChanges ? (
          <span className="forensic-state-tag" data-state="warning">Unsaved changes</span>
        ) : (
          <span className="forensic-state-tag" data-state="ok">Saved</span>
        )}
      </div>

      {message ? (
        <p className={tone === "error" ? "chat-action-warning" : "forensic-card-copy"}>
          {message}
        </p>
      ) : null}
    </form>
  );
}
