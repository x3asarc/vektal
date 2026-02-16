"use client";

import Link from "next/link";

export type SidebarMode = "off-canvas" | "non-persistent" | "persistent";

export function getSidebarMode(width: number): SidebarMode {
  if (width < 640) return "off-canvas";
  if (width < 1024) return "non-persistent";
  return "persistent";
}

type SidebarProps = {
  width: number;
};

export function Sidebar({ width }: SidebarProps) {
  const mode = getSidebarMode(width);
  const routes = [
    "/dashboard",
    "/onboarding",
    "/jobs",
    "/search",
    "/enrichment",
    "/chat",
    "/settings",
  ];

  return (
    <aside className="panel" data-sidebar-mode={mode}>
      <h2>Navigation</h2>
      <p className="muted">
        Sidebar mode: <strong>{mode}</strong>
      </p>
      <ul>
        {routes.map((route) => (
          <li key={route}>
            <Link href={route}>{route}</Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}
