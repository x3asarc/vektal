"use client";

import { useEffect, useState } from "react";

type DependencyStatus = {
  key: string;
  label: string;
  path: string;
  expected: string;
  status: number;
  checkedAt: string | null;
};

const TARGETS: Array<Omit<DependencyStatus, "status" | "checkedAt">> = [
  {
    key: "frontend",
    label: "Frontend",
    path: "/test",
    expected: "200",
  },
  {
    key: "auth",
    label: "Auth API",
    path: "/api/v1/auth/me",
    expected: "200 or 401",
  },
  {
    key: "chat",
    label: "Chat API",
    path: "/api/v1/chat/sessions",
    expected: "200 or 401",
  },
  {
    key: "jobs",
    label: "Jobs API",
    path: "/api/v1/jobs?limit=1",
    expected: "200 or 401",
  },
];

export function FrontendTestConsole() {
  const [statuses, setStatuses] = useState<DependencyStatus[]>(
    TARGETS.map((target) => ({ ...target, status: 0, checkedAt: null })),
  );

  useEffect(() => {
    let cancelled = false;

    async function runChecks() {
      const results = await Promise.all(
        TARGETS.map(async (target) => {
          try {
            const response = await fetch(target.path, { method: "GET", credentials: "include" });
            return { ...target, status: response.status, checkedAt: new Date().toISOString() };
          } catch {
            return { ...target, status: 0, checkedAt: new Date().toISOString() };
          }
        }),
      );
      if (cancelled) return;
      setStatuses(results);
    }

    void runChecks();
    const interval = window.setInterval(() => {
      void runChecks();
    }, 20_000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  return (
    <article className="panel">
      <p className="forensic-zero-top">Next.js frontend is reachable and rendering.</p>
      <p className="muted forensic-zero">
        Use this route for smoke tests before feature workflows.
      </p>

      <div className="forensic-table-wrap">
        <table className="forensic-table">
          <thead>
            <tr>
              <th>Dependency</th>
              <th>Endpoint</th>
              <th>Status</th>
              <th>Expected</th>
              <th>Checked</th>
            </tr>
          </thead>
          <tbody>
            {statuses.map((entry) => (
              <tr key={entry.key}>
                <td>{entry.label}</td>
                <td><code>{entry.path}</code></td>
                <td>{entry.status || "offline"}</td>
                <td>{entry.expected}</td>
                <td>{entry.checkedAt ? new Date(entry.checkedAt).toLocaleTimeString() : "pending"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
