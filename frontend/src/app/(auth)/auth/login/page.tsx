"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiRequest, ApiClientError } from "@/lib/api/client";
import { setGuardFlags } from "@/lib/auth/session-flags";
import { resolveSafeRedirect } from "@/lib/auth/guards";

export default function LoginPage() {
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
      .catch(() => {
        if (cancelled) return;
        setGuardFlags({ A: false, V: false, S: false });
        setCheckingSession(false);
      });

    return () => {
      cancelled = true;
    };
  }, [router]);

  if (checkingSession) {
    return (
      <main>
        <h1>login</h1>
        <p className="muted">Checking existing session...</p>
      </main>
    );
  }

  return (
    <main>
      <h1>login</h1>
      <p className="muted">
        Already-authenticated users are redirected to a safe return path or
        /dashboard.
      </p>
      <section className="panel">
        <h2>Backend Login</h2>
        <p className="muted">
          Sign in creates backend session cookie used by OAuth and jobs APIs.
        </p>
        {existingSessionMessage && (
          <div className="panel" style={{ marginBottom: 8 }}>
            <p className="muted">{existingSessionMessage}</p>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => {
                  if (existingSessionTarget) {
                    router.replace(existingSessionTarget);
                  }
                }}
              >
                Continue
              </button>
              <button
                type="button"
                onClick={() => {
                  setError(null);
                  setLoading(true);
                  void apiRequest<{ success: boolean }>("/api/v1/auth/logout", {
                    method: "POST",
                  })
                    .finally(() => {
                      setGuardFlags({ A: false, V: false, S: false });
                      setExistingSessionTarget(null);
                      setExistingSessionMessage(null);
                      setLoading(false);
                    });
                }}
                disabled={loading}
              >
                Use different account
              </button>
            </div>
          </div>
        )}
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setError(null);
            setLoading(true);
            void apiRequest<{
              success: boolean;
              user: { email_verified: boolean; account_status: string };
            }, { email: string; password: string; remember_me: boolean }>(
              "/api/v1/auth/login",
              {
                method: "POST",
                body: { email, password, remember_me: false },
              },
            )
              .then((result) => {
                const verified = Boolean(result.user.email_verified);
                const connected = result.user.account_status === "active";
                setGuardFlags({ A: true, V: verified, S: connected });
                const fallback = connected ? "/dashboard" : "/onboarding";
                setExistingSessionTarget(
                  resolveSafeRedirect("/auth/login", returnTo, fallback),
                );
                setExistingSessionMessage(
                  connected
                    ? "Login successful. Continue to dashboard."
                    : "Login successful. Continue to onboarding.",
                );
              })
              .catch((err: unknown) => {
                if (err instanceof ApiClientError) {
                  setError(err.normalized.detail);
                } else if (err instanceof Error) {
                  setError(err.message);
                } else {
                  setError("Login failed.");
                }
              })
              .finally(() => setLoading(false));
          }}
          style={{ display: "grid", gap: 8, maxWidth: 360 }}
        >
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.currentTarget.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
        {error && (
          <p className="muted" style={{ color: "var(--error)" }}>
            {error}
          </p>
        )}
      </section>
      <section className="panel" style={{ marginTop: 12 }}>
        <h2>Developer Session Controls</h2>
        <p className="muted">
          These controls exist for Phase 7 UI verification only and do not create
          backend auth sessions. Set `NEXT_PUBLIC_DEV_AUTH_BYPASS=1` to make app
          routes trust these local guard flags.
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => {
              setGuardFlags({ A: true, V: false, S: false });
              router.replace("/auth/verify");
            }}
          >
            Sign in (unverified)
          </button>
          <button
            type="button"
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: false });
              router.replace("/onboarding");
            }}
          >
            Sign in (verified)
          </button>
          <button
            type="button"
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: true });
              router.replace("/dashboard");
            }}
          >
            Sign in (full access)
          </button>
        </div>
      </section>
    </main>
  );
}
