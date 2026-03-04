---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality using a Graph-First approach. Use this skill when the user asks to build web components, pages, artifacts, or applications. Generates creative, polished code that avoids generic AI aesthetics.
---

This skill transforms the agent into a senior UI/UX engineer equipped with a **Graph-First Discovery** toolkit. It focuses on distinctive, production-grade interfaces that leverage existing codebase relationships and design tokens.

---

## Pre-flight: Graph-Aware Discovery

**Before coding, always map the current frontend cluster.** This avoids redundant components and ensures stylistic consistency.

1.  **Search the Knowledge Graph**: Use the feature name or component path to find related files and planning requirements.
2.  **Run Discovery Script**:
    ```powershell
    # Replace <FeatureName> with the current task (e.g., "Approvals")
    powershell ./.gemini/skills/frontend-design-skill/scripts/get-frontend-context.ps1 -FeatureName "<FeatureName>"
    ```
3.  **Identify existing tokens**: If the script found `globals.css`, use those variables instead of hex codes.

**Ask the user**:
> "I've mapped the current frontend context using the Knowledge Graph. I found [X components] and [Y design tokens]. Should I extend these existing patterns, or are we introducing a new aesthetic direction for this feature?"

---

## Step 0: Design Strategy & Aesthetic Reference

Commit to a BOLD direction early. Consult the **[Visual Language Reference](references/visual-language.md)** for inspiration on:
- **Brutalist Refined**: Raw, sharp, high-contrast.
- **Organic Soft UI**: Pastel, rounded, layered.
- **Retro-Futuristic**: Neon, glowing, dark-mode.

---

## Step 1: Component Strategy (Themed Boilerplate)

**Don't reinvent the wheel.**
- **Asset Usage**: Use the foundational styles in **[Base Styles](assets/base-styles.css)** (e.g., `.glass-card`, `.interactive-button`) as a starting point.
- **21st.dev**: For complex interactive elements (Hero sections, Bento grids), search 21st.dev first:
  ```bash
  npx shadcn@latest add "https://21st.dev/r/[component-name]"
  ```

---

## Step 2: Implementation Guidelines

- **Typography**: Match display and body font pairings from the reference.
- **Spatial**: Apply asymmetry and generous negative space.
- **Motion**: Use the `.stagger-load` class for page entries.
- **Accessibility**: Ensure WCAG AA compliance and keyboard navigability.

**Deliver:**
1.  **The Implementation**: Clean, production-grade React/TypeScript or Vanilla code.
2.  **The Rationale**: Explain the aesthetic choice and how it aligns with the Graph context.
3.  **Next Steps**: How to customize or refine the design further.

---

Remember: The goal is a UI that feels *deliberately designed* and deeply integrated with the project's existing Knowledge Graph, not generic AI output.
