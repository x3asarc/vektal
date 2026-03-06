---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with strong design quality and implementation rigor. Use when building or redesigning web UI, when `design-tokens-v2.json` is provided, or when `deployment-validator` returns FAIL and design corrections are required. Make sure to use this skill immediately after token extraction and in remediation loops after failed validation.
---

This skill turns design intent into production frontend code. It should consume structured tokens first, then build themed UI using the project stack.

---

## Pipeline position

- Previous skill: `taste-to-token-extractor`
- Current skill: `frontend-design`
- Next skill: `frontend-deploy-debugger`

If `design-tokens-v2.json` exists, treat it as primary design input.

---

## Closed-loop contract

This skill participates in an iterative loop:

`frontend-design -> frontend-deploy-debugger -> deployment-validator`

If validator result is `FAIL`, this skill must be called again with validator evidence and remediation advice, then produce targeted design/code fixes.

---

## Step 0: Input contract and token-first workflow

Before any UI implementation, look for:

- `design-tokens-v2.json`
- `design-tokens-v2.*.json`
- any user-provided token file path
- latest `frontend-deploy-debugger` report (if available)
- latest `deployment-validator` report (if available)

If token JSON exists, parse it first and lock these foundations:

- `tokens.colors`
- `tokens.typography`
- `tokens.spacing`
- `tokens.radius`
- `tokens.motion`

If validator/debugger reports exist, treat them as mandatory context and prioritize fixes that address failing gates without regressing previously passing checks.

If token JSON is missing, ask whether to continue without it or run `taste-to-token-extractor` first.

---

## Step 1: Detect environment

Detect:

- framework (`next`, `react`, `vue`, `svelte`, static html)
- styling system (Tailwind, CSS Modules, plain CSS, styled-components)
- existing component libraries
- existing tokens in `globals.css`, `tailwind.config.*`, or theme files

Preserve existing design-system conventions unless user asks for a reset.

---

## Step 2: Map tokens to implementation primitives

When `design-tokens-v2.json` is present, always map it into runtime styling primitives.

### Required mapping

1. `tokens.colors` -> CSS custom properties and theme roles
2. `tokens.typography` -> font families, size scale, role styles
3. `tokens.spacing` -> spacing scale and layout spacing variables
4. `tokens.radius` -> radius and border-width variables
5. `tokens.motion` -> duration/easing vars and reduced-motion-safe transitions

### Tailwind projects

- extend `theme.colors` from token roles/primitives
- extend `fontFamily`, `fontSize`, `spacing`, `borderRadius`
- map motion tokens via CSS variables and utility classes

### Non-Tailwind projects

- create/update global token stylesheet with CSS variables
- apply token roles in component styles instead of hardcoded values

Do not invent conflicting values when valid tokens are provided.

---

## Step 3: Build UI with component strategy

### Component source evaluation

Before building from scratch, evaluate available sources in this order:

1. **Existing project components** - Reuse when quality is high and appropriate
2. **Magic (21st.dev) via MCP** - Query for production-grade patterns (optional)
3. **Custom build** - Full control, use when Magic doesn't fit or adds complexity

Magic is a **resource to query, not a requirement**. Always prefer simple over clever.

---

### When to query Magic (optional)

Query Magic MCP when building:
- Complex interactive sections (hero, pricing, testimonials, feature grids)
- Standard UI patterns (nav, footer, dashboard shells, auth forms)
- High-polish components where custom build would be time-intensive

**Skip Magic when:**
- Building simple components (buttons, cards, basic layouts)
- Requirements are highly specific to your domain
- You're already familiar with the pattern
- Magic MCP is unavailable or slow

---

### Magic query workflow

If querying Magic, follow this lightweight discovery process:

#### 3.1 Identify functional requirements

Define what you need **functionally** (not visually):
- Component type: "hero section", "pricing table", "navigation", etc.
- Required functionality: "must have CTA button and background image"
- Constraints: "mobile responsive", "supports dark mode", "keyboard accessible"

**Important:** Query Magic based on **function and structure**, not design tokens.
Tokens define the theme; Magic provides the structural patterns.

#### 3.2 Query Magic MCP

Use available Magic MCP tools to search the component library:
- Search by component type/category
- Filter by required features
- Get component metadata (props, variants, complexity, dependencies)

**Quick timeout:** If Magic doesn't respond within a few seconds, move on to custom build.

#### 3.3 Evaluate results

For each Magic component returned, assess:
- **Functional fit:** Does it meet requirements?
- **Theming effort:** Can it be themed to project tokens easily?
- **Complexity:** Is it simpler than custom build?
- **Dependencies:** Does it bring unwanted dependencies?

Present top 2-3 options with pros/cons in your response:

```markdown
## Magic Component Options

### Option 1: [component-name]
- Pros: [...]
- Cons: [...]
- Theming effort: low|medium|high
- Recommendation: [use|skip]

### Option 2: [component-name]
- Pros: [...]
- Cons: [...]
- Theming effort: low|medium|high
- Recommendation: [use|skip]

### Custom build
- Pros: Full control, exactly fits requirements
- Cons: More implementation time
- Recommendation: [preferred if Magic doesn't fit]
```

This makes Magic options **visible and discoverable** without forcing a choice.

#### 3.4 Implement choice

**If using Magic component:**
1. Fetch component code via Magic MCP
2. Install required dependencies
3. Theme component to project tokens (critical - see Step 3.5)
4. Test responsiveness and accessibility
5. Document which Magic component was used

**If building custom:**
1. Use project tokens from the start
2. Follow existing component patterns
3. Ensure accessibility and responsiveness
4. Keep implementation lean

---

### Step 3.5: Theme Magic components to project tokens

When using Magic components, **always theme them** to project tokens. Never leave vendor defaults.

#### Theming workflow

1. **Identify themeable properties:**
   - Colors (backgrounds, text, borders, brand elements)
   - Typography (font families, sizes, weights, line heights)
   - Spacing (padding, margins, gaps)
   - Radius (border-radius values)
   - Motion (transitions, animations)

2. **Map tokens to component:**
   - Replace hardcoded colors with `var(--color-*)` or Tailwind token classes
   - Replace hardcoded spacing with token scale values
   - Replace hardcoded typography with role styles (h1, body, etc.)
   - Ensure motion respects `prefers-reduced-motion`

3. **Verify consistency:**
   - Component should look native to the project
   - No visual discontinuity with existing UI
   - Design tokens fully applied

#### Example theming

**Before (Magic default):**
```tsx
<div className="bg-blue-600 text-white p-8 rounded-lg">
  <h2 className="text-4xl font-bold">Hello</h2>
</div>
```

**After (themed to tokens):**
```tsx
<div className="bg-brand-primary text-surface-on-brand p-section rounded-card">
  <h2 className="text-heading-xl font-heading">Hello</h2>
</div>
```

---

### Step 3.6: Mix Magic + custom freely

You're not locked into one approach. Common patterns:

- **Magic for structure, custom for domain logic:** Use Magic hero layout, but replace generic content with domain-specific components
- **Magic for one section, custom for others:** Use Magic pricing table, build custom dashboard from scratch
- **Start with Magic, refactor later:** Use Magic to ship fast, replace with custom if needs evolve

The goal is **compositional freedom**, not dependency on any single source.

---

## Step 4: Visual quality and accessibility

Must satisfy:

- keyboard navigability and visible focus states
- WCAG AA contrast targets
- semantic HTML structure
- responsive behavior for mobile/tablet/desktop
- `prefers-reduced-motion` support for animated UI

Avoid generic design defaults. Keep the visual direction intentional and consistent with token DNA.

---

## Step 5: Delivery format

Return:

1. **Implemented files and key edits**
2. **Token mapping summary** (`design-tokens-v2` -> CSS/Tailwind targets)
3. **Install commands** (if any)
4. **Magic component usage** (if any):
   ```markdown
   ### Magic Components Used
   - [component-name] from 21st.dev
     - Location: [file path]
     - Theming applied: [summary]
     - Customizations: [any modifications made]
   ```
5. **Component source breakdown**:
   - Magic: [list of Magic components used]
   - Custom: [list of custom components built]
   - Mixed: [components that started with Magic but were heavily customized]
6. **Unresolved assumptions or `N/A` token decisions**

This breakdown helps you understand what came from Magic vs custom build, making it easier to explore Magic later or refactor as needed.

---

## Step 6: Mandatory pipeline handoff

After implementation is complete, immediately continue with `frontend-deploy-debugger` for a quick regression check and runtime verification.

Include this handoff payload:

```json
{
  "next_skill": "frontend-deploy-debugger",
  "handoff_reason": "Frontend implementation/remediation complete; run quick regression deployment checks.",
  "local_target_url": "http://localhost:<port-or-N/A>",
  "public_target_url": "https://<domain-or-N/A>",
  "run_commands": ["<dev-or-start-command>"],
  "changed_files": ["path/one", "path/two"],
  "iteration": "<n>"
}
```
