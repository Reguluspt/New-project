---
name: Vibrant Enterprise
colors:
  surface: '#faf9ff'
  surface-dim: '#ccdaff'
  surface-bright: '#faf9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f3ff'
  surface-container: '#e9edff'
  surface-container-high: '#e1e8ff'
  surface-container-highest: '#d8e2ff'
  on-surface: '#051a3e'
  on-surface-variant: '#434654'
  inverse-surface: '#1d3054'
  inverse-on-surface: '#edf0ff'
  outline: '#737685'
  outline-variant: '#c3c6d6'
  surface-tint: '#0c56d0'
  primary: '#003d9b'
  on-primary: '#ffffff'
  primary-container: '#0052cc'
  on-primary-container: '#c4d2ff'
  inverse-primary: '#b2c5ff'
  secondary: '#5e4db9'
  on-secondary: '#ffffff'
  secondary-container: '#9f8eff'
  on-secondary-container: '#341d8d'
  tertiary: '#5e3c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#7d5200'
  on-tertiary-container: '#ffca81'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2ff'
  primary-fixed-dim: '#b2c5ff'
  on-primary-fixed: '#001848'
  on-primary-fixed-variant: '#0040a2'
  secondary-fixed: '#e5deff'
  secondary-fixed-dim: '#c9bfff'
  on-secondary-fixed: '#1a0063'
  on-secondary-fixed-variant: '#4633a0'
  tertiary-fixed: '#ffddb3'
  tertiary-fixed-dim: '#ffb950'
  on-tertiary-fixed: '#291800'
  on-tertiary-fixed-variant: '#624000'
  background: '#faf9ff'
  on-background: '#051a3e'
  surface-variant: '#d8e2ff'
typography:
  h1:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  gutter: 24px
  margin: 40px
---

## Brand & Style

This design system centers on a **Corporate / Modern** aesthetic that balances high-efficiency enterprise functionality with an approachable, contemporary energy. The brand personality is dependable and precise, yet avoids the coldness of traditional legacy software by utilizing soft geometry and a breathable layout.

The target audience consists of data-driven professionals who require a high information density without cognitive overload. The UI evokes a sense of "organized flow"—where vibrant accents guide the eye and soft elevations provide a clear mental model of the workspace hierarchy.

## Colors

The palette is anchored by a vibrant **Atlassian Blue (#0052CC)**, serving as the primary driver for actions and brand presence. To achieve the "approachable" requirement, the background is not a stark white but a very light blue-gray tint, reducing eye strain and helping white card components pop.

- **Primary**: Used for main actions, active states, and primary navigation elements.
- **Secondary**: A muted purple used for secondary data visualizations or supporting badges.
- **Neutral**: Deep blues and grays are used for text and borders to maintain a professional "Enterprise" feel.
- **Surface**: Pure white is reserved for cards and modals to create a clear "layer" above the tinted background.

## Typography

This design system utilizes **Inter** exclusively to ensure maximum legibility across dense data tables and complex dashboards. The type scale is optimized for screen-based reading with a slight negative letter-spacing on larger headings to maintain a modern, compact feel.

For enterprise contexts, use `body-md` (14px) as the standard text size for forms and lists. Reserve `label-md` for table headers and small metadata tags to provide clear structural distinction.

## Layout & Spacing

The layout follows a **Fluid Grid** model with a 12-column structure for main content areas. It uses a base 8px rhythmic scale to ensure consistent alignment. 

Margins are generous (40px) to give the application a premium, "breathable" feel. Gutters are fixed at 24px to prevent content from feeling cramped during high-density data display. Elements should prioritize vertical stacking with `16px` (md) padding within cards and containers.

## Elevation & Depth

Depth is conveyed through **Ambient Shadows** and tonal layering. This design system avoids harsh borders in favor of soft, diffused shadows that use a slight blue tint (`rgba(9, 30, 66, 0.08)`) to harmonize with the background.

- **Level 0 (Floor)**: The light gray/blue tinted background.
- **Level 1 (Card)**: White surfaces with a 4px blur shadow. Used for the main workspace.
- **Level 2 (Dropdown/Popover)**: White surfaces with an 8px blur shadow. Used for context menus.
- **Level 3 (Modal)**: White surfaces with a 24px blur shadow. Used for high-priority interruptions.

## Shapes

The shape language is defined by **Rounded** corners that soften the "technical" nature of enterprise data. 

- **Standard Buttons & Inputs**: 8px (`rounded-md`) to feel modern yet stable.
- **Cards & Containers**: 12px (`rounded-lg`) to create a clear containerized look.
- **Utility Tags/Chips**: Fully rounded (Pill) to distinguish them from actionable buttons.

## Components

- **Buttons**: Primary buttons use the vibrant blue with white text. Secondary buttons use a subtle gray ghost style with blue text. Avoid heavy gradients; use solid fills.
- **Inputs**: Use a 1px border (`#DFE1E6`) that transitions to the primary blue on focus. Backgrounds should be white or a very light gray.
- **Cards**: Cards are the primary organizational unit. They should have a 12px corner radius, a white background, and the Level 1 "Ambient Shadow."
- **Chips**: Use for status and filtering. They should have a light background tint of the primary color (e.g., 10% opacity) and bolded text for readability.
- **Data Tables**: Remove vertical borders. Use subtle horizontal dividers (`1px solid #EBECF0`). The header row should use the `label-md` typography style with a light tinted background.
- **Sidebar**: A slightly darker tint of the background or a deep navy (`#091E42`) to create a strong vertical anchor for navigation.