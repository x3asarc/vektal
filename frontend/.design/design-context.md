# Design Context

**Created:** 2026-02-17
**Project:** Proxyum-style AI Chat Dashboard

<brief>
## Brief

**What:** An AI-powered product management dashboard with a conversational interface for Shopify operators
**Who:** Shopify store operators who manage product catalogs and need AI assistance for bulk operations
**Core action:** Typing a message or selecting a starter to begin an AI-assisted product task
</brief>

<references>
## Visual References

- **Proxyum 5.0 (screenshot provided)** — dark glass UI, two starter cards with "Generate" CTA, quick-action pills row, full-width chat input with toolbar row (+ | Attach | Deep Search | Generate Image | audio | send)
- **Linear** — spacing restraint, tight typography hierarchy, dark mode discipline
- **Vercel dashboard** — clean welcome state, centered content on dark bg

**Anti-references:**
- Not Material Design (too colorful, too much elevation)
- Not generic SaaS (blue-dominant, light mode first)
- Not cluttered with data on home screen
</references>

<constraints>
## Constraints

**Tech stack:** Next.js (App Router), React, pure CSS custom properties (no Tailwind), Material Symbols icons
**Platform:** Web (desktop-first, responsive)
**Color mode:** Dark mode only
**Accessibility target:** WCAG AA minimum
**Other hard constraints:** No new dependencies. Use existing CSS classes where possible, extend globals.css.
</constraints>

<what_this_is_not>
## What This Is Not

- Not a data dashboard with charts and tables on the home screen
- Not a sidebar-heavy navigation-first product
- Not light mode or dual-mode
- Not a generic CRUD admin panel
</what_this_is_not>

<vocabulary>
## Design Vocabulary for This Project

**Typography:**
- Title: clamp(2rem, 5vw, 3rem), weight 700, letter-spacing -0.02em, white
- Subtitle: 1.25rem, muted (#71717a), weight 400, flex row with emoji
- Section label: 0.7rem, uppercase, letter-spacing 0.1em, weight 600, muted
- Card title: 1rem, weight 700, #f4f4f5
- Card desc: 0.75rem, muted
- Tool btn label: 0.72rem, weight 500

**Spacing:**
- Base: 8px
- Section gaps: 48px (dashboard-home gap)
- Card internal: 22px 20px padding
- Input internal: 18px 20px padding
- Toolbar gap: 6px between tool buttons

**Color:**
- Background: #0a0a0f
- Surface: #121212
- Card: #1c1c24
- Border: rgba(255,255,255,0.08), hover: rgba(255,255,255,0.20)
- Text: #f4f4f5 | Muted: #71717a | Accent: #fff
- Generate btn: border rgba(255,255,255,0.2), ghost style

**Motion:**
- Card hover: translateY(-2px), 0.2s ease
- Input glow: opacity transition 0.3s on focus-within
- Wave emoji: infinite 2s wave keyframe
</vocabulary>
