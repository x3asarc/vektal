---
name: taste-to-token-extractor
description: Advanced design-engineering researcher. Deconstruct visual/web inspiration into low-level design tokens and normalize into a `design-tokens-v2.json` manifest for the `frontend-design` skill. Use when the user mentions vibe, Pinterest, mood boards, extracting a look, or asks for tokenized design systems. Make sure to use this skill before `frontend-design` whenever visual inspiration must be converted into tokens first.
---

# Taste-to-Token Extractor

This skill deconstructs visual inspiration from images, mood boards, or live URLs into precise, implementation-ready design tokens for the **frontend-design** skill.

---

## 1. Technical Audit Framework

When analyzing images (vision) or URLs (`web_fetch`/`run_shell_command`), avoid vague terms. Extract the following Design DNA with concrete values.

- **Color Systems**: Build primitive ramps (brand + neutral), role tokens (background, surface, text, border, brand), semantic tokens (success/warning/danger/info), and state tokens (hover/active/focus/disabled).
- **Typography Architecture**: Extract font families, weight distribution, **size scale**, line-height scale, letter-spacing scale, and role mappings (`h1`, `h2`, `body`, `caption`).
- **Spatial Systems**: Define base spacing unit and spacing scale, plus container width, section spacing, and grid gap patterns.
- **Geometric Logic**: Extract radius scale, component radius mapping (button/card/input/modal/chip), and border-width scale.
- **Motion System**: Extract duration scale, easing curves, state transition presets, keyframe intent (for major entrances), and reduced-motion fallback behavior.
- **Elevation and Depth**: Extract shadow scale, blur/backdrop settings, and opacity semantics.
- **Component Patterns**: Identify recurring structural patterns (bento, split hero, sidebar, cards) and state expectations per component.

---

## 2. Tiered Extraction Protocol

- **Vision (Local/Images)**: Batch process `./images/` or user screenshots. Check vibe consistency, hierarchy, and contrast.
- **Functional (Live URLs)**: Scrape computed styles, existing CSS variables (`--vars`), and utility class patterns.
- **Conceptual (Research)**: Fill gaps with research only when needed; do not invent novel tokens when evidence is available.

---

## 3. Required `design-tokens-v2` Contract

Always normalize findings to **[design-tokens-template.json](assets/design-tokens-template.json)** and output it as `design-tokens-v2.json`.

The following token groups are required unless truly non-inferable:

- `tokens.colors`
- `tokens.typography` (must include `size_scale`)
- `tokens.spacing`
- `tokens.radius`
- `tokens.motion`

Use explicit `N/A` only for values that cannot be inferred from evidence.

### Handoff workflow
1. **Extract**: Pull concrete evidence from visuals and/or code.
2. **Normalize**: Map all inferred values to the v2 schema.
3. **Validate**: Check the five required token groups are present.
4. **Handoff**: Return JSON and explain major DNA choices in plain language.

### Mandatory pipeline handoff
After returning `design-tokens-v2.json`, immediately continue with the `frontend-design` skill if the user is building UI from those tokens.
Include this handoff payload in your response:

```json
{
  "next_skill": "frontend-design",
  "design_tokens_path": "path/to/design-tokens-v2.json",
  "handoff_reason": "Token extraction complete; implementation should now consume v2 tokens."
}
```

---

## 4. Output quality bar

- Prefer token references (`{colors.primitives.brand.500}`) over duplicated values.
- Include state coverage where relevant: `default`, `hover`, `active`, `focus-visible`, `disabled`.
- Include accessibility intent through `contrast_targets`.
- Ensure motion tokens include a reduced-motion strategy.
- Keep naming deterministic and reusable; avoid one-off token names.

---

## 5. Discovery Tooling

- Use `web_fetch` (or equivalent) to inspect `<style>` tags and linked stylesheets from URLs.
- Use `run_shell_command` with `curl`/`Select-String` for local code token extraction (`--var`, spacing, radius, transition patterns).
- Use search tooling only when first-party evidence is incomplete.
