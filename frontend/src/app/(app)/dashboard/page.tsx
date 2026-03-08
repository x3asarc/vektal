"use client";

import { useEffect, useState } from "react";
import { readGuardFlags } from "@/lib/auth/session-flags";
import { CommandCenter } from "@/features/dashboard/components/CommandCenter";

type HealthProbe = {
  key: string;
  label: string;
  path: string;
  status: number;
  checkedAt: string | null;
};

const HEALTH_TARGETS: Array<Omit<HealthProbe, "status" | "checkedAt">> = [
  { key: "auth", label: "Auth", path: "/api/v1/auth/me" },
  { key: "chat", label: "Chat", path: "/api/v1/chat/sessions" },
  { key: "jobs", label: "Jobs", path: "/api/v1/jobs?limit=1" },
  { key: "search", label: "Search", path: "/api/v1/products/search?limit=1" },
];

export default function Dashboard() {
  const [probes, setProbes] = useState<HealthProbe[]>(
    HEALTH_TARGETS.map((target) => ({ ...target, status: 0, checkedAt: null })),
  );
  const [guardFlags, setGuardFlags] = useState({ A: false, V: false, S: false });

  useEffect(() => {
    setGuardFlags(readGuardFlags());
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function runHealthChecks() {
      const results = await Promise.all(
        HEALTH_TARGETS.map(async (target) => {
          try {
            const response = await fetch(target.path, { 
              method: "GET", 
              credentials: "include",
              headers: { 'Accept': 'application/json' }
            });
            return {
              ...target,
              status: response.status,
              checkedAt: new Date().toISOString(),
            };
          } catch {
            return {
              ...target,
              status: 0,
              checkedAt: new Date().toISOString(),
            };
          }
        }),
      );
      if (cancelled) return;
      setProbes(results);
    }

    void runHealthChecks();
    const interval = window.setInterval(() => {
      void runHealthChecks();
    }, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-[var(--bg)]">
      <main className="flex-1 overflow-y-auto">
        <CommandCenter />
      </main>
    </div>
  );
}
