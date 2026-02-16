"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { readGuardFlags, setGuardFlags } from "@/lib/auth/session-flags";
import { resolveSafeRedirect } from "@/lib/auth/guards";

export default function VerifyEmailPage() {
  const router = useRouter();
  const [returnTo, setReturnTo] = useState<string | null>(null);

  const state = readGuardFlags();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setReturnTo(params.get("returnTo"));
  }, []);

  useEffect(() => {
    if (!state.A) {
      router.replace("/auth/login");
    }
  }, [router, state.A]);

  return (
    <main>
      <h1>verify-email</h1>
      <p className="muted">
        Verification is required before accessing protected routes.
      </p>
      <section className="panel">
        <h2>Mock Verification Controls</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: state.S });
              router.replace(resolveSafeRedirect("/auth/verify", returnTo, "/dashboard"));
            }}
          >
            Mark email verified
          </button>
          <button
            type="button"
            onClick={() => {
              setGuardFlags({ A: true, V: true, S: true });
              router.replace("/dashboard");
            }}
          >
            Mark verified + store connected
          </button>
        </div>
      </section>
    </main>
  );
}
