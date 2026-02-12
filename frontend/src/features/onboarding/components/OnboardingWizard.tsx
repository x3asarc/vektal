"use client";

import { useMemo, useState } from "react";
import {
  chooseIngestPath,
  connectShopify,
  INITIAL_ONBOARDING_STATE,
  markComplete,
  OnboardingState,
  startImport,
  toggleAdvanced,
} from "@/features/onboarding/state/onboarding-machine";
import {
  useConnectShopifyMutation,
  useStartImportMutation,
} from "@/features/onboarding/api/onboarding-mutations";
import { setGuardFlags } from "@/lib/auth/session-flags";
import { ApiClientError } from "@/lib/api/client";

function nextState(
  state: OnboardingState,
  action: "connect" | "sync" | "csv" | "start" | "done" | "advanced",
) {
  switch (action) {
    case "connect":
      return connectShopify(state);
    case "sync":
      return chooseIngestPath(state, "sync_store");
    case "csv":
      return chooseIngestPath(state, "upload_csv");
    case "start":
      return startImport(state);
    case "done":
      return markComplete(state);
    case "advanced":
      return toggleAdvanced(state);
    default:
      return state;
  }
}

export function OnboardingWizard() {
  const [state, setState] = useState(INITIAL_ONBOARDING_STATE);
  const [shopDomain, setShopDomain] = useState("example.myshopify.com");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [isRedirectingToShopify, setIsRedirectingToShopify] = useState(false);
  const connectMutation = useConnectShopifyMutation();
  const startMutation = useStartImportMutation();

  function setUiError(error: unknown) {
    if (error instanceof ApiClientError) {
      const statusSuffix =
        error.normalized.status > 0 ? ` (HTTP ${error.normalized.status})` : "";
      setErrorMessage(`${error.normalized.detail}${statusSuffix}`);
      return;
    }
    if (error instanceof Error) {
      setErrorMessage(error.message);
      return;
    }
    setErrorMessage("The request could not be completed.");
  }

  const stepLabel = useMemo(() => {
    switch (state.step) {
      case "connect_shopify":
        return "Step 1: Connect Shopify";
      case "choose_ingest":
        return "Step 2: Choose ingest path";
      case "preview_start_import":
        return "Step 3: Preview and Start Import";
      case "import_progress":
        return "Import Progress";
      case "completed":
        return "Complete";
      default:
        return state.step;
    }
  }, [state.step]);

  return (
    <section className="panel">
      <h2>{stepLabel}</h2>
      <p className="muted">
        Completion rule: either Sync Store or Upload CSV path can complete
        onboarding.
      </p>

      {state.step === "connect_shopify" && (
        <div style={{ display: "grid", gap: 8 }}>
          <label htmlFor="shop-domain">Shopify Domain</label>
          <input
            id="shop-domain"
            value={shopDomain}
            onChange={(event) => setShopDomain(event.currentTarget.value)}
          />
          <button
            type="button"
            disabled={isRedirectingToShopify}
            onClick={() => {
              setErrorMessage(null);
              void connectMutation
                .mutateAsync({ shopDomain })
                .then((result) => {
                  if (!result.auth_url) {
                    throw new Error("Missing auth_url in OAuth response.");
                  }
                  setAuthUrl(result.auth_url);
                  setIsRedirectingToShopify(true);
                  window.location.assign(result.auth_url);
                })
                .catch((error: unknown) => {
                  setIsRedirectingToShopify(false);
                  setUiError(error);
                });
            }}
          >
            {isRedirectingToShopify ? "Redirecting to Shopify..." : "Connect Shopify"}
          </button>
          {authUrl && (
            <p className="muted">
              Shopify auth URL generated:
              {" "}
              <a href={authUrl} target="_blank" rel="noreferrer">
                Open authorization page
              </a>
            </p>
          )}
        </div>
      )}

      {state.step === "choose_ingest" && (
        <div style={{ display: "grid", gap: 8 }}>
          <p>
            Choose ingest path:
            <strong> Sync Store </strong>
            is the primary CTA.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" onClick={() => setState((prev) => nextState(prev, "sync"))}>
              Sync Store
            </button>
            <button type="button" onClick={() => setState((prev) => nextState(prev, "csv"))}>
              Upload CSV
            </button>
          </div>
        </div>
      )}

      {state.step === "preview_start_import" && (
        <div style={{ display: "grid", gap: 8 }}>
          <p>
            Preview and Start Import
            {state.ingestPath === "sync_store"
              ? " - Sync defaults to import everything."
              : " - CSV ingest selected."}
          </p>
          <button
            type="button"
            onClick={() => setState((prev) => nextState(prev, "advanced"))}
          >
            {state.advancedOpen ? "Hide" : "Show"} advanced options
          </button>
          {state.advancedOpen && (
            <div className="panel">
              <p className="muted">
                Advanced scope/filter options are explicit. Empty selections do
                not silently alter import intent.
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={() => {
              setErrorMessage(null);
              void startMutation
                .mutateAsync({
                  ingestPath: state.ingestPath ?? "sync_store",
                  includeAll: true,
                })
                .then(() => {
                  setState((prev) => nextState(prev, "start"));
                })
                .catch(setUiError);
            }}
          >
            Preview and Start Import
          </button>
        </div>
      )}

      {state.step === "import_progress" && (
        <div style={{ display: "grid", gap: 8 }}>
          <p>Import in progress. You can navigate away without blocking.</p>
          <button
            type="button"
            onClick={() => {
              setState((prev) => nextState(prev, "done"));
              setGuardFlags({ A: true, V: true, S: true });
            }}
          >
            Mark onboarding complete
          </button>
        </div>
      )}

      {state.step === "completed" && (
        <p>
          Onboarding complete. You can now use
          <strong> /dashboard </strong>
          as the default landing.
        </p>
      )}

      {errorMessage && (
        <div className="panel" style={{ borderColor: "var(--error)" }}>
          <strong>Request error</strong>
          <p className="muted">{errorMessage}</p>
        </div>
      )}
    </section>
  );
}
