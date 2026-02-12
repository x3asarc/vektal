"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiRequest } from "@/lib/api/client";
import {
  createTransportLadder,
  TransportMode,
} from "@/features/jobs/observer/transport-ladder";

type JobDetail = {
  id: number;
  status: string;
  error_message?: string | null;
  job_name?: string;
};

type JobDetailResponse = {
  job: JobDetail;
};

function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
  if (typeof window !== "undefined" && window.location.hostname === "localhost") {
    return "http://localhost:5000";
  }
  return "";
}

function parseSsePayload(payload: unknown): JobDetail | null {
  if (!payload || typeof payload !== "object") return null;
  const data = payload as Record<string, unknown>;
  if ("job" in data && typeof data.job === "object" && data.job) {
    const nested = data.job as Record<string, unknown>;
    if (typeof nested.id === "number" && typeof nested.status === "string") {
      return {
        id: nested.id,
        status: nested.status,
        error_message:
          typeof nested.error_message === "string" ? nested.error_message : null,
      };
    }
  }
  if (typeof data.id === "number" && typeof data.status === "string") {
    return {
      id: data.id,
      status: data.status,
      error_message:
        typeof data.error_message === "string" ? data.error_message : null,
    };
  }
  return null;
}

export function useJobDetailObserver(jobId: number | string | null) {
  const [job, setJob] = useState<JobDetail | null>(null);
  const [mode, setMode] = useState<TransportMode>("sse");
  const [degraded, setDegraded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ladder = useMemo(() => createTransportLadder(), []);
  const pollingRef = useRef<number | null>(null);
  const inactivityRef = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) return;

    let disposed = false;
    let eventSource: EventSource | null = null;

    const cleanupPolling = () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };

    const pollJob = async () => {
      try {
        const detail = await apiRequest<JobDetailResponse>(`/api/v1/jobs/${jobId}`);
        if (disposed) return;
        setJob(detail.job);
        setError(null);
        if (ladder.getSnapshot().mode === "degraded") {
          const next = ladder.markPollingRecovery();
          setMode(next.mode);
          setDegraded(false);
        }
      } catch (err) {
        if (disposed) return;
        const next = ladder.markPollingFailure("polling_failed");
        setMode(next.mode);
        setDegraded(true);
        setError(err instanceof Error ? err.message : "Polling failed.");
      }
    };

    const startPolling = () => {
      cleanupPolling();
      void pollJob();
      pollingRef.current = window.setInterval(
        () => void pollJob(),
        ladder.getSnapshot().pollingIntervalMs,
      );
    };

    const streamUrl = `${resolveApiBase()}/api/v1/jobs/${jobId}/stream`;
    if (typeof window !== "undefined" && "EventSource" in window) {
      eventSource = new window.EventSource(streamUrl, { withCredentials: true });
      eventSource.onmessage = (event) => {
        let payload: unknown = null;
        try {
          const rawData = typeof event.data === "string" ? event.data : "";
          payload = rawData ? (JSON.parse(rawData) as unknown) : null;
        } catch {
          payload = null;
        }
        const parsed = parseSsePayload(payload);
        ladder.markSseEvent();
        setMode("sse");
        setDegraded(false);
        if (parsed) setJob(parsed);
      };
      eventSource.onerror = () => {
        const next = ladder.checkInactivity(
          Date.now() + ladder.getSnapshot().inactivityThresholdMs + 1,
        );
        setMode(next.mode);
        if (next.mode === "polling") {
          startPolling();
        }
      };
    } else {
      startPolling();
    }

    inactivityRef.current = window.setInterval(() => {
      const next = ladder.checkInactivity();
      setMode(next.mode);
      if (next.mode === "polling" && pollingRef.current === null) {
        startPolling();
      }
    }, 1000);

    return () => {
      disposed = true;
      cleanupPolling();
      if (inactivityRef.current !== null) {
        window.clearInterval(inactivityRef.current);
        inactivityRef.current = null;
      }
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [jobId, ladder]);

  return {
    job,
    mode,
    degraded,
    error,
  };
}
