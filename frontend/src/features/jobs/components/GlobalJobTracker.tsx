"use client";

import { useEffect, useRef, useState } from "react";
import { isTerminalLifecycle, mapBackendStatusToLifecycle } from "@/features/jobs/observer/job-observer";
import { useJobRehydrate } from "@/features/jobs/hooks/useJobRehydrate";
import {
  JobTerminalEvent,
  JobTerminalNotifications,
} from "@/features/jobs/components/JobTerminalNotifications";

function toTerminalStatus(status: string): JobTerminalEvent["status"] | null {
  const lifecycle = mapBackendStatusToLifecycle(status);
  if (!isTerminalLifecycle(lifecycle)) return null;
  if (lifecycle === "success") return "success";
  if (lifecycle === "cancelled") return "cancelled";
  return "error";
}

export function GlobalJobTracker() {
  const { jobs, activeJobs, error, isRehydrating, rehydrate } = useJobRehydrate();
  const [terminalEvents, setTerminalEvents] = useState<JobTerminalEvent[]>([]);
  const seenEvents = useRef<Set<string>>(new Set());

  useEffect(() => {
    const created: JobTerminalEvent[] = [];
    for (const job of jobs) {
      const terminal = toTerminalStatus(job.status);
      if (!terminal) continue;
      const key = `${job.id}:${job.status}`;
      if (seenEvents.current.has(key)) continue;
      seenEvents.current.add(key);
      created.push({
        key,
        jobId: job.id,
        status: terminal,
        message:
          terminal === "success"
            ? `Job ${job.id} completed`
            : terminal === "cancelled"
              ? `Job ${job.id} cancelled`
              : `Job ${job.id} failed`,
        occurredAt: Date.now(),
      });
    }
    if (created.length > 0) {
      setTerminalEvents((existing) => [...created, ...existing].slice(0, 50));
    }
  }, [jobs]);

  return (
    <section className="panel" data-job-tracker>
      <h2>Global Job Tracker</h2>
      <p className="muted">
        Tracks active jobs and rehydrate cycles from backend source-of-truth.
      </p>
      <p className="muted">
        Active jobs: <strong>{activeJobs.length}</strong>
      </p>
      {isRehydrating && <p className="muted">Rehydrating jobs...</p>}
      {error && <p className="muted">Transport degraded: {error}</p>}
      <button type="button" onClick={() => void rehydrate()}>
        rehydrate now
      </button>
      <JobTerminalNotifications events={terminalEvents} />
    </section>
  );
}
