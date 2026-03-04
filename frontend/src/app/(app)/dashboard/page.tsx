"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { DryRunReview } from "@/features/resolution/components/DryRunReview";
import styles from "./dashboard.module.css";

// ─── Terminal Box Wrapper ────────────────────────────────────────────────────

function TerminalBox({ children, className = "" }: { children: React.ReactNode, className?: string }) {
  return (
    <div className={`${styles.terminalBox} ${className}`}>
      <div className={styles.terminalBoxInner} />
      {children}
    </div>
  );
}

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
      className={styles.starterCard}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") handleClick();
      }}
    >
      <div className={styles.cardBody}>
        <span className={styles.cardTitle}>
          {title.split(" ")[0]} <span className={styles.redacted}>REDACTED</span>
        </span>
        <span className={styles.cardDesc}>{description}</span>
      </div>
      <button
        type="button"
        className={styles.toolBtn}
        style={{ marginTop: '2ch' }}
        onClick={(e) => {
          e.stopPropagation();
          handleClick();
        }}
        tabIndex={-1}
        aria-hidden
      >
        EXECUTE_PROMPT
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

function PillLink({ label, href }: PillLinkProps) {
  return (
    <Link href={href} className={styles.pill}>
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
    <form className={styles.inputWrap} onSubmit={handleSubmit}>
      <textarea
        rows={2}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter encrypted command..."
        aria-label="Send a message to the AI assistant"
      />
      <div className={styles.toolbar}>
        <div className={styles.tools}>
          <button type="button" className={styles.toolBtn} disabled>ATTACH_FILES</button>
          <button type="button" className={styles.toolBtn} disabled>DEEP_SCAN</button>
        </div>

        <div className={styles.actions}>
          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!value.trim()}
          >
            TRANSMIT
          </button>
        </div>
      </div>
    </form>
  );
}

// ─── Page ───────────────────────────────────────────────────────────────────

function DashboardPageContent() {
  const searchParams = useSearchParams();
  const batchId = Number(searchParams.get("batchId") ?? "");

  return (
    <div className={styles.dashboardPageWrap}>
      <div className={styles.crtOverlay} aria-hidden />
      
      <div className={styles.dashboardHome}>
        {/* Welcome heading */}
        <section className={`${styles.dashboardWelcome} ${styles.staggerLoad}`}>
          <h2 className={styles.dashboardTitle}>VEKTAL_OS v1.0</h2>
          <p className={styles.dashboardSubtitle}>
            ACCESS_LEVEL: <span className={styles.redacted}>TOP_SECRET</span> | STATUS: ACTIVE
          </p>
        </section>

        {/* Starter cards */}
        <section className={styles.staggerLoad} style={{ animationDelay: '0.1s' }}>
          <h3 className={styles.dashboardSectionLabel}>System_Entry_Points</h3>
          <div className={styles.starterGrid}>
            <StarterCard
              title="Smart Response Assistant"
              description="Automated AI response protocol."
              prompt="smart response: "
            />
            <StarterCard
              title="Chatbot Flow Generator"
              description="Logic gate flow generation."
              prompt="chatbot flow: "
            />
          </div>
        </section>

        {/* Quick-action pills */}
        <div
          className={`${styles.pills} ${styles.staggerLoad}`}
          role="list"
          aria-label="Quick actions"
          style={{ animationDelay: '0.2s' }}
        >
          <PillLink label="MARKET_TREND_SCAN" href="/search" icon="" />
          <PillLink label="GENERATE_REPORTS" href="/jobs" icon="" />
          <PillLink label="DATA_VISUALIZATION" href="/enrichment" icon="" />
        </div>

        {/* Chat input */}
        <div className={styles.staggerLoad} style={{ animationDelay: '0.3s' }}>
          <DashboardChatInput />
        </div>

        {/* Disclaimer */}
        <p className={styles.disclaimer}>
          [NOTICE] DO NOT ENTER RESTRICTED DATA. AI OUTPUT MAY BE UNSTABLE.
        </p>

        {/* DryRunReview preserved for ?batchId deep-links */}
        {Number.isFinite(batchId) && batchId > 0 && (
          <TerminalBox className={styles.staggerLoad}>
            <DryRunReview batchId={batchId} />
          </TerminalBox>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className={styles.dashboardPageWrap} data-testid="dashboard-loading" />}>
      <DashboardPageContent />
    </Suspense>
  );
}
