# Visual Language & Aesthetic Reference

This reference provides concrete patterns and inspiration for high-end frontend design that avoids "AI slop."

## 1. Aesthetic Archetypes

### Brutalist Refined
- **Typography**: Large, bold, monospaced or high-contrast sans-serif.
- **Color**: High contrast (True Black #000, True White #FFF) with one sharp accent (e.g., #00FF00).
- **Spatial**: Sharp borders (2px+), no border-radius, overlapping elements.
- **Example**: A developer dashboard with thick lines and raw layout.

### Organic / Soft UI
- **Typography**: Rounded sans-serif (e.g., Inter, Quicksand) with generous line-height.
- **Color**: Pastel backgrounds, subtle gradients, low-contrast text (#333 on #F9F9F9).
- **Spatial**: Large border-radius (16px+), soft shadows, blurred background overlays.
- **Example**: An onboarding flow for a wellness app.

### Retro-Futuristic (Synthwave)
- **Typography**: Glowing display fonts, digital-clock styles for numbers.
- **Color**: Dark mode (#0A0A0A) with neon pinks, purples, and teals.
- **Spatial**: Glowing borders, scanline overlays, depth through transparency.
- **Example**: A real-time data visualization for scraping jobs.

## 2. Spatial Composition Rules

- **Asymmetry**: Avoid perfectly centered layouts. Use a 60/40 split or staggered grids.
- **Negative Space**: Be generous. If in doubt, add 2rem more padding.
- **Depth**: Use z-index and subtle offsets to make elements feel layered, not flat.

## 3. Motion & Micro-interactions

- **Staggered Reveals**: Instead of `opacity: 1`, use a 20px Y-translation with a 50ms stagger per item.
- **Hover Feedback**: Beyond color changes. Try a slight scale (1.02) or a subtle 3D tilt.
- **Transitions**: Always use `cubic-bezier(0.4, 0, 0.2, 1)` for a "premium" feel.

## 4. Typography Pairing Examples

- **Display**: Playfair Display / **Body**: Inter
- **Display**: Space Grotesk / **Body**: JetBrains Mono
- **Display**: Syne / **Body**: Archivo

**Never use**: Times New Roman, Comic Sans, or default system fonts for anything prominent.
