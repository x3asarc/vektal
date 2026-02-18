import { create } from "zustand";

type PendingStore = {
  pendingCount: number;
  begin: () => void;
  end: () => void;
  reset: () => void;
};

export const usePendingStore = create<PendingStore>((set) => ({
  pendingCount: 0,
  begin: () => set((state) => ({ pendingCount: state.pendingCount + 1 })),
  end: () =>
    set((state) => ({ pendingCount: Math.max(0, state.pendingCount - 1) })),
  reset: () => set({ pendingCount: 0 }),
}));
