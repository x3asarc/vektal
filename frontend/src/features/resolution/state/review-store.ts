"use client";

import { create } from "zustand";
import {
  acquireBatchLock,
  fetchDryRun,
  getBatchLock,
  heartbeatBatchLock,
  releaseBatchLock,
} from "@/features/resolution/api/resolution-api";
import { ResolutionDryRunBatch } from "@/shared/contracts/resolution";
import { ApiClientError } from "@/lib/api/client";

type ReviewStore = {
  batch: ResolutionDryRunBatch | null;
  loading: boolean;
  lockError: string | null;
  heartbeatTimer: ReturnType<typeof setInterval> | null;
  hydrate: (batchId: number) => Promise<void>;
  acquire: (batchId: number, leaseSeconds?: number) => Promise<void>;
  heartbeat: (batchId: number, leaseSeconds?: number) => Promise<void>;
  release: (batchId: number) => Promise<void>;
  startHeartbeat: (batchId: number, leaseSeconds?: number) => void;
  stopHeartbeat: () => void;
};

function lockMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (error.normalized.status === 409) {
      const owner = error.normalized.extensions?.lock_owner;
      return owner
        ? `Batch is currently checked out by user ${String(owner)}.`
        : "Batch is currently checked out by another user.";
    }
    return error.normalized.detail;
  }
  if (error instanceof Error) return error.message;
  return "Unable to update lock state.";
}

export const useResolutionReviewStore = create<ReviewStore>((set, get) => ({
  batch: null,
  loading: false,
  lockError: null,
  heartbeatTimer: null,
  async hydrate(batchId: number) {
    set({ loading: true });
    try {
      const batch = await fetchDryRun(batchId);
      set({ batch, lockError: null });
    } catch (error) {
      set({ lockError: lockMessage(error) });
    } finally {
      set({ loading: false });
    }
  },
  async acquire(batchId: number, leaseSeconds = 300) {
    try {
      await acquireBatchLock(batchId, leaseSeconds);
      await get().hydrate(batchId);
    } catch (error) {
      set({ lockError: lockMessage(error) });
      throw error;
    }
  },
  async heartbeat(batchId: number, leaseSeconds = 300) {
    try {
      await heartbeatBatchLock(batchId, leaseSeconds);
      const lock = await getBatchLock(batchId);
      set((state) => ({
        lockError: null,
        batch:
          state.batch == null
            ? state.batch
            : {
                ...state.batch,
                lock_owner_user_id: lock.lock_owner_user_id ?? null,
                read_only: lock.lock_owner_user_id != null,
              },
      }));
    } catch (error) {
      set({ lockError: lockMessage(error) });
    }
  },
  async release(batchId: number) {
    try {
      await releaseBatchLock(batchId);
      await get().hydrate(batchId);
    } catch (error) {
      set({ lockError: lockMessage(error) });
    }
  },
  startHeartbeat(batchId: number, leaseSeconds = 300) {
    get().stopHeartbeat();
    const timer = setInterval(() => {
      void get().heartbeat(batchId, leaseSeconds);
    }, Math.max(20_000, Math.floor((leaseSeconds * 1000) / 2)));
    set({ heartbeatTimer: timer });
  },
  stopHeartbeat() {
    const timer = get().heartbeatTimer;
    if (timer) clearInterval(timer);
    set({ heartbeatTimer: null });
  },
}));
