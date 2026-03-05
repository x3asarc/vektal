"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { readGuardFlags, setGuardFlags } from "@/lib/auth/session-flags";
import { resolveSafeRedirect } from "@/lib/auth/guards";

export default function VerifyEmailPage() {
  const router = useRouter();
  const [returnTo, setReturnTo] = useState<string | null>(null);
  const [state, setState] = useState(() => readGuardFlags());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setReturnTo(params.get("returnTo"));
    setState(readGuardFlags());
  }, []);

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">
            <span className="material-symbols-rounded auth-icon">mark_email_read</span>
          </div>
          <span className="auth-logo-text">Identity Gate</span>
        </div>

        <div>
          <h1 className="auth-heading">Verify Email</h1>
          <p className="auth-subheading">Verification is required before protected operations are enabled.</p>
        </div>

        {!state.A ? (
          <div className="auth-notice">
            <p className="auth-message">
              No active session found. Sign in first, then return to verify your email.
            </p>
            <div className="auth-notice-actions">
              <button className="btn-primary" type="button" onClick={() => router.replace("/auth/login?force=1")}>
                Go to sign in
              </button>
            </div>
          </div>
        ) : (
          <div className="auth-notice">
            <p className="auth-message">
              Confirm your mailbox, then continue with verified credentials.
            </p>
          </div>
        )}

        <div className="auth-dev-buttons">
          <button
            className="btn-primary"
            type="button"
            disabled={!state.A}
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: state.S });
              router.replace(resolveSafeRedirect("/auth/verify", returnTo, "/dashboard"));
            }}
          >
            Mark Email Verified
          </button>
          <button
            className="btn-ghost"
            type="button"
            disabled={!state.A}
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: true });
              router.replace("/dashboard");
            }}
          >
            Verified + Store Linked
          </button>
        </div>
      </div>
    </div>
  );
}
