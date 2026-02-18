"use client";

export type ChatMode = "overlay" | "docked";

export function getChatMode(width: number): ChatMode {
  if (width < 1024) return "overlay";
  return "docked";
}

type ChatSurfaceProps = {
  width: number;
};

export function ChatSurface({ width: _width }: ChatSurfaceProps) {
  // The canonical assistant surface is /chat.
  // This shell slot is reserved for a future floating overlay mode.
  return null;
}
