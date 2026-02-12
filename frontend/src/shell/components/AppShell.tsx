"use client";

import { ReactNode, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  getRedirectForRoute,
  resolveSafeRedirect,
} from "@/lib/auth/guards";
import { apiRequest } from "@/lib/api/client";
import { setGuardFlags } from "@/lib/auth/session-flags";
import { GuardState } from "@/shared/contracts";
import { GlobalJobTracker } from "@/features";
import { Sidebar } from "@/shell/components/Sidebar";
import { ChatSurface } from "@/shell/components/ChatSurface";
import { GlobalPendingIndicator } from "@/shell/components/GlobalPendingIndicator";
import { NotificationStack } from "@/shell/components/NotificationStack";

type AppShellProps = {
  children: ReactNode;
};

function readFlag(name: string, fallback: boolean): boolean {
  if (typeof document === "undefined") return fallback;
  const match = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`));
  if (!match) return fallback;
  return match.split("=")[1] === "1";
}

function readGuardStateFromCookies(): GuardState {
  // Defaults start unauthenticated until backend session is confirmed.
  return {
    A: readFlag("phase7_A", false),
    V: readFlag("phase7_V", false),
    S: readFlag("phase7_S", false),
  };
}

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
  const [guardState, setGuardState] = useState<GuardState>(() =>
    readGuardStateFromCookies(),
  );

  useEffect(() => {
    const updateWidth = () => setWidth(window.innerWidth);
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function refreshGuardState() {
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
