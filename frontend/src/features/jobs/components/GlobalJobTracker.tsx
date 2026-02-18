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
  const { jobs, activeJobs: _activeJobs, error: _error, isRehydrating: _isRehydrating, rehydrate: _rehydrate } = useJobRehydrate();
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
        detail:
          terminal === "success"
            ? `${job.successful_items ?? 0} succeeded, ${job.failed_items ?? 0} failed.`
            : job.error_message ?? undefined,
        jobUrl: `/jobs/${job.id}`,
        resultsUrl: job.results_url ?? undefined,
        occurredAt: Date.now(),
      });
    }
    if (created.length > 0) {
      setTerminalEvents((existing) => [...created, ...existing].slice(0, 50));
    }
  }, [jobs]);

  // Only render when there are terminal notifications to surface
  if (terminalEvents.length === 0) return null;

  return <JobTerminalNotifications events={terminalEvents} />;
}
