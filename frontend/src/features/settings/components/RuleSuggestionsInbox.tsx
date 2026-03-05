"use client";

import { useCallback, useEffect, useState } from "react";
import { OperationalErrorCard } from "@/components/OperationalErrorCard";
import {
  acceptRuleSuggestion,
  declineRuleSuggestion,
  fetchRuleSuggestions,
} from "@/features/resolution/api/resolution-api";
import { ResolutionRuleSuggestion } from "@/shared/contracts/resolution";
import { ApiClientError } from "@/lib/api/client";
import { stableDiagnosticId } from "@/lib/diagnostics";

type EditableSuggestion = ResolutionRuleSuggestion & {
  actionDraft: string;
  expiryDaysDraft: number;
};

export function RuleSuggestionsInbox() {
  const [suggestions, setSuggestions] = useState<EditableSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSuggestionId, setActiveSuggestionId] = useState<string | null>(null);

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const items = await fetchRuleSuggestions();
      const editableItems = items.map((item) => ({
        ...item,
        actionDraft: item.action,
        expiryDaysDraft: item.suggestedExpiryDays ?? 30,
      }));
      setSuggestions(editableItems);
      setError(null);
    } catch (reason: unknown) {
      if (reason instanceof ApiClientError) {
        setError(reason.normalized.detail);
      } else if (reason instanceof Error) {
        setError(reason.message);
      } else {
        setError("Unable to load rule suggestions.");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSuggestions();
  }, [loadSuggestions]);

  async function accept(suggestion: EditableSuggestion) {
    setActiveSuggestionId(suggestion.id);
    try {
      await acceptRuleSuggestion(
        {
          ...suggestion,
          action: suggestion.actionDraft,
        },
        suggestion.expiryDaysDraft,
      );
      setSuggestions((prev) => prev.filter((item) => item.id !== suggestion.id));
      setError(null);
    } catch (reason: unknown) {
      if (reason instanceof Error) setError(reason.message);
      else setError("Unable to accept suggestion.");
    } finally {
      setActiveSuggestionId(null);
    }
  }

  async function decline(suggestionId: string) {
    setActiveSuggestionId(suggestionId);
    try {
      await declineRuleSuggestion(suggestionId);
      setSuggestions((prev) => prev.filter((item) => item.id !== suggestionId));
      setError(null);
    } catch (reason: unknown) {
      if (reason instanceof Error) setError(reason.message);
      else setError("Unable to decline suggestion.");
    } finally {
      setActiveSuggestionId(null);
    }
  }

  return (
    <section className="panel strategy-grid">
      <h2 className="forensic-card-title">Rule Suggestions Inbox</h2>
      <p className="forensic-card-copy">
        Batched suggestions generated from repeated dry-run overrides.
      </p>
      {loading ? <p className="forensic-card-copy">Loading suggestions...</p> : null}
      {error ? (
        <OperationalErrorCard
          title="Rule suggestions unavailable"
          detail={error}
          diagnosticId={stableDiagnosticId(error)}
          retryLabel="Retry load"
          onRetry={() => { void loadSuggestions(); }}
        />
      ) : null}
      {!loading && !error && suggestions.length === 0 ? (
        <p className="forensic-card-copy">No suggestions pending.</p>
      ) : null}

      {suggestions.map((suggestion) => (
        <article key={suggestion.id} className="suggestion-card">
          <strong className="forensic-card-title">
            {suggestion.supplierCode} / {suggestion.fieldGroup}
          </strong>
          <p className="forensic-card-copy">
            {suggestion.reason}
          </p>

          <div className="suggestion-edit-grid">
            <label className="forensic-field">
              <span className="forensic-field-label">Action override</span>
              <input
                value={suggestion.actionDraft}
                onChange={(event) =>
                  setSuggestions((prev) =>
                    prev.map((item) =>
                      item.id === suggestion.id ? { ...item, actionDraft: event.target.value } : item,
                    ),
                  )
                }
              />
            </label>
            <label className="forensic-field">
              <span className="forensic-field-label">Expiry days</span>
              <input
                type="number"
                min={1}
                max={365}
                value={suggestion.expiryDaysDraft}
                onChange={(event) =>
                  setSuggestions((prev) =>
                    prev.map((item) =>
                      item.id === suggestion.id
                        ? { ...item, expiryDaysDraft: Number(event.target.value) || 30 }
                        : item,
                    ),
                  )
                }
              />
            </label>
          </div>

          <p className="forensic-inline-note">
            Preview: {suggestion.action} {"->"} {suggestion.actionDraft}
          </p>

          <div className="forensic-actions">
            <button
              className="btn-primary"
              type="button"
              onClick={() => { void accept(suggestion); }}
              disabled={activeSuggestionId === suggestion.id}
            >
              Accept suggestion
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => { void decline(suggestion.id); }}
              disabled={activeSuggestionId === suggestion.id}
            >
              Decline
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
