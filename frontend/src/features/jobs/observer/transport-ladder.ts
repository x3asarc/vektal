export type TransportMode = "sse" | "polling" | "degraded";

export type TransportLadderConfig = {
  inactivityThresholdMs?: number;
  pollingIntervalMs?: number;
};

export type TransportSnapshot = {
  mode: TransportMode;
  inactivityThresholdMs: number;
  pollingIntervalMs: number;
  lastSseEventAt: number | null;
  degradationReason: string | null;
};

const DEFAULT_INACTIVITY_THRESHOLD_MS = 4_000;
const DEFAULT_POLLING_INTERVAL_MS = 2_000;

export function createTransportLadder(config: TransportLadderConfig = {}) {
  const inactivityThresholdMs =
    config.inactivityThresholdMs ?? DEFAULT_INACTIVITY_THRESHOLD_MS;
  const pollingIntervalMs = config.pollingIntervalMs ?? DEFAULT_POLLING_INTERVAL_MS;

  let mode: TransportMode = "sse";
  let lastSseEventAt: number | null = null;
  let degradationReason: string | null = null;

  function snapshot(): TransportSnapshot {
    return {
      mode,
      inactivityThresholdMs,
      pollingIntervalMs,
      lastSseEventAt,
      degradationReason,
    };
  }

  return {
    getSnapshot: snapshot,
    markSseEvent: (at = Date.now()) => {
      lastSseEventAt = at;
      mode = "sse";
      degradationReason = null;
    },
    checkInactivity: (at = Date.now()) => {
      if (mode !== "sse" || lastSseEventAt === null) return snapshot();
      if (at - lastSseEventAt >= inactivityThresholdMs) {
        mode = "polling";
      }
      return snapshot();
    },
    markPollingFailure: (reason = "polling_failed") => {
      mode = "degraded";
      degradationReason = reason;
      return snapshot();
    },
    markPollingRecovery: () => {
      if (mode === "degraded") {
        mode = "polling";
        degradationReason = null;
      }
      return snapshot();
    },
    resumeSse: (at = Date.now()) => {
      mode = "sse";
      lastSseEventAt = at;
      degradationReason = null;
      return snapshot();
    },
  };
}
