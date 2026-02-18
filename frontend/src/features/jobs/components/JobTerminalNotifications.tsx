"use client";

export type TerminalStatus = "success" | "error" | "cancelled";

export type JobTerminalEvent = {
  key: string;
  jobId: number;
  status: TerminalStatus;
  message: string;
  detail?: string;
  jobUrl?: string;
  resultsUrl?: string;
  occurredAt: number;
};

type TerminalPolicyConfig = {
  successTtlMs?: number;
  cancelledTtlMs?: number;
  burstThreshold?: number;
  burstWindowMs?: number;
};

const DEFAULT_CONFIG: Required<TerminalPolicyConfig> = {
  successTtlMs: 12_000,
  cancelledTtlMs: 5_000,
  burstThreshold: 3,
  burstWindowMs: 10_000,
};

export function selectVisibleTerminalEvents(
  events: JobTerminalEvent[],
  now = Date.now(),
  config: TerminalPolicyConfig = {},
) {
  const {
    successTtlMs,
    cancelledTtlMs,
    burstThreshold,
    burstWindowMs,
  } = { ...DEFAULT_CONFIG, ...config };

  const ordered = [...events].sort((a, b) => b.occurredAt - a.occurredAt);

  const recentBurst = ordered.filter((event) => now - event.occurredAt <= burstWindowMs);
  const collapsed = recentBurst.length >= burstThreshold;

  const visible = ordered.filter((event) => {
    if (event.status === "error") return true;
    if (event.status === "success") return now - event.occurredAt <= successTtlMs;
    return now - event.occurredAt <= cancelledTtlMs;
  });

  return {
    visible,
    collapsed,
    collapsedCount: collapsed ? recentBurst.length : 0,
  };
}

type JobTerminalNotificationsProps = {
  events: JobTerminalEvent[];
  now?: number;
};

export function JobTerminalNotifications({
  events,
  now,
}: JobTerminalNotificationsProps) {
  const evaluated = selectVisibleTerminalEvents(events, now);

  if (evaluated.visible.length === 0) return null;

  return (
    <section className="panel" data-terminal-notifications>
      <h2>Terminal Notifications</h2>
      {evaluated.collapsed && (
        <p className="muted">
          {evaluated.collapsedCount}
          {" "}
          terminal updates in the last window; showing a summary.
        </p>
      )}
      <ul>
        {evaluated.visible.map((event) => (
          <li key={event.key}>
            <strong>{event.status}</strong>
            : {event.message}
            {event.detail && (
              <>
                {" "}
                <span className="muted">{event.detail}</span>
              </>
            )}
            {(event.jobUrl || event.resultsUrl) && (
              <span>
                {" "}
                {event.jobUrl && <a href={event.jobUrl}>Open job</a>}
                {event.jobUrl && event.resultsUrl && " | "}
                {event.resultsUrl && <a href={event.resultsUrl}>View results</a>}
              </span>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
