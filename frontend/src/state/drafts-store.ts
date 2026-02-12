import { create } from "zustand";

export const ttlMs = 2 * 60 * 60 * 1000;
export const draftVersion = "v1";

type DraftRecord = {
  key: string;
  value: unknown;
  createdAt: number;
  expiresAt: number;
  version: string;
};

type DraftOptions = {
  sensitive?: boolean;
  now?: number;
};

type DraftsState = {
  drafts: Record<string, DraftRecord>;
  setDraft: (key: string, value: unknown, options?: DraftOptions) => void;
  getDraft: <T>(key: string) => T | null;
  clearDraft: (key: string) => void;
  clearAllDrafts: () => void;
  markSubmitSuccess: (key: string) => void;
  markCancelled: (key: string) => void;
  hydrate: (now?: number) => void;
  resetWorkspace: () => void;
};

const STORAGE_PREFIX = "phase7:drafts";

export function getDraftStorageKey(key: string): string {
  return `${STORAGE_PREFIX}:${draftVersion}:${key}`;
}

export function isDraftExpired(record: DraftRecord, now = Date.now()): boolean {
  return record.expiresAt <= now;
}

function parseDraft(raw: string | null): DraftRecord | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DraftRecord;
    if (
      typeof parsed.key !== "string" ||
      parsed.version !== draftVersion ||
      typeof parsed.expiresAt !== "number"
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeDraftToSession(record: DraftRecord): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(getDraftStorageKey(record.key), JSON.stringify(record));
}

function clearDraftFromSession(key: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(getDraftStorageKey(key));
}

function clearAllDraftsFromSession(): void {
  if (typeof window === "undefined") return;
  const keys: string[] = [];
  for (let i = 0; i < window.sessionStorage.length; i += 1) {
    const itemKey = window.sessionStorage.key(i);
    if (itemKey?.startsWith(`${STORAGE_PREFIX}:${draftVersion}:`)) {
      keys.push(itemKey);
    }
  }
  keys.forEach((key) => window.sessionStorage.removeItem(key));
}

function readDraftsFromSession(now = Date.now()): Record<string, DraftRecord> {
  if (typeof window === "undefined") return {};
  const drafts: Record<string, DraftRecord> = {};
  const staleKeys: string[] = [];

  for (let i = 0; i < window.sessionStorage.length; i += 1) {
    const itemKey = window.sessionStorage.key(i);
    if (!itemKey?.startsWith(`${STORAGE_PREFIX}:${draftVersion}:`)) continue;
    const parsed = parseDraft(window.sessionStorage.getItem(itemKey));
    if (!parsed || isDraftExpired(parsed, now)) {
      staleKeys.push(itemKey);
      continue;
    }
    drafts[parsed.key] = parsed;
  }

  staleKeys.forEach((key) => window.sessionStorage.removeItem(key));
  return drafts;
}

let lifecycleAttached = false;

function attachLifecycleHandlers(): void {
  if (typeof window === "undefined") return;
  if (lifecycleAttached) return;
  lifecycleAttached = true;
  window.addEventListener("beforeunload", () => {
    clearAllDraftsFromSession();
  });
}

attachLifecycleHandlers();

export const useDraftsStore = create<DraftsState>((set, get) => ({
  drafts: readDraftsFromSession(),
  setDraft: (key, value, options) => {
    if (!key) return;
    if (options?.sensitive) {
      clearDraftFromSession(key);
      set((state) => {
        const next = { ...state.drafts };
        delete next[key];
        return { drafts: next };
      });
      return;
    }

    const now = options?.now ?? Date.now();
    const record: DraftRecord = {
      key,
      value,
      createdAt: now,
      expiresAt: now + ttlMs,
      version: draftVersion,
    };

    writeDraftToSession(record);
    set((state) => ({
      drafts: {
        ...state.drafts,
        [key]: record,
      },
    }));
  },
  getDraft: <T>(key: string): T | null => {
    const record = get().drafts[key];
    if (!record) return null;
    if (isDraftExpired(record)) {
      get().clearDraft(key);
      return null;
    }
    return record.value as T;
  },
  clearDraft: (key: string) => {
    clearDraftFromSession(key);
    set((state) => {
      const next = { ...state.drafts };
      delete next[key];
      return { drafts: next };
    });
  },
  clearAllDrafts: () => {
    clearAllDraftsFromSession();
    set({ drafts: {} });
  },
  markSubmitSuccess: (key: string) => {
    get().clearDraft(key);
  },
  markCancelled: (key: string) => {
    get().clearDraft(key);
  },
  hydrate: (now?: number) => {
    set({ drafts: readDraftsFromSession(now) });
  },
  resetWorkspace: () => {
    get().clearAllDrafts();
  },
}));

export function resetWorkspaceDrafts(): void {
  useDraftsStore.getState().resetWorkspace();
}
