"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { apiRequest } from "@/lib/api/client";
import {
  createTransportLadder,
  TransportMode,
} from "@/features/jobs/observer/transport-ladder";

export type JobDetail = {
  id: number;
  status: string;
  error_message?: string | null;
  job_name?: string;
  processed_items?: number;
  total_items?: number;
  successful_items?: number;
  failed_items?: number;
  percent_complete?: number;
  current_step?: string;
  current_step_label?: string;
  step_index?: number;
  step_total?: number;
  eta_seconds?: number | null;
  can_retry?: boolean;
  retry_url?: string | null;
  results_url?: string | null;
};

type JobDetailResponse = {
  job: JobDetail;
};

function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
  // Default to same-origin so /api/* requests use Next.js rewrite proxy in dev.
  return "";
}

function asNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function asNullableString(value: unknown): string | null | undefined {
  if (value === null) return null;
  if (typeof value === "string") return value;
  return undefined;
}

function asNullableNumber(value: unknown): number | null | undefined {
  if (value === null) return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  return undefined;
}

export function parseSsePayload(payload: unknown): JobDetail | null {
  if (!payload || typeof payload !== "object") return null;
  const data = payload as Record<string, unknown>;

  const raw = (
    "job" in data && typeof data.job === "object" && data.job
      ? (data.job as Record<string, unknown>)
      : data
  );

  const rawId = asNumber(raw.id) ?? asNumber(raw.job_id);
  const status = asString(raw.status);
  if (rawId === undefined || status === undefined) return null;

  return {
    id: rawId,
    status,
    job_name: asString(raw.job_name),
    error_message: asNullableString(raw.error_message) ?? null,
    processed_items: asNumber(raw.processed_items),
    total_items: asNumber(raw.total_items),
    successful_items: asNumber(raw.successful_items),
    failed_items: asNumber(raw.failed_items),
    percent_complete: asNumber(raw.percent_complete),
    current_step: asString(raw.current_step),
    current_step_label: asString(raw.current_step_label),
    step_index: asNumber(raw.step_index),
    step_total: asNumber(raw.step_total),
    eta_seconds: asNullableNumber(raw.eta_seconds),
    can_retry: typeof raw.can_retry === "boolean" ? raw.can_retry : undefined,
    retry_url: asNullableString(raw.retry_url) ?? null,
    results_url: asNullableString(raw.results_url) ?? null,
  };
}

function eventDataToPayload(eventData: unknown): unknown {
  if (typeof eventData !== "string") return null;
  if (!eventData) return null;
  try {
    return JSON.parse(eventData) as unknown;
  } catch {
    return null;
  }
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
      const eventName = `job_${jobId}`;

      const handleStreamPayload = (event: MessageEvent) => {
        const payload = eventDataToPayload(event.data);
        const parsed = parseSsePayload(payload);
        ladder.markSseEvent();
        setMode("sse");
        setDegraded(false);
        setError(null);
        if (parsed) setJob(parsed);
      };

      eventSource.addEventListener(eventName, handleStreamPayload as EventListener);
      eventSource.onmessage = handleStreamPayload;
      eventSource.onerror = () => {
        const snapshot = ladder.getSnapshot();
        if (snapshot.lastSseEventAt === null) {
          setMode("polling");
          startPolling();
          return;
        }
        const next = ladder.checkInactivity(Date.now() + snapshot.inactivityThresholdMs + 1);
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
