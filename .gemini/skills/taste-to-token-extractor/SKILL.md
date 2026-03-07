---
name: taste-to-token-extractor
description: Advanced design-engineering researcher. Deconstructs visual/web inspiration into low-level design tokens (CSS variables, geometric logic, and spatial systems). Normalizes inspiration into a 'design-tokens.json' manifest for the 'frontend-design' skill. Trigger when the user mentions "vibe," "Pinterest," "mood board," or "extracting a look" from a website.
---

# Taste-to-Token Extractor

This skill transforms Gemini CLI into a senior design-engineering researcher. It deconstructs visual inspiration—from images, mood boards, or live URLs—into precise, implementable design tokens that feed directly into the **frontend-design** skill.

---

## 1. Technical Audit Framework

When analyzing images (via vision) or URLs (via `web_fetch`/`run_shell_command`), do not use vague terms. Extract the following specific **Design DNA**:

- **Color Systems**: Identify Primary, Secondary, and Tertiary HSL/Hex scales. Distinguish between **Surface** (backgrounds), **Semantic** (error/warning), and **Overlay** colors.
- **Geometric Logic**: Extract specific **Border Radius** values (e.g., "8px rounded-lg aesthetic"), **Border Widths**, and **Container Constraints**.
- **Spatial Systems**: Define the **Whitespace Strategy**—is it a 4px/8px incremental grid? Are we using **Compact** or **Breathable** padding scales?
- **Elevation & Depth**: Identify **Box Shadow** logic (e.g., "layered soft shadows with 0.05 opacity"), **Z-index layering**, and **Backdrop-filters** (Glassmorphism/Blur logic: 10px-20px range).
- **Typography Architecture**: Identify Font Pairings, **Line-height (leading)**, **Letter-spacing (tracking)**, and **Font-weight distribution** (e.g., 400 for body, 600 for headers).
- **Component Patterns**: Identify **Bento Grid** layouts, **Skeleton loaders**, and specific **Micro-interactions** (hover states, transitions).

---

## 2. Tiered Extraction Protocol

- **Vision (Local/Images)**: Batch process `./images/` or user-provided screenshots. Analyze for "vibe" consistency. Look for **Color Contrast Ratios** and **Visual Hierarchy**.
- **Functional (Live URLs)**: Scrape the DOM for Computed Styles. Extract existing **CSS Variables (--vars)** and **Tailwind class patterns**. 
- **Conceptual (Web Search)**: Use `google_web_search` or Perplexity to bridge gaps. Query: "What are the common CSS variables and spacing patterns for [Target Site/Style]?"

---

## 3. The "Handshake" Manifest

Standardize all findings into the **[design-tokens-template.json](assets/design-tokens-template.json)** schema. Once extracted, provide this JSON to the user and suggest passing it to the **frontend-design** skill for implementation.

### Implementation Workflow:
1.  **Extract**: Identify tokens using the Audit Framework.
2.  **Normalize**: Map tokens to the `design-tokens.json` structure.
3.  **Handoff**: Generate the manifest and explain the "Design DNA" to the user.

---

## 4. Discovery Tooling
- Use **`google_web_search`** for finding design systems of famous sites.
- Use **`web_fetch`** on URLs to find the `<style>` tags or linked stylesheets.
- Use **`run_shell_command`** with `curl` or `Select-String` to find `--var` patterns in local code if the "inspiration" is an existing component.
