---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics. Make sure to use this skill whenever the user wants to build, redesign, or improve any visual UI — even if they don't say "design" explicitly.
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. The goal is real working code with exceptional visual quality — not invented from scratch when great building blocks exist, but thoughtfully composed, themed, and elevated.

---

## Pre-flight: Existing design work?

**Before doing anything else**, ask the user this question and wait for the answer:

> "Do you have existing frontend design files I should work from — things like a design system, style guide, component files, CSS/Tailwind tokens, Figma exports, or UI that already exists and needs updating? Or are we starting fresh?"

Based on the answer:

- **Existing files** → Scan and read them first (see below), then update/extend rather than replace. Preserve the established aesthetic, tokens, and patterns unless the user explicitly asks to change them.
- **Starting fresh** → Proceed to Step 0 and build from scratch.

### If existing design files are present

Run a quick scan to find what's there:
```powershell
# Find design-related files
Get-ChildItem -Recurse -Include "*.css", "*.scss", "globals.*", "tailwind.config.*", "theme.*", "tokens.*", "design-system.*", "*.figma.json" | Select-Object -First 30 -ExpandProperty FullName

# Check for existing component directories
Get-ChildItem -Directory -Path "src/components/", "components/", "ui/" -ErrorAction SilentlyContinue
```

Then read the key files — at minimum:
- Global CSS / `globals.css` → extract the color palette, typography scale, spacing, and any CSS variables
- `tailwind.config.*` → extract custom tokens, theme extensions, font config
- A sample existing component → understand the code patterns and naming conventions in use

Summarize what you found before proceeding:
> "I found your existing design system. Here's what's established: [palette, fonts, tokens, patterns]. I'll work within this and only change what you've asked me to update."

Then proceed to Step 1 with this context locked in — don't override existing decisions unless the user asks.

---

## Step 0: Detect the environment

Before anything else, understand what you're working with.

**If a codebase exists**, run these commands to detect the stack:
```powershell
if (Test-Path "package.json") { Get-Content "package.json" | Select-String '"react"|"next"|"vue"|"svelte"|"tailwind"|"vite"' }
Get-ChildItem -Path "src/", "app/", "pages/" -ErrorAction SilentlyContinue
```

Then identify:
- Framework: React, Next.js, Vue, Svelte, or plain HTML
- Styling: Tailwind, CSS modules, styled-components, plain CSS
- Component libraries already installed (shadcn/ui, Radix, etc.)
- Existing design tokens (check `tailwind.config.*`, `globals.css`, CSS variables)

**If no codebase exists** (greenfield or artifact), ask the user before proceeding:

> "Before I start, what stack should I use? Here are my recommendations based on your use case:"
> - **Single-file / artifact / prototype**: Plain HTML + CSS + JS (no dependencies, runs anywhere)
> - **Modern web app**: Next.js + Tailwind CSS + shadcn/ui (production-ready, great DX)
> - **Component library / design system**: React + Tailwind + 21st.dev components
> - **Something else?** Tell me and I'll adapt.

Wait for confirmation before writing any code.

---

## Step 1: Design thinking

Once you know the stack, understand the context and commit to a BOLD aesthetic direction:

- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme and commit — brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian. Use these as starting points, not boxes to fit into.
- **Constraints**: Performance, accessibility, existing brand/tokens.
- **Differentiation**: What's the one thing someone will remember about this UI?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work — the key is intentionality, not intensity.

---

## Step 2: Component strategy

### In a React / Next.js / Tailwind project

**Check 21st.dev first.** Before hand-rolling any component, check whether a high-quality version exists at 21st.dev. It ships polished, animated, production-ready React + Tailwind components that consistently outperform model-generated primitives.

Use 21st.dev components for:
- Hero sections, feature grids, pricing tables
- Navigation bars, sidebars, footers
- Cards, testimonials, stats blocks
- Buttons, inputs, modals with animations
- Dashboard layouts and data displays

**How to use 21st.dev components:**
```bash
# Install via npx (recommended)
npx shadcn@latest add "https://21st.dev/r/[component-name]"

# Or browse https://21st.dev and copy the component code directly
```

When referencing a 21st.dev component in your plan, name it explicitly: *"I'll use the 21st.dev Bento Grid for the features section."* Then install or inline it and theme it to the project's design tokens.

**The agent's role shifts when using 21st.dev:**
- From: inventing raw UI primitives
- To: selecting the right components, composing layouts, applying the aesthetic vision, and writing only the parts that don't already exist

### In a plain HTML / artifact context

No external dependencies available. Build everything inline — but apply the same aesthetic rigor. The absence of a component library is not an excuse for generic output.

---

## Step 3: Frontend aesthetics

Apply these regardless of stack:

**Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts (Arial, Inter, Roboto, system fonts). Pair a distinctive display font with a refined body font. In HTML, load from Google Fonts or use @font-face. In React/Next.js, use `next/font` or import in globals.

**Color & Theme**: Commit to a cohesive palette. Use CSS variables or Tailwind config for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Define the palette before writing components.

**Motion**: High-impact over scattered. One well-orchestrated page load with staggered reveals creates more delight than a dozen micro-interactions. In plain HTML/CSS, use `animation-delay` and `@keyframes`. In React, use the Motion library when available. Always respect `prefers-reduced-motion`.

**Spatial composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density — never the default centered-column layout.

**Backgrounds & visual details**: Create atmosphere. Gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, grain overlays. Match the effect to the aesthetic direction.

**NEVER use**: Inter/Roboto/Arial as body fonts, purple gradients on white, predictable card-heavy layouts, or any pattern that looks like it came from a generic AI UI tutorial.

No design should look like another. Vary light/dark themes, font choices, and aesthetics deliberately. Never converge on safe defaults like Space Grotesk or blue-on-white.

---

## Step 4: Accessibility & production quality

Every output must be:
- **Keyboard navigable**: visible focus states on all interactive elements
- **Contrast-compliant**: WCAG AA minimum (4.5:1 for body text)
- **Semantic HTML**: proper heading hierarchy, landmark roles, button vs. link distinction
- **Responsive**: mobile-first, or at minimum tested at 375px, 768px, and 1280px
- **Performance-conscious**: no unnecessary re-renders, lazy-load images, avoid layout shift

---

## Step 5: Implementation

Match complexity to the vision:
- Maximalist designs need elaborate code — extensive animations, layered effects, rich detail
- Minimalist/refined designs need restraint — precision in spacing, typography, and subtle micro-details

Write production-grade, well-organized code. If using 21st.dev components, show the install command and integration clearly. If building from scratch, structure CSS with variables at the top and components logically grouped.

**Deliver:**
1. The complete implementation (all files, or single file if artifact)
2. A brief note on the aesthetic direction chosen and why
3. Any install commands needed (21st.dev components, fonts, etc.)
4. What to do next to extend or customize it

---

## What not to do

- Don't start coding before knowing the stack
- Don't reinvent components that 21st.dev already does better
- Don't use generic aesthetics — Space Grotesk + purple gradient is not a design direction
- Don't scatter micro-interactions everywhere — fewer, higher-impact moments
- Don't ignore existing design tokens if the project already has them

---

Remember: You are capable of extraordinary creative work. Don't hold back — show what can truly be created when thinking outside the box and committing fully to a distinctive vision. The goal is a UI that feels *deliberately designed*, not AI-generated.
