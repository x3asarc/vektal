'use client';

import React from 'react';
import './Hero.css';

export interface HeroProps {
  headline?: string;
  subheadline?: string;
  ctaText?: string;
  ctaHref?: string;
  onCtaClick?: () => void;
}

export default function Hero({
  headline = 'Orbital Forensics Platform',
  subheadline = 'Multi-vendor inventory management with deep-space precision',
  ctaText = 'Get Started',
  ctaHref = '/auth/login',
  onCtaClick
}: HeroProps) {
  const handleClick = (e: React.MouseEvent) => {
    if (onCtaClick) {
      e.preventDefault();
      onCtaClick();
    }
  };

  return (
    <section className="hero-section" data-testid="hero-section">
      {/* Atmospheric background elements */}
      <div className="hero-bg-grid" aria-hidden="true" />
      <div className="hero-bg-glow" aria-hidden="true" />

      <div className="hero-content">
        {/* Monospace headline with glitch-safe rendering */}
        <h1 className="hero-headline">
          {headline}
        </h1>

        {/* Technical subheadline */}
        <p className="hero-subheadline">
          {subheadline}
        </p>

        {/* Primary CTA with terminal-style interaction */}
        <div className="hero-cta-wrapper">
          <a
            href={ctaHref}
            className="hero-cta-btn"
            onClick={handleClick}
          >
            <span className="hero-cta-text">{ctaText}</span>
            <span className="hero-cta-icon material-symbols-rounded" aria-hidden="true">
              arrow_forward
            </span>
          </a>
        </div>

        {/* Status indicator (optional - can show system health) */}
        <div className="hero-status" aria-label="System status: operational">
          <span className="hero-status-indicator" />
          <span className="hero-status-text">All systems operational</span>
        </div>
      </div>
    </section>
  );
}
