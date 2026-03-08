# Design DNA Glossary

A technical reference for deconstructing visual inspiration into engineering tokens.

## 1. Color Systems
- **Primitive ramp**: Raw hue scales by step (`50..900`) such as `brand` and `neutral`.
- **Role token**: Semantic usage mapping (background, surface, text, border, brand) that references primitive ramps.
- **State token**: Visual overlays for interaction states (`hover`, `active`, `focus`, `disabled`).
- **Semantic token**: Status colors with fixed meaning (`success`, `warning`, `danger`, `info`).
- **Contrast targets**: Accessibility intent for text and UI contrast (WCAG AA baseline: 4.5:1 body text).

## 2. Geometric Logic
- **Border Radius scale**: Standard increments for rounding (example: `xs`, `sm`, `md`, `lg`, `xl`, `pill`).
- **Container Constraint**: The max-width of a page layout (e.g., 1280px, 1440px).
- **Component radius mapping**: Intentional radius choice per component (button, card, input, modal, chip).
- **Border width scale**: Standard stroke weights (`hairline`, `default`, `strong`).

## 3. Spatial Systems
- **Base unit**: The root spacing atom (commonly `4px` or `8px`).
- **Spacing scale**: Named or numeric steps mapped to rem/px values.
- **Whitespace Strategy**:
  - **Compact**: 4px-8px increments.
  - **Breathable**: 12px-24px+ increments.
- **Layout spacing tokens**: Container max width, section paddings, and grid gaps.
- **Golden Ratio (1.618)**: Often used for font size or padding scales.

## 4. Elevation & Depth
- **Box Shadow Logic**:
  - **Soft**: Large blur, low opacity (e.g., `0 10px 30px rgba(0,0,0,0.05)`).
  - **Hard**: Small blur, higher opacity (e.g., `2px 2px 0 #000`).
- **Backdrop-filter (Blur)**: The degree of background distortion (usually 10px-20px for "glass" effects).
- **Opacity semantics**: Consistent transparency levels for muted text, overlays, and disabled UI.

## 5. Typography Architecture
- **Size scale**: Ordered typography steps (`2xs` to `5xl`) used across UI.
- **Role map**: Mapping from content role (`h1`, `h2`, `body`, `caption`) to family, size, weight, line-height, and tracking.
- **Line-height (Leading)**: Ratio of text size to line height (e.g., 1.5).
- **Letter-spacing (Tracking)**: Space between characters (e.g., -0.01em for display headers).
- **Weight Distribution**: The specific range of font weights used (e.g., 400, 600, 800).

## 6. Motion System
- **Duration scale**: Tokenized transition timings (`fast`, `base`, `slow`).
- **Easing curves**: Cubic-bezier curves mapped by intent (`standard`, `entrance`, `exit`).
- **Transition presets**: Reusable transition strings for hover/focus/modal states.
- **Reduced motion strategy**: Rule for preserving usability when animation should be minimized.

## 7. Component Patterns
- **Bento Grid**: A grid layout where cards have varying heights/widths but fit together like a box.
- **Skeleton Loaders**: Low-fidelity placeholders used during loading states.
- **Micro-interactions**: The specific logic of hover, active, and focus-visible state transitions.
