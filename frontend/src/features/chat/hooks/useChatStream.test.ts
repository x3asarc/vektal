import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetChatStreamRegistryForTests,
  useChatStream,
} from "@/features/chat/hooks/useChatStream";

type Listener = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  onmessage: Listener | null = null;
  onerror: ((event: Event) => void) | null = null;
  listeners = new Map<string, Listener>();

  constructor(_url: string, _init?: EventSourceInit) {
    MockEventSource.instances.push(this);
  }

  addEventListener(name: string, listener: EventListener) {
    this.listeners.set(name, listener as Listener);
  }

  close() {
    return;
  }

  emitNamed(name: string, data: unknown) {
    const listener = this.listeners.get(name);
    if (listener) {
      listener(new MessageEvent(name, { data: JSON.stringify(data) }));
    }
  }

  emitError() {
    this.onerror?.(new Event("error"));
  }
}

describe("useChatStream", () => {
  beforeEach(() => {
    __resetChatStreamRegistryForTests();
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  it("keeps one EventSource per session for multiple hook subscribers", () => {
    const onEnvelopeA = vi.fn();
    const onEnvelopeB = vi.fn();
    const poll = vi.fn().mockResolvedValue(undefined);

    const first = renderHook(() =>
      useChatStream({
        sessionId: 9,
        onEnvelope: onEnvelopeA,
        poll,
      }),
    );
    const second = renderHook(() =>
      useChatStream({
        sessionId: 9,
        onEnvelope: onEnvelopeB,
        poll,
      }),
    );

    expect(MockEventSource.instances).toHaveLength(1);

    act(() => {
      MockEventSource.instances[0].emitNamed("chat_message", {
        session_id: 9,
        event: "assistant_update",
        payload: { message_id: 1, content: "ok" },
      });
    });

    expect(onEnvelopeA).toHaveBeenCalled();
    expect(onEnvelopeB).toHaveBeenCalled();

    first.unmount();
    second.unmount();
  });

  it("falls back to polling when stream errors before first event", async () => {
    const poll = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() =>
      useChatStream({
        sessionId: 10,
        onEnvelope: vi.fn(),
        poll,
      }),
    );

    act(() => {
      MockEventSource.instances[0].emitError();
    });

    await waitFor(() => {
      expect(poll).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(result.current.mode).toBe("polling");
    });
  });
});
