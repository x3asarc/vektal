"use client";

import { useEffect, useMemo, useState } from "react";
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
            const response = await fetch(target.path, { method: "GET", credentials: "include" });
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
    <div className="flex flex-col min-h-screen bg-white">
      {/* System Health Ribbon (Forensic Sub-bar) */}
      <div className="bg-gray-900 px-6 py-1.5 flex items-center justify-between overflow-x-auto">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className={`w-1.5 h-1.5 rounded-full ${guardFlags.S ? 'bg-green-400' : 'bg-red-400'}`}></div>
            <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">Store Link</span>
          </div>
          <div className="flex gap-4">
            {probes.map((probe) => (
              <div key={probe.key} className="flex items-center gap-1.5">
                <div className={`w-1 h-1 rounded-full ${probe.status >= 200 && probe.status < 500 ? 'bg-green-500' : 'bg-gray-600'}`}></div>
                <span className="text-[9px] font-mono text-gray-500 uppercase">{probe.label}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="text-[9px] font-mono text-gray-600 uppercase tracking-widest hidden sm:block">
          Environment: Production · Region: EU-Central-1
        </div>
      </div>

      <CommandCenter />
    </div>
  );
}
