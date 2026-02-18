"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export type SidebarMode = "off-canvas" | "non-persistent" | "persistent";

export function getSidebarMode(width: number): SidebarMode {
  if (width < 640) return "off-canvas";
  if (width < 1024) return "non-persistent";
  return "persistent";
}

type NavItem = {
  href: string;
  icon: string;
  label: string;
  filled?: boolean;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", icon: "space_dashboard", label: "Dashboard" },
  { href: "/search", icon: "search", label: "Search" },
  { href: "/chat", icon: "auto_awesome", label: "Chat", filled: true },
  { href: "/enrichment", icon: "inventory_2", label: "Enrichment" },
  { href: "/jobs", icon: "work_history", label: "Jobs" },
  { href: "/onboarding", icon: "settings_suggest", label: "Onboarding" },
];

type SidebarProps = {
  width: number;
};

export function Sidebar({ width }: SidebarProps) {
  const pathname = usePathname();
  const mode = getSidebarMode(width);

  return (
    <aside className="app-sidebar glass-panel" data-sidebar-mode={mode}>
      {/* Logo */}
      <div className="sidebar-logo">
        <button className="sidebar-icon-btn" title="Menu" type="button">
          <span className="material-symbols-rounded">asterisk</span>
        </button>
      </div>

      {/* Main nav */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV_ITEMS.map(({ href, icon, label, filled }) => {
          const isActive = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`sidebar-icon-btn${isActive ? " active" : ""}`}
              title={label}
              aria-label={label}
              aria-current={isActive ? "page" : undefined}
            >
              <span className={`material-symbols-rounded${filled && isActive ? " filled-icon" : ""}`}>
                {icon}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom actions */}
      <div className="sidebar-bottom">
        <Link
          href="/settings"
          className={`sidebar-icon-btn${pathname === "/settings" ? " active" : ""}`}
          title="Settings"
          aria-label="Settings"
        >
          <span className="material-symbols-rounded">settings</span>
        </Link>

        {/* Avatar / profile placeholder */}
        <button className="sidebar-avatar" title="Profile" type="button" aria-label="Profile">
          <span className="material-symbols-rounded" style={{ fontSize: 16 }}>person</span>
        </button>
      </div>
    </aside>
  );
}
