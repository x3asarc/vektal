"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

type ForensicShellProps = {
  children: ReactNode;
};

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "space_dashboard" },
  { href: "/search", label: "Search", icon: "search" },
  { href: "/chat", label: "Chat", icon: "auto_awesome" },
  { href: "/enrichment", label: "Enrichment", icon: "inventory_2" },
  { href: "/jobs", label: "Jobs", icon: "work_history" },
  { href: "/onboarding", label: "Onboarding", icon: "settings_suggest" },
  { href: "/settings", label: "Settings", icon: "settings" },
  { href: "/approvals", label: "Approvals", icon: "approval_delegation" },
];

export function ForensicShell({ children }: ForensicShellProps) {
  const pathname = usePathname();

  return (
    <div className="forensic-shell">
      <aside className="forensic-nav">
        <div className="forensic-brand">
          <span className="material-symbols-rounded">asterisk</span>
          <span>VEKTAL OS</span>
        </div>
        <nav className="forensic-nav-list" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`forensic-nav-link${pathname?.startsWith(item.href) ? " is-active" : ""}`}
            >
              <span className="material-symbols-rounded">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>
      </aside>
      <section className="forensic-content">
        <aside className="forensic-about" aria-label="About Vektal">
          <p className="forensic-about-title">About Vektal</p>
          <p className="forensic-about-copy">
            Vektal OS is the governed console for catalog forensics, enrichment, and approvals.
          </p>
        </aside>
        {children}
      </section>
    </div>
  );
}
