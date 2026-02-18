import { GuardState } from "@/shared/contracts";

const AUTH_PREFIX = "/auth/";

const STORE_REQUIRED_PREFIXES = ["/dashboard", "/jobs", "/chat", "/search", "/resolution"];

export function requiresStore(route: string): boolean {
  return STORE_REQUIRED_PREFIXES.some(
    (prefix) => route === prefix || route.startsWith(`${prefix}/`),
  );
}

export function sanitizeReturnTo(
  value: string | null | undefined,
  fallback = "/dashboard",
): string {
  if (!value) return fallback;
  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//")) return fallback;
  if (value.includes("://")) return fallback;
  return value;
}

export function causesRedirectLoop(
  currentRoute: string,
  redirectTarget: string,
): boolean {
  return currentRoute === redirectTarget;
}

export function getRedirectForRoute(route: string, state: GuardState): string | null {
  if (route.startsWith(AUTH_PREFIX)) return null;

  if (!state.A) {
    if (route === "/auth/login") return null;
    return `/auth/login?returnTo=${encodeURIComponent(route)}`;
  }

  if (!state.V) {
    if (route === "/auth/verify") return null;
    return `/auth/verify?returnTo=${encodeURIComponent(route)}`;
  }

  if (requiresStore(route) && !state.S && route !== "/onboarding") {
    return `/onboarding?returnTo=${encodeURIComponent(route)}`;
  }

  return null;
}

export function resolveSafeRedirect(
  currentRoute: string,
  candidate: string | null | undefined,
  fallback = "/dashboard",
): string {
  const safe = sanitizeReturnTo(candidate, fallback);
  if (causesRedirectLoop(currentRoute, safe)) {
    return fallback;
  }
  return safe;
}
