"use client";

import { useEffect, useMemo, useState } from "react";
import { DASHBOARD_SECTIONS } from "@/app/(app)/dashboard/sections";
import { readGuardFlags } from "@/lib/auth/session-flags";

type HealthProbe = {
  key: string;
  label: string;
  path: string;
  status: number;
  checkedAt: string | null;
};

const HEALTH_TARGETS: Array<Omit<HealthProbe, "status" | "checkedAt">> = [
  { key: "auth", label: "Auth API", path: "/api/v1/auth/me" },
  { key: "chat", label: "Chat API", path: "/api/v1/chat/sessions" },
  { key: "jobs", label: "Jobs API", path: "/api/v1/jobs?limit=1" },
  { key: "search", label: "Search API", path: "/api/v1/products/search?limit=1" },
];

export default function Dashboard() {
  const [probes, setProbes] = useState<HealthProbe[]>(
    HEALTH_TARGETS.map((target) => ({ ...target, status: 0, checkedAt: null })),
  );
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [guardFlags, setGuardFlags] = useState({ A: false, V: false, S: false });

  const readiness = useMemo(() => {
    const reachable = probes.filter((probe) => probe.status > 0).length;
    return {
      reachable,
      total: probes.length,
      isReady: guardFlags.A && guardFlags.V && guardFlags.S && reachable >= 3,
    };
  }, [guardFlags, probes]);

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
      setLastChecked(new Date().toISOString());
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
    <div className="page-wrap">
      <header className="page-header">
        <h1 className="page-title">
          <span className="material-symbols-rounded title-icon">space_dashboard</span>
          Orbital Forensics Console
        </h1>
        <p className="page-subtitle">Brutalist archive view with live operations telemetry.</p>
      </header>

      <section className="page-body">
        <article className="panel" data-section={DASHBOARD_SECTIONS[0]}>
          <h2 className="forensic-section-title forensic-zero-top">Session Status</h2>
          <p className="muted forensic-session-line">
            {readiness.isReady
              ? "ONLINE - STORE CONNECTIVITY VERIFIED - GOVERNED MODE ACTIVE"
              : "PARTIAL - VERIFY AUTH/STORE STATE BEFORE RUNNING OPERATIONS"}
          </p>
          <p className="forensic-inline-note">
            Last sync check: {lastChecked ? new Date(lastChecked).toLocaleTimeString() : "pending"}
          </p>
        </article>

        <div className="forensic-dashboard-grid" data-section={DASHBOARD_SECTIONS[1]}>
          <div className="forensic-kpi">
            <h3>Catalog Integrity</h3>
            <p>98.4%</p>
            <span className="forensic-inline-note">+1.2% / 24h</span>
          </div>
          <div className="forensic-kpi">
            <h3>Queued Jobs</h3>
            <p>12</p>
            <span className="forensic-inline-note">-2 / 24h</span>
          </div>
          <div className="forensic-kpi">
            <h3>Pending Approvals</h3>
            <p>3</p>
            <span className="forensic-inline-note">+1 / 24h</span>
          </div>
          <div className="forensic-kpi">
            <h3>Graph Context Mode</h3>
            <p>Hybrid</p>
            <span className="forensic-inline-note">{readiness.reachable}/{readiness.total} APIs reachable</span>
          </div>
        </div>

        <article className="panel">
          <h2 className="forensic-section-title forensic-zero-top">Health Matrix</h2>
          <div className="forensic-chip-row">
            {probes.map((probe) => (
              <span key={probe.key} className={`forensic-chip ${probe.status >= 200 && probe.status < 500 ? "is-active" : "is-warning"}`}>
                {probe.label}: {probe.status || "offline"}
              </span>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2 className="forensic-section-title forensic-zero-top">Quick Start Checklist</h2>
          <div className="forensic-chip-row">
            <span className={`forensic-chip ${guardFlags.A ? "is-active" : "is-warning"}`}>Auth session</span>
            <span className={`forensic-chip ${guardFlags.V ? "is-active" : "is-warning"}`}>Email verified</span>
            <span className={`forensic-chip ${guardFlags.S ? "is-active" : "is-warning"}`}>Store linked</span>
          </div>
        </article>

        <article className="panel" data-section={DASHBOARD_SECTIONS[2]}>
          <h2 className="forensic-section-title forensic-zero-top">Next Operators</h2>
          {!readiness.isReady ? (
            <p className="chat-action-warning">Primary actions are gated until auth, verification, and store linkage are ready.</p>
          ) : null}
          <div className="forensic-inline-actions">
            <a
              className="btn-primary forensic-link-btn"
              href={readiness.isReady ? "/search" : "/onboarding"}
              aria-disabled={!readiness.isReady}
            >
              {readiness.isReady ? "Run Search Sweep" : "Complete Onboarding"}
            </a>
            <a className="btn-ghost forensic-link-btn" href="/chat">
              Open Assistant
            </a>
            <a className="btn-ghost forensic-link-btn" href="/jobs">
              Inspect Jobs
            </a>
          </div>
        </article>
      </section>
    </div>
  );
}
