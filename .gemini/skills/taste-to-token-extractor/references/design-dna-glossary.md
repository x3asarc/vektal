# Design DNA Glossary

A technical reference for deconstructing visual inspiration into engineering tokens.

## 1. Color Systems
- **Surface**: The base color of a container (e.g., #FFF, #000, or #F9F9F9).
- **Semantic**: Colors with fixed meanings (e.g., Error/Red, Warning/Yellow).
- **Overlay**: Translucent colors used for backgrounds of modals or tooltips.
- **Contrast Ratios**: The measure of the difference in luminance between two colors (Target 4.5:1 for WCAG AA).

## 2. Geometric Logic
- **Border Radius scale**: Standard increments for rounding (e.g., 2px, 4px, 8px, 16px, 9999px).
- **Container Constraint**: The max-width of a page layout (e.g., 1280px, 1440px).

## 3. Spatial Systems
- **Whitespace Strategy**: 
  - **Compact**: 4px-8px increments.
  - **Breathable**: 12px-24px+ increments.
- **Golden Ratio (1.618)**: Often used for font size or padding scales.

## 4. Elevation & Depth
- **Box Shadow Logic**:
  - **Soft**: Large blur, low opacity (e.g., `0 10px 30px rgba(0,0,0,0.05)`).
  - **Hard**: Small blur, higher opacity (e.g., `2px 2px 0 #000`).
- **Backdrop-filter (Blur)**: The degree of background distortion (usually 10px-20px for "glass" effects).

## 5. Typography Architecture
- **Line-height (Leading)**: Ratio of text size to line height (e.g., 1.5).
- **Letter-spacing (Tracking)**: Space between characters (e.g., -0.01em for display headers).
- **Weight Distribution**: The specific range of font weights used (e.g., 400, 600, 800).

## 6. Component Patterns
- **Bento Grid**: A grid layout where cards have varying heights/widths but fit together like a box.
- **Skeleton Loaders**: Low-fidelity placeholders used during loading states.
- **Micro-interactions**: The specific logic of a hover or active state transition.
