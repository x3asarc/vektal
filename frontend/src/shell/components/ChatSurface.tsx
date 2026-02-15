"use client";

export type ChatMode = "overlay" | "docked";

export function getChatMode(width: number): ChatMode {
  if (width < 1024) return "overlay";
  return "docked";
}

type ChatSurfaceProps = {
  width: number;
};

export function ChatSurface({ width }: ChatSurfaceProps) {
  const mode = getChatMode(width);
  return (
    <section className="panel" data-chat-mode={mode}>
      <h2>Chat Surface</h2>
      <p className="muted">
        Chat mode: <strong>{mode}</strong> (canonical route: <a href="/chat">/chat</a>)
      </p>
      <p className="muted">
        In-product assistant supports dry-run-first approvals and bulk orchestration.
      </p>
    </section>
  );
}
