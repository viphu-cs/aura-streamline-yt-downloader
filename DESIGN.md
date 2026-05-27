---
name: Aura Streamline
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#414750'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#717782'
  outline-variant: '#c1c7d2'
  surface-tint: '#0061a5'
  primary: '#00497e'
  on-primary: '#ffffff'
  primary-container: '#0061a5'
  on-primary-container: '#c0dbff'
  inverse-primary: '#9fcaff'
  secondary: '#006e2f'
  on-secondary: '#ffffff'
  secondary-container: '#6bff8f'
  on-secondary-container: '#007432'
  tertiary: '#37485e'
  on-tertiary: '#ffffff'
  tertiary-container: '#4f6077'
  on-tertiary-container: '#c8daf5'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d2e4ff'
  primary-fixed-dim: '#9fcaff'
  on-primary-fixed: '#001d36'
  on-primary-fixed-variant: '#00497e'
  secondary-fixed: '#6bff8f'
  secondary-fixed-dim: '#4ae176'
  on-secondary-fixed: '#002109'
  on-secondary-fixed-variant: '#005321'
  tertiary-fixed: '#d2e4ff'
  tertiary-fixed-dim: '#b6c8e2'
  on-tertiary-fixed: '#091c30'
  on-tertiary-fixed-variant: '#37485e'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
  liquid-blue-start: '#60A5FA'
  liquid-blue-end: '#0061A5'
  glass-fill: rgba(255, 255, 255, 0.4)
  glass-border: rgba(255, 255, 255, 0.3)
  surface-bg: '#F8F9FF'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  body-md:
    fontFamily: Be Vietnam Pro
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Be Vietnam Pro
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-padding: 24px
  gutter: 16px
  card-gap: 20px
  sidebar-width: 288px
---

## Brand & Style

Aura Streamline is a **Frutiger Aero-inspired Glassmorphism** system designed for high-performance utility applications. It evokes a sense of "digital optimism" through the use of organic shapes, glossy textures, and liquid-like gradients.

The brand personality is **energetic, transparent, and ultra-fast**. It moves away from flat minimalism, embracing depth and dimensionality to make complex tasks feel tactile and satisfying. The target audience values speed and high-fidelity feedback, necessitating an interface that feels "alive" through subtle blurs, caustic light effects, and responsive scale-based interactions.

## Colors

The palette is anchored by **Vibrant Azure** and **Atmospheric Whites**. 

- **Primary**: A deep, saturated blue used for core actions and active states. It often appears in a vertical "liquid" gradient.
- **Secondary**: An energetic green reserved for success states, ready-indicators, and premium upgrades.
- **Surface Strategy**: Instead of solid grays, the system uses "Frutiger-bg"—a radial gradient from `#D2E4FF` to `#F8F9FF`. 
- **Glass Accents**: Pure white is rarely used as a solid; it is almost always applied with 40-80% opacity and a 20px-60px backdrop blur to maintain the "glass" aesthetic.

## Typography

The system utilizes a dual-font strategy to balance character with legibility:

- **Plus Jakarta Sans** is the primary display face. It is used for all headings and branding to provide a friendly, rounded, and contemporary feel. Tight tracking is applied to larger sizes to maintain a "high-end" look.
- **Be Vietnam Pro** serves as the functional workhorse. It handles body copy, labels, and input text, offering exceptional clarity at smaller sizes and within glass-textured containers.

Typography should always favor high contrast against surfaces. On glass panels, use `on-surface-variant` with reduced opacity (70-80%) for secondary info to maintain the hierarchical depth.

## Layout & Spacing

Aura Streamline uses a **Hybrid Fixed-Sidebar/Fluid-Canvas** layout.

1. **Sidebar**: A fixed 288px (72 units) vertical navigation area on the left. It uses high-intensity backdrop blurs to separate it from the content canvas.
2. **Main Canvas**: A fluid area that grows to fill the viewport. Content is centered within a maximum width or structured using a consistent 20px card gap.
3. **Spacing Rhythm**: All margins and paddings are derived from an 8px base unit. Component interiors typically use 16px (2 units) or 24px (3 units) for breathing room. 

Large-scale containers like the "Download Canvas" use 32px padding to emphasize their status as the primary focal point.

## Elevation & Depth

Depth in this system is created through **Subtractive Transparency** rather than simple shadows.

- **Level 1 (Floor)**: The animated radial background with blurred "blobs" for atmospheric light.
- **Level 2 (Glass Panels)**: `rgba(255, 255, 255, 0.4)` with a `20px` blur. These panels feature a dual border: a 1px solid white/30 outer border and a subtle interior white glow (`inset 0 1px 1px white/80`).
- **Level 3 (Recessed Elements)**: Inputs and secondary containers use "Recessed-Depth"—inner shadows (`inset 2px 2px 5px rgba(0,0,0,0.05)`) that make the element look carved into the glass.
- **Level 4 (Floating/Active)**: High-priority buttons use `0 8px 32px 0 rgba(31, 38, 135, 0.1)` to appear lifted. Active interactive elements (like focused inputs) use an `active-glow` effect: `0 0 15px rgba(0, 97, 165, 0.3)`.

## Shapes

The shape language is **Hyper-Rounded**, avoiding sharp corners entirely to maintain the "liquid" aesthetic.

- **Base Radius**: 0.5rem (8px).
- **Large Containers (Cards)**: 1.5rem (24px) to 2rem (32px).
- **Interactive Elements**: Buttons and active navigation links use **Full Pill** (9999px) rounding to encourage clicking and provide a friendly silhouette.
- **Icon Enclosures**: Small icons are often encased in "Squircle" or circular glass containers to signify interactability.

## Components

### Buttons
- **Liquid Button**: Primary actions. Uses a vertical gradient (`#60A5FA` to `#0061A5`), a glossy white inner-top stroke, and a 1.05x hover scale transform.
- **Ghost Button**: Circular icons with glass backgrounds and 1.1x hover scale.

### Input Fields
- **Recessed Input**: Large (64px height) containers with `white/30` background. They feature an "inner-carved" shadow and a 4px outer ring glow on focus.

### Navigation Links
- **Active State**: Pill-shaped with a gradient background and a subtle white inner-shadow to give it a 3D "pushed" appearance.
- **Inactive State**: Low-opacity text that gains a glass-panel background and backdrop-blur on hover.

### Cards (Glass Panels)
- Large containers for content sections. Must include a `1px` white border at 30% opacity and a `backdrop-filter: blur(20px)`. For empty states, use dashed borders at `white/60`.

### Status Indicators
- Compact, uppercase labels with wide tracking (0.1em) and 10px font size, paired with Material Symbols at 16px.