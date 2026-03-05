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
import { apiRequest, ApiClientError } from "@/lib/api/client";
import { useJobDetailObserver } from "@/lib/jobs/useJobDetailObserver";

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
  const [csvRaw, setCsvRaw] = useState("sku,title,price");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [authUrl, setAuthUrl] = useState<string | null>(null);
  const [activeJobId, setActiveJobId] = useState<number | string | null>(null);
  const [isRedirectingToShopify, setIsRedirectingToShopify] = useState(false);
  const connectMutation = useConnectShopifyMutation();
  const startMutation = useStartImportMutation();
  const observed = useJobDetailObserver(activeJobId);

  function redirectToTopWindow(url: string) {
    try {
      if (window.top && window.top !== window.self) {
        window.top.location.href = url;
        return;
      }
    } catch {
      // Ignore cross-origin access errors and fallback to same-window redirect.
    }
    window.location.assign(url);
  }

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

  const progress = useMemo(() => {
    const map: Record<OnboardingState["step"], number> = {
      connect_shopify: 1,
      choose_ingest: 2,
      preview_start_import: 3,
      import_progress: 3,
      completed: 3,
    };
    return map[state.step] ?? 1;
  }, [state.step]);

  const csvSummary = useMemo(() => {
    const lines = csvRaw
      .split(/\r?\n/g)
      .map((line) => line.trim())
      .filter(Boolean);
    if (lines.length <= 1) {
      return { rows: 0, invalid: 0 };
    }
    const dataLines = lines.slice(1);
    let invalid = 0;
    for (const line of dataLines) {
      const columns = line.split(",").map((part) => part.trim());
      if (columns.length < 2 || !columns[0]) invalid += 1;
    }
    return { rows: dataLines.length, invalid };
  }, [csvRaw]);

  return (
    <section className="panel">
      <h2 className="forensic-card-title">{stepLabel}</h2>
      <p className="forensic-card-copy">
        Completion rule: either Sync Store or Upload CSV path can complete
        onboarding.
      </p>

      <div className="forensic-chip-row">
        <span className={`forensic-chip ${progress >= 1 ? "is-active" : ""}`}>1. Connect</span>
        <span className={`forensic-chip ${progress >= 2 ? "is-active" : ""}`}>2. Upload / Sync</span>
        <span className={`forensic-chip ${progress >= 3 ? "is-active" : ""}`}>3. Preview</span>
      </div>

      {state.step === "connect_shopify" && (
        <div className="onboarding-step">
          <label htmlFor="shop-domain" className="forensic-field-label">Shopify Domain</label>
          <input
            id="shop-domain"
            value={shopDomain}
            onChange={(event) => setShopDomain(event.currentTarget.value)}
          />
          <button
            className="btn-primary"
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
                  redirectToTopWindow(result.auth_url);
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
            <p className="forensic-card-copy">
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
        <div className="onboarding-step">
          <p className="forensic-card-copy">
            Choose ingest path:
            <strong> Sync Store </strong>
            is the primary CTA.
          </p>
          <div className="forensic-actions">
            <button className="btn-primary" type="button" onClick={() => setState((prev) => nextState(prev, "sync"))}>
              Sync Store
            </button>
            <button className="btn-ghost" type="button" onClick={() => setState((prev) => nextState(prev, "csv"))}>
              Upload CSV
            </button>
          </div>
        </div>
      )}

      {state.step === "preview_start_import" && (
        <div className="onboarding-step">
          <p className="forensic-card-copy">
            Preview and Start Import
            {state.ingestPath === "sync_store"
              ? " - Sync defaults to import everything."
              : " - CSV ingest selected."}
          </p>
          <button
            className="btn-ghost"
            type="button"
            onClick={() => setState((prev) => nextState(prev, "advanced"))}
          >
            {state.advancedOpen ? "Hide" : "Show"} advanced options
          </button>
          {state.advancedOpen && (
            <div className="panel">
              <p className="forensic-card-copy">
                Advanced scope/filter options are explicit. Empty selections do
                not silently alter import intent.
              </p>
            </div>
          )}
          {state.ingestPath === "upload_csv" && (
            <div className="panel onboarding-csv-panel">
              <label className="forensic-field">
                <span className="forensic-field-label">CSV payload</span>
                <textarea
                  rows={6}
                  value={csvRaw}
                  onChange={(event) => setCsvRaw(event.target.value)}
                  placeholder={"sku,title,price\nSKU-100,Paint A,12.99"}
                />
              </label>
              <div className="forensic-chip-row">
                <span className="forensic-chip">Rows: {csvSummary.rows}</span>
                <span className={`forensic-chip ${csvSummary.invalid > 0 ? "is-warning" : ""}`}>
                  Invalid: {csvSummary.invalid}
                </span>
              </div>
            </div>
          )}
          <button
            className="btn-primary"
            type="button"
            onClick={() => {
              setErrorMessage(null);
              void startMutation
                .mutateAsync({
                  ingestPath: state.ingestPath ?? "sync_store",
                  includeAll: true,
                })
                .then((result) => {
                  setActiveJobId(result.job_id);
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
        <div className="onboarding-step">
          <p className="forensic-card-copy">Import in progress. You can navigate away without blocking.</p>
          {observed.job ? (
            <>
              <div className="progress-shell" aria-label="onboarding-progress">
                <div
                  className="progress-bar"
                  style={{
                    width: `${Math.max(0, Math.min(100, observed.job.percent_complete ?? 0))}%`,
                  }}
                />
              </div>
              <div className="onboarding-status-grid">
                <div className="panel">
                  <p className="forensic-inline-note">Progress</p>
                  <p className="forensic-card-copy">
                {Number(observed.job.percent_complete ?? 0).toFixed(1)}% complete
                  </p>
                </div>
                <div className="panel">
                  <p className="forensic-inline-note">Step</p>
                  <p className="forensic-card-copy">
                Step: <strong>{observed.job.current_step_label ?? observed.job.current_step ?? "Queued"}</strong>
                  </p>
                </div>
                <div className="panel">
                  <p className="forensic-inline-note">ETA</p>
                  <p className="forensic-card-copy">
                ETA: <strong>{typeof observed.job.eta_seconds === "number" ? `${observed.job.eta_seconds}s` : "Calculating ETA..."}</strong>
                  </p>
                </div>
                <div className="panel">
                  <p className="forensic-inline-note">Processed</p>
                  <p className="forensic-card-copy">
                Processed: <strong>{observed.job.processed_items ?? 0}</strong> / <strong>{observed.job.total_items ?? 0}</strong>
                  </p>
                </div>
              </div>
              {observed.job.error_message && (
                <p className="chat-action-warning">
                  {observed.job.error_message}
                </p>
              )}
              <div className="forensic-actions">
                {observed.job.results_url && (
                  <a className="btn-ghost" href={observed.job.results_url}>View results</a>
                )}
                {activeJobId && (
                  <a className="btn-ghost" href={`/jobs/${activeJobId}`}>Open job detail</a>
                )}
                {observed.job.can_retry && activeJobId && (
                  <button
                    className="btn-ghost"
                    type="button"
                    disabled={retrying}
                    onClick={() => {
                      setRetryError(null);
                      setRetrying(true);
                      void apiRequest<{ job_id: number }>(`/api/v1/jobs/${activeJobId}/retry`, { method: "POST" })
                        .then((result) => {
                          setActiveJobId(result.job_id);
                        })
                        .catch((reason: unknown) => {
                          if (reason instanceof ApiClientError) {
                            setRetryError(`${reason.normalized.detail} (HTTP ${reason.normalized.status})`);
                          } else if (reason instanceof Error) {
                            setRetryError(reason.message);
                          } else {
                            setRetryError("Retry request failed.");
                          }
                        })
                        .finally(() => {
                          setRetrying(false);
                        });
                    }}
                  >
                    {retrying ? "Retrying..." : "Retry import"}
                  </button>
                )}
              </div>
            </>
          ) : (
            <p className="forensic-card-copy">Waiting for live job status...</p>
          )}
          {retryError && (
            <p className="chat-action-warning">
              {retryError}
            </p>
          )}
          <button
            className="btn-primary"
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
        <p className="forensic-card-copy">
          Onboarding complete. You can now use
          <strong> /dashboard </strong>
          as the default landing.
        </p>
      )}

      {errorMessage && (
        <div className="chat-action-warning">
          <strong>Request error</strong> {errorMessage}
        </div>
      )}
    </section>
  );
}
