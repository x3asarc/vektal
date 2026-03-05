"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, ApiClientError } from "@/lib/api/client";
import { setGuardFlags } from "@/lib/auth/session-flags";
import { resolveSafeRedirect } from "@/lib/auth/guards";

export default function LoginPage() {
  const devBypassEnabled = process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "1";
  const router = useRouter();
  const [returnTo, setReturnTo] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [existingSessionTarget, setExistingSessionTarget] = useState<string | null>(
    null,
  );
  const [existingSessionMessage, setExistingSessionMessage] = useState<string | null>(
    null,
  );
  const [resettingSession, setResettingSession] = useState(false);

  async function resetStaleSession() {
    setResettingSession(true);
    setError(null);
    try {
      await apiRequest<{ success: boolean }>("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Best effort reset.
    } finally {
      setGuardFlags({ A: false, V: false, S: false });
      setExistingSessionTarget(null);
      setExistingSessionMessage(null);
      setResettingSession(false);
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setReturnTo(params.get("returnTo"));
    const force = params.get("force") === "1";

    if (force) {
      setGuardFlags({ A: false, V: false, S: false });
      setCheckingSession(false);
      return;
    }

    const target = params.get("returnTo");
    let cancelled = false;

    void apiRequest<{
      user: { email_verified: boolean; account_status: string };
    }>("/api/v1/auth/me")
      .then((result) => {
        if (cancelled) return;
        const verified = Boolean(result.user.email_verified);
        const connected = result.user.account_status === "active";
        setGuardFlags({ A: true, V: verified, S: connected });
        const fallback = connected ? "/dashboard" : "/onboarding";
        setExistingSessionTarget(resolveSafeRedirect("/auth/login", target, fallback));
        setExistingSessionMessage(
          connected
            ? "You already have an active backend session."
            : "You already have a backend session but onboarding is still required.",
        );
        setCheckingSession(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiClientError && (err.normalized.status === 401 || err.normalized.status === 403)) {
          setGuardFlags({ A: false, V: false, S: false });
        }
        setCheckingSession(false);
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (checkingSession) {
    return (
      <div className="auth-page">
        <div className="auth-glow" aria-hidden />
        <div className="auth-card">
          <p className="muted forensic-center-muted">
            Checking session...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-glow" aria-hidden />

      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">
            <span className="material-symbols-rounded auth-icon">asterisk</span>
          </div>
          <span className="auth-logo-text">Platform</span>
        </div>

        <div>
          <h1 className="auth-heading">Sign in</h1>
          <p className="auth-subheading">Enter your credentials to continue.</p>
        </div>

        {existingSessionMessage ? (
          <div className="auth-notice">
            <p className="auth-message">{existingSessionMessage}</p>
            <div className="auth-notice-actions">
              <button
                className="btn-primary"
                type="button"
                onClick={() => {
                  if (existingSessionTarget) router.replace(existingSessionTarget);
                }}
              >
                Continue
              </button>
              <button
                className="btn-ghost"
                type="button"
                disabled={loading || resettingSession}
                onClick={() => {
                  void resetStaleSession();
                }}
              >
                {resettingSession ? "Resetting..." : "Use different account"}
              </button>
            </div>
          </div>
        ) : null}

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            setError(null);
            setLoading(true);
            void apiRequest<
              { success: boolean; user: { email_verified: boolean; account_status: string } },
              { email: string; password: string; remember_me: boolean }
            >("/api/v1/auth/login", {
              method: "POST",
              body: { email, password, remember_me: false },
            })
              .then((result) => {
                const verified = Boolean(result.user.email_verified);
                const connected = result.user.account_status === "active";
                setGuardFlags({ A: true, V: verified, S: connected });
                const fallback = connected ? "/dashboard" : "/onboarding";
                const target = resolveSafeRedirect("/auth/login", returnTo, fallback);
                router.replace(target);
              })
              .catch((err: unknown) => {
                if (err instanceof ApiClientError) setError(err.normalized.detail);
                else if (err instanceof Error) setError(err.message);
                else setError("Login failed.");
              })
              .finally(() => setLoading(false));
          }}
        >
          <div className="auth-field">
            <label className="auth-label" htmlFor="email">Email</label>
            <input
              className="auth-input"
              id="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
            />
          </div>
          <div className="auth-field">
            <label className="auth-label" htmlFor="password">Password</label>
            <input
              className="auth-input"
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="........"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
            />
          </div>
          {error ? <p className="auth-error">{error}</p> : null}
          <button className="auth-submit-btn" type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <div className="auth-notice-actions">
            <button
              className="btn-ghost"
              type="button"
              disabled={resettingSession || loading}
              onClick={() => { void resetStaleSession(); }}
            >
              {resettingSession ? "Resetting..." : "Reset stale session"}
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => router.replace("/auth/verify")}
            >
              Need email verification?
            </button>
          </div>
        </form>

        {devBypassEnabled ? (
          <div>
            <div className="auth-divider">dev only</div>
            <div className="auth-dev-section">
              <p className="auth-dev-label">Developer Session Controls</p>
              <div className="auth-dev-buttons">
                <button
                  className="btn-ghost auth-dev-pill"
                  type="button"
                  onClick={() => { setGuardFlags({ A: true, V: false, S: false }); router.replace("/auth/verify"); }}
                >
                  Unverified
                </button>
                <button
                  className="btn-ghost auth-dev-pill"
                  type="button"
                  onClick={() => { setGuardFlags({ A: true, V: true, S: false }); router.replace("/onboarding"); }}
                >
                  Verified
                </button>
                <button
                  className="btn-ghost auth-dev-pill"
                  type="button"
                  onClick={() => { setGuardFlags({ A: true, V: true, S: true }); router.replace("/dashboard"); }}
                >
                  Full access
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
