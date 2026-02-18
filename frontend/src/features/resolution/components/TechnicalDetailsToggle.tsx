"use client";

import { ReactNode, useState } from "react";

type TechnicalDetailsToggleProps = {
  summary?: string;
  children: ReactNode;
};

export function TechnicalDetailsToggle({
  summary = "Technical details",
  children,
}: TechnicalDetailsToggleProps) {
  const [open, setOpen] = useState(false);

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        style={{ justifySelf: "start" }}
      >
        {open ? "Hide" : "Show"} {summary}
      </button>
      {open && <div className="panel">{children}</div>}
    </div>
  );
}
