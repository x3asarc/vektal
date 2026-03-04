"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { DryRunReview } from "@/features/resolution/components/DryRunReview";

// ─── Starter cards ──────────────────────────────────────────────────────────

type StarterCardProps = {
  title: string;
  description: string;
  prompt: string;
};

function StarterCard({ title, description, prompt }: StarterCardProps) {
  const router = useRouter();

  function handleClick() {
    router.push("/chat?q=" + encodeURIComponent(prompt));
  }

  return (
    <div
      className="starter-card"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
    >
      <div className="starter-card-body">
        <span className="starter-card-title">{title}</span>
        <span className="starter-card-desc">{description}</span>
      </div>
      <button
        type="button"
        className="starter-card-btn"
        onClick={(e) => {
          e.stopPropagation();
          handleClick();
        }}
        tabIndex={-1}
        aria-hidden
      >
        <span
          className="material-symbols-rounded filled-icon"
          style={{ fontSize: 13 }}
        >
          auto_awesome
        </span>
        Generate
      </button>
    </div>
  );
}

// ─── Quick-action pill ──────────────────────────────────────────────────────

type PillLinkProps = {
  icon: string;
  label: string;
  href: string;
};

function PillLink({ icon, label, href }: PillLinkProps) {
  return (
    <Link href={href} className="dashboard-pill">
      <span className="material-symbols-rounded" style={{ fontSize: 16 }}>
        {icon}
      </span>
      {label}
    </Link>
  );
}

// ─── Dashboard chat input ───────────────────────────────────────────────────

function DashboardChatInput() {
  const [value, setValue] = useState("");
  const router = useRouter();

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    router.push("/chat?q=" + encodeURIComponent(trimmed));
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const trimmed = value.trim();
      if (!trimmed) return;
      router.push("/chat?q=" + encodeURIComponent(trimmed));
    }
  }

  return (
    <form className="dashboard-input-wrap" onSubmit={handleSubmit}>
      <div className="dashboard-input-glow" aria-hidden />
      <div className="dashboard-input-glass">
        <textarea
          rows={2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything…"
          aria-label="Send a message to the AI assistant"
        />
        <div className="dashboard-input-toolbar">
          <div className="dashboard-input-tools">
            {/* + add button (circular ring) */}
            <button
              type="button"
              className="dashboard-tool-btn dashboard-tool-btn--add"
              title="More options"
              disabled
              aria-label="More options"
            >
              <span
                className="material-symbols-rounded"
                style={{ fontSize: 18 }}
              >
                add
              </span>
            </button>

            <button
              type="button"
              className="dashboard-tool-btn"
              title="Attach file"
              disabled
            >
              <span
                className="material-symbols-rounded"
                style={{ fontSize: 14 }}
              >
                attachment
              </span>
              Attach
            </button>

            <button
              type="button"
              className="dashboard-tool-btn"
              title="Deep search"
              disabled
            >
              <span
                className="material-symbols-rounded"
                style={{ fontSize: 14 }}
              >
                travel_explore
              </span>
              Deep Search
            </button>

            <button
              type="button"
              className="dashboard-tool-btn"
              title="Generate image"
              disabled
            >
              <span
                className="material-symbols-rounded"
                style={{ fontSize: 14 }}
              >
                image
              </span>
              Generate Image
            </button>
          </div>

          <div className="dashboard-input-actions">
            {/* Audio / voice waveform button */}
            <button
              type="button"
              className="dashboard-tool-btn dashboard-tool-btn--icon"
              title="Voice input"
              disabled
              aria-label="Voice input"
            >
              <span
                className="material-symbols-rounded"
                style={{ fontSize: 18 }}
              >
                graphic_eq
              </span>
            </button>

            <button
              type="submit"
              className="dashboard-submit-btn"
              disabled={!value.trim()}
              title="Send"
              aria-label="Send message"
            >
              <span
                className="material-symbols-rounded filled-icon"
                style={{ fontSize: 18 }}
              >
                arrow_upward
              </span>
            </button>
          </div>
        </div>
      </div>
    </form>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

export const DASHBOARD_SECTIONS = [
  "global-health-summary",
  "in-progress",
  "needs-attention",
  "fast-recovery-actions",
] as const;

function DashboardPageContent() {
  const searchParams = useSearchParams();
  const batchId = Number(searchParams.get("batchId") ?? "");

  return (
    <div className="dashboard-page-wrap">
      <div className="dashboard-home">
        {/* Ambient glow */}
        <div className="dashboard-glow" aria-hidden />

        {/* Welcome heading */}
        <section className="dashboard-welcome">
          <h2 className="dashboard-title">Welcome to Vektal!</h2>
          <p className="dashboard-subtitle">
            <span>Friendly Owner</span>
            <span className="wave-emoji" aria-hidden>
              👋
            </span>
          </p>
        </section>

        {/* Starter cards */}
        <section className="dashboard-starters" aria-label="Starters">
          <h3 className="dashboard-section-label">Starters</h3>
          <div className="starter-grid">
            <StarterCard
              title="Smart Response Assistant"
              description="Create instant, accurate AI replies."
              prompt="smart response: "
            />
            <StarterCard
              title="Chatbot Flow Generator"
              description="Design smart reply flows in seconds."
              prompt="chatbot flow: "
            />
          </div>
        </section>

        {/* Quick-action pills */}
        <div
          className="dashboard-pills"
          role="list"
          aria-label="Quick actions"
        >
          <PillLink icon="trending_up" label="Market Trend Research" href="/search" />
          <PillLink icon="description" label="Generate Reports" href="/jobs" />
          <PillLink icon="bar_chart" label="Create Data Visual" href="/enrichment" />
        </div>

        {/* Chat input */}
        <DashboardChatInput />

        {/* Disclaimer */}
        <p className="dashboard-disclaimer">
          <span className="material-symbols-rounded" aria-hidden>
            info
          </span>
          Don&apos;t enter sensitive info. AI may generate inaccurate or
          incomplete responses.
        </p>

        {/* DryRunReview preserved for ?batchId deep-links */}
        {Number.isFinite(batchId) && batchId > 0 && (
          <DryRunReview batchId={batchId} />
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="dashboard-page-wrap" data-testid="dashboard-loading" />}>
      <DashboardPageContent />
    </Suspense>
  );
}
