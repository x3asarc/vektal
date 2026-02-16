"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  getRedirectForRoute,
  resolveSafeRedirect,
} from "@/lib/auth/guards";
import { apiRequest } from "@/lib/api/client";
import { readGuardFlags, setGuardFlags } from "@/lib/auth/session-flags";
import { GuardState } from "@/shared/contracts";
import { GlobalJobTracker } from "@/features";
import { Sidebar } from "@/shell/components/Sidebar";
import { ChatSurface } from "@/shell/components/ChatSurface";
import { GlobalPendingIndicator } from "@/shell/components/GlobalPendingIndicator";
import { NotificationStack } from "@/shell/components/NotificationStack";

type AppShellProps = {
  children: ReactNode;
};

const DEV_AUTH_BYPASS =
  process.env.NEXT_PUBLIC_DEV_AUTH_BYPASS === "1" ||
  process.env.NODE_ENV !== "production";

type AuthMeResponse = {
  user: {
    email_verified: boolean;
    account_status: string;
  };
};

type OAuthStatusResponse = {
  connected: boolean;
};

async function fetchGuardStateFromBackend(): Promise<GuardState> {
  try {
    const me = await apiRequest<AuthMeResponse>("/api/v1/auth/me");
    let storeConnected = me.user.account_status === "active";

    if (!storeConnected) {
      try {
        const oauthStatus = await apiRequest<OAuthStatusResponse>("/api/v1/oauth/status");
        storeConnected = Boolean(oauthStatus.connected);
      } catch {
        // Keep account status fallback when oauth status is unavailable.
      }
    }

    return {
      A: true,
      V: Boolean(me.user.email_verified),
      S: storeConnected,
    };
  } catch {
    return {
      A: false,
      V: false,
      S: false,
    };
  }
}

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [width, setWidth] = useState(1280);
  const [guardHydrated, setGuardHydrated] = useState(false);
  const [guardState, setGuardState] = useState<GuardState>(() => readGuardFlags());

  useEffect(() => {
    const updateWidth = () => setWidth(window.innerWidth);
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function refreshGuardState() {
      if (DEV_AUTH_BYPASS) {
        const localState = readGuardFlags();
        if (cancelled) return;
        setGuardFlags(localState);
        setGuardState(localState);
        setGuardHydrated(true);
        return;
      }

      const backendState = await fetchGuardStateFromBackend();
      if (cancelled) return;
      setGuardFlags(backendState);
      setGuardState(backendState);
      setGuardHydrated(true);
    }

    void refreshGuardState();

    return () => {
      cancelled = true;
    };
  }, [pathname]);

  const redirectTo = useMemo(
    () => (guardHydrated ? getRedirectForRoute(pathname, guardState) : null),
    [guardHydrated, pathname, guardState],
  );

  useEffect(() => {
    if (!redirectTo) return;
    const target = resolveSafeRedirect(pathname, redirectTo, "/dashboard");
    if (target !== pathname) {
      router.replace(target);
    }
  }, [pathname, redirectTo, router]);

  return (
    <main>
      <GlobalPendingIndicator />
      <div style={{ display: "grid", gap: 16, gridTemplateColumns: "1fr" }}>
        <Sidebar width={width} />
        <NotificationStack />
        <GlobalJobTracker />
        {children}
        <ChatSurface width={width} />
      </div>
    </main>
  );
}
