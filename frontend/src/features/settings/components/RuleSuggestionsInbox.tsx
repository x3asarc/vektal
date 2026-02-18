"use client";

import { useEffect, useState } from "react";
import {
  acceptRuleSuggestion,
  declineRuleSuggestion,
  fetchRuleSuggestions,
} from "@/features/resolution/api/resolution-api";
import { ResolutionRuleSuggestion } from "@/shared/contracts/resolution";
import { ApiClientError } from "@/lib/api/client";

export function RuleSuggestionsInbox() {
  const [suggestions, setSuggestions] = useState<ResolutionRuleSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    void fetchRuleSuggestions()
      .then((items) => {
        if (!mounted) return;
        setSuggestions(items);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!mounted) return;
        if (reason instanceof ApiClientError) {
          setError(reason.normalized.detail);
        } else if (reason instanceof Error) {
          setError(reason.message);
        } else {
          setError("Unable to load rule suggestions.");
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  async function accept(suggestion: ResolutionRuleSuggestion) {
    await acceptRuleSuggestion(suggestion, suggestion.suggestedExpiryDays ?? 30);
    setSuggestions((prev) => prev.filter((item) => item.id !== suggestion.id));
  }

  async function decline(suggestionId: string) {
    await declineRuleSuggestion(suggestionId);
    setSuggestions((prev) => prev.filter((item) => item.id !== suggestionId));
  }

  return (
    <section className="panel" style={{ display: "grid", gap: 10 }}>
      <h2 style={{ margin: 0 }}>Rule Suggestions Inbox</h2>
      <p className="muted" style={{ margin: 0 }}>
        Batched suggestions generated from repeated dry-run overrides.
      </p>
      {loading && <p className="muted">Loading suggestions...</p>}
      {error && <p style={{ color: "var(--error)" }}>{error}</p>}
      {!loading && !error && suggestions.length === 0 && (
        <p className="muted">No suggestions pending.</p>
      )}
      {suggestions.map((suggestion) => (
        <article key={suggestion.id} className="panel" style={{ display: "grid", gap: 8 }}>
          <strong>
            {suggestion.supplierCode} • {suggestion.fieldGroup}
          </strong>
          <p className="muted" style={{ margin: 0 }}>
            {suggestion.reason}
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" onClick={() => void accept(suggestion)}>
              Accept suggestion
            </button>
            <button type="button" onClick={() => void decline(suggestion.id)}>
              Decline
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
