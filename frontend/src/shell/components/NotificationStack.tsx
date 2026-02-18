"use client";

type NotificationLevel = "global-blocking" | "page-banner" | "inline" | "toast";

type NotificationItem = {
  level: NotificationLevel;
  message: string;
};

const PRIORITY: Record<NotificationLevel, number> = {
  "global-blocking": 1,
  "page-banner": 2,
  inline: 3,
  toast: 4,
};

export function sortNotifications(items: NotificationItem[]): NotificationItem[] {
  return [...items].sort((a, b) => PRIORITY[a.level] - PRIORITY[b.level]);
}

export function NotificationStack() {
  // Scaffold placeholder — no active notifications.
  // When real notifications exist, render a fixed overlay toast stack here.
  return null;
}
