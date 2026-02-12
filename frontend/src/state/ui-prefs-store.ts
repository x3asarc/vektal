import { create } from "zustand";

export type DeviceBucket = "sm" | "md" | "lg";

type UiPrefsSnapshot = {
  sidebarCollapsed: boolean;
  updatedAt: number;
};

type UiPrefsState = UiPrefsSnapshot & {
  device: DeviceBucket;
  hydrate: (width?: number) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  resetWorkspace: () => void;
};

const STORAGE_VERSION = "v1";
const STORAGE_NAMESPACE = "phase7:ui-prefs";

export function resolveDeviceBucket(width: number): DeviceBucket {
  if (width < 640) return "sm";
  if (width < 1024) return "md";
  return "lg";
}

export function getUiPrefsStorageKey(device: DeviceBucket): string {
  return `${STORAGE_NAMESPACE}:${STORAGE_VERSION}:${device}`;
}

function getCurrentDevice(width?: number): DeviceBucket {
  if (typeof window === "undefined") return "lg";
  return resolveDeviceBucket(width ?? window.innerWidth);
}

function readSnapshot(device: DeviceBucket): UiPrefsSnapshot {
  if (typeof window === "undefined") {
    return { sidebarCollapsed: false, updatedAt: Date.now() };
  }

  try {
    const raw = window.localStorage.getItem(getUiPrefsStorageKey(device));
    if (!raw) return { sidebarCollapsed: false, updatedAt: Date.now() };
    const parsed = JSON.parse(raw) as Partial<UiPrefsSnapshot>;
    return {
      sidebarCollapsed: Boolean(parsed.sidebarCollapsed),
      updatedAt:
        typeof parsed.updatedAt === "number" ? parsed.updatedAt : Date.now(),
    };
  } catch {
    return { sidebarCollapsed: false, updatedAt: Date.now() };
  }
}

function persistSnapshot(device: DeviceBucket, snapshot: UiPrefsSnapshot): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(getUiPrefsStorageKey(device), JSON.stringify(snapshot));
}

export const useUiPrefsStore = create<UiPrefsState>((set, get) => {
  const device = getCurrentDevice();
  const snapshot = readSnapshot(device);

  return {
    device,
    sidebarCollapsed: snapshot.sidebarCollapsed,
    updatedAt: snapshot.updatedAt,
    hydrate: (width?: number) => {
      const nextDevice = getCurrentDevice(width);
      const nextSnapshot = readSnapshot(nextDevice);
      set({
        device: nextDevice,
        sidebarCollapsed: nextSnapshot.sidebarCollapsed,
        updatedAt: nextSnapshot.updatedAt,
      });
    },
    setSidebarCollapsed: (collapsed: boolean) => {
      const current = get();
      const nextSnapshot: UiPrefsSnapshot = {
        sidebarCollapsed: collapsed,
        updatedAt: Date.now(),
      };
      persistSnapshot(current.device, nextSnapshot);
      set(nextSnapshot);
    },
    resetWorkspace: () => {
      const current = get();
      if (typeof window !== "undefined") {
        window.localStorage.removeItem(getUiPrefsStorageKey(current.device));
      }
      set({
        sidebarCollapsed: false,
        updatedAt: Date.now(),
      });
    },
  };
});

export function resetUiPrefsForCurrentDevice(width?: number): void {
  useUiPrefsStore.getState().hydrate(width);
  useUiPrefsStore.getState().resetWorkspace();
}
