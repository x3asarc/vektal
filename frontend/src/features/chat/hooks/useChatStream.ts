"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createTransportLadder, TransportMode } from "@/features/jobs/observer/transport-ladder";

export type ChatStreamEnvelope = {
  session_id: number;
  event: string;
  emitted_at?: string;
  payload: Record<string, unknown>;
};

type ChatStreamListener = {
  onEnvelope: (eventName: string, envelope: ChatStreamEnvelope) => void;
  onError: () => void;
};

type SessionStreamEntry = {
  source: EventSource;
  listeners: Set<ChatStreamListener>;
};

const SESSION_STREAMS = new Map<number, SessionStreamEntry>();

function resolveApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) return process.env.NEXT_PUBLIC_API_BASE_URL;
  // Default to same-origin so /api/* requests use Next.js rewrite proxy in dev.
  return "";
}

function parseEnvelope(raw: unknown): ChatStreamEnvelope | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as Record<string, unknown>;
  if (typeof data.session_id !== "number" || typeof data.event !== "string") {
    return null;
  }
  if (!data.payload || typeof data.payload !== "object") {
    return null;
  }
  return {
    session_id: data.session_id,
    event: data.event,
    emitted_at: typeof data.emitted_at === "string" ? data.emitted_at : undefined,
    payload: data.payload as Record<string, unknown>,
  };
}

function parseEventData(eventData: unknown): ChatStreamEnvelope | null {
  if (typeof eventData !== "string" || !eventData) return null;
  try {
    const parsed: unknown = JSON.parse(eventData);
    return parseEnvelope(parsed);
  } catch {
    return null;
  }
}

function notifyListeners(sessionId: number, eventName: string, envelope: ChatStreamEnvelope) {
  const entry = SESSION_STREAMS.get(sessionId);
  if (!entry) return;
  for (const listener of entry.listeners) {
    listener.onEnvelope(eventName, envelope);
  }
}

function notifyStreamError(sessionId: number) {
  const entry = SESSION_STREAMS.get(sessionId);
  if (!entry) return;
  for (const listener of entry.listeners) {
    listener.onError();
  }
}

function attachNamedEvent(
  sessionId: number,
  source: EventSource,
  eventName: string,
) {
  source.addEventListener(eventName, (event) => {
    if (!(event instanceof MessageEvent)) return;
    const envelope = parseEventData(event.data);
    if (!envelope) return;
    notifyListeners(sessionId, eventName, envelope);
  });
}

function subscribeSessionStream(
  sessionId: number,
  listener: ChatStreamListener,
): () => void {
  const existing = SESSION_STREAMS.get(sessionId);
  if (existing) {
    existing.listeners.add(listener);
    return () => {
      existing.listeners.delete(listener);
      if (existing.listeners.size === 0) {
        existing.source.close();
        SESSION_STREAMS.delete(sessionId);
      }
    };
  }

  const url = `${resolveApiBase()}/api/v1/chat/sessions/${sessionId}/stream`;
  const source = new window.EventSource(url, { withCredentials: true });
  const entry: SessionStreamEntry = {
    source,
    listeners: new Set([listener]),
  };
  SESSION_STREAMS.set(sessionId, entry);

  const namedEvents = [
    "chat_session_state",
    "chat_message",
    "chat_action",
    "chat_heartbeat",
  ] as const;
  for (const eventName of namedEvents) {
    attachNamedEvent(sessionId, source, eventName);
  }

  source.onmessage = (event) => {
    const envelope = parseEventData(event.data);
    if (!envelope) return;
    notifyListeners(sessionId, "message", envelope);
  };

  source.onerror = () => {
    notifyStreamError(sessionId);
  };

  return () => {
    const latest = SESSION_STREAMS.get(sessionId);
    if (!latest) return;
    latest.listeners.delete(listener);
    if (latest.listeners.size === 0) {
      latest.source.close();
      SESSION_STREAMS.delete(sessionId);
    }
  };
}

export function __resetChatStreamRegistryForTests() {
  for (const entry of SESSION_STREAMS.values()) {
    entry.source.close();
  }
  SESSION_STREAMS.clear();
}

type UseChatStreamOptions = {
  sessionId: number | null;
  onEnvelope: (eventName: string, envelope: ChatStreamEnvelope) => void;
  poll: () => Promise<void>;
  inactivityThresholdMs?: number;
  pollingIntervalMs?: number;
};

export function useChatStream(options: UseChatStreamOptions) {
  const { sessionId, onEnvelope, poll } = options;
  const [mode, setMode] = useState<TransportMode>("sse");
  const [degraded, setDegraded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const onEnvelopeRef = useRef(onEnvelope);
  const pollRef = useRef(poll);

  useEffect(() => {
    onEnvelopeRef.current = onEnvelope;
  }, [onEnvelope]);

  useEffect(() => {
    pollRef.current = poll;
  }, [poll]);

  const ladder = useMemo(
    () =>
      createTransportLadder({
        inactivityThresholdMs: options.inactivityThresholdMs,
        pollingIntervalMs: options.pollingIntervalMs,
      }),
    [options.inactivityThresholdMs, options.pollingIntervalMs],
  );
  const pollingRef = useRef<number | null>(null);
  const inactivityRef = useRef<number | null>(null);
  const hasStreamEventRef = useRef(false);

  useEffect(() => {
    if (!sessionId) return;

    let disposed = false;

    const cleanupPolling = () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };

    const poll = async () => {
      try {
        await pollRef.current();
        if (disposed) return;
        setError(null);
        if (ladder.getSnapshot().mode === "degraded") {
          const next = ladder.markPollingRecovery();
          setMode(next.mode);
          setDegraded(false);
        }
      } catch (reason: unknown) {
        if (disposed) return;
        const next = ladder.markPollingFailure("chat_polling_failed");
        setMode(next.mode);
        setDegraded(next.mode === "degraded");
        setError(reason instanceof Error ? reason.message : "Polling failed.");
      }
    };

    const startPolling = () => {
      cleanupPolling();
      void poll();
      pollingRef.current = window.setInterval(
        () => void poll(),
        ladder.getSnapshot().pollingIntervalMs,
      );
    };

    const unsubscribe = subscribeSessionStream(sessionId, {
      onEnvelope: (eventName, envelope) => {
        hasStreamEventRef.current = true;
        ladder.markSseEvent();
        setMode("sse");
        setDegraded(false);
        setError(null);
        onEnvelopeRef.current(eventName, envelope);
      },
      onError: () => {
        if (!hasStreamEventRef.current) {
          setMode("polling");
          startPolling();
          return;
        }
        const next = ladder.checkInactivity(Date.now() + ladder.getSnapshot().inactivityThresholdMs + 1);
        setMode(next.mode);
        if (next.mode === "polling") {
          startPolling();
        }
      },
    });

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
      unsubscribe();
    };
  }, [ladder, sessionId]);

  return {
    mode,
    degraded,
    error,
  };
}
