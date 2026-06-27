---
name: FoodieAI Design System
colors:
  surface: '#12121d'
  surface-dim: '#12121d'
  surface-bright: '#383845'
  surface-container-lowest: '#0d0d18'
  surface-container-low: '#1b1a26'
  surface-container: '#1f1e2a'
  surface-container-high: '#292935'
  surface-container-highest: '#343440'
  on-surface: '#e3e0f1'
  on-surface-variant: '#e1bfb5'
  inverse-surface: '#e3e0f1'
  inverse-on-surface: '#302f3b'
  outline: '#a98a80'
  outline-variant: '#594139'
  surface-tint: '#ffb59d'
  primary: '#ffb59d'
  on-primary: '#5d1900'
  primary-container: '#ff6b35'
  on-primary-container: '#5f1900'
  inverse-primary: '#ab3500'
  secondary: '#41eec2'
  on-secondary: '#00382b'
  secondary-container: '#00d1a7'
  on-secondary-container: '#005441'
  tertiary: '#efc141'
  on-tertiary: '#3e2e00'
  tertiary-container: '#d1a626'
  on-tertiary-container: '#503d00'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59d'
  on-primary-fixed: '#390c00'
  on-primary-fixed-variant: '#832600'
  secondary-fixed: '#55fcd0'
  secondary-fixed-dim: '#28dfb5'
  on-secondary-fixed: '#002118'
  on-secondary-fixed-variant: '#00513f'
  tertiary-fixed: '#ffdf92'
  tertiary-fixed-dim: '#eec140'
  on-tertiary-fixed: '#241a00'
  on-tertiary-fixed-variant: '#594400'
  background: '#12121d'
  on-background: '#e3e0f1'
  surface-variant: '#343440'
typography:
  display-lg:
    fontFamily: Outfit
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Outfit
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Outfit
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Outfit
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  container-padding-mobile: 20px
  container-padding-desktop: 40px
  gutter: 24px
  card-gap: 16px
---

## Brand & Style
The design system embodies a premium, high-tech culinary concierge. The brand personality is sophisticated yet appetizing, combining the precision of artificial intelligence with the warmth of gourmet dining. 

The visual style is **Glassmorphism**, set against a deep, cinematic dark mode. This creates a sense of "digital depth," where content feels layered and ethereal. We utilize vibrant gradients and blurred textures to evoke the neon glow of city nightlife and the refined ambiance of upscale restaurants. The emotional response should be one of discovery, exclusivity, and confidence in the AI’s curated recommendations.

## Colors
The palette is anchored by a deep midnight foundation, allowing vibrant accents to pop with high luminosity. 

- **Primary Accent:** A coral-to-amber gradient used exclusively for high-priority actions, ranking badges, and "AI Magic" moments.
- **Secondary Accent:** A soft teal used for utilitarian success states and logistical indicators like delivery availability.
- **Surface Layering:** We do not use solid grays for cards. Instead, we use semi-transparent white (rgba 255, 255, 255, 0.05) to create the frosted glass effect.
- **Typography:** Warm white is used for primary readability to reduce eye strain against the dark background, while muted silver-gray handles metadata.

## Typography
The typography system pairs the geometric, high-fashion personality of **Outfit** for headlines with the industrial clarity of **Inter** for functional body text.

Headlines should utilize tight letter-spacing to maintain a modern, "editorial" feel. Display sizes are reserved for hero sections and major restaurant names. Use the uppercase label style for category tags (e.g., "MICHELIN STARRED", "OPEN NOW") to create a clear visual hierarchy against body descriptions.

## Layout & Spacing
The design system utilizes a **fluid grid** model to ensure the immersive background gradient feels expansive. 

- **Desktop:** 12-column grid with a max-width of 1440px. Gutters are fixed at 24px to provide enough breathing room for the glassmorphic blurs to overlap elegantly.
- **Mobile:** 4-column grid with 20px side margins.
- **Spacing Logic:** All spacing is based on an 8px scale. Use larger 48px-64px gaps between major sections to emphasize the "Premium" minimalist aesthetic.

## Elevation & Depth
Depth in this design system is achieved through **optical transparency** rather than traditional drop shadows.

1.  **Level 0 (Base):** The deep charcoal-to-midnight gradient.
2.  **Level 1 (Cards):** `background: rgba(255, 255, 255, 0.05)`, `backdrop-filter: blur(12px)`, and a `1px solid rgba(255, 255, 255, 0.08)` border.
3.  **Level 2 (Modals/Popovers):** `background: rgba(255, 255, 255, 0.08)`, `backdrop-filter: blur(20px)`, and a subtle outer glow using the primary accent color at 10% opacity.

Avoid using black shadows; if a shadow is necessary for legibility, use a soft, large-radius shadow with a deep navy tint (#05050a).

## Shapes
We use a **Rounded** shape language to soften the technical feel of the AI. Standard cards and input fields use a 16px (1rem) corner radius. Elements that are highly interactive, such as chips and search bars, should use the **Pill-shaped** (rounded-full) style to distinguish them from static content containers.

## Components

- **Buttons:** Primary buttons use the `accent_gradient` with white text and a subtle box-shadow glow that matches the amber end of the gradient. Secondary buttons are "Ghost" style with a glass background and white border.
- **Glassmorphic Cards:** Every card must have the 1px semi-transparent border to ensure it doesn't get lost against the dark background. Images inside cards should have a subtle darkening overlay at the bottom to ensure white text remains legible.
- **Range Sliders:** Used for price and distance. The track should be a muted midnight blue, and the handle should be the vibrant coral primary color. As the user slides, provide real-time feedback with star icons that glow as the rating increases.
- **Chips/Badges:** Use a solid `rgba(255, 255, 255, 0.1)` background for general tags, but use the `secondary_color` (Teal) for status-driven badges like "Table Available."
- **Animated Transitions:** Use "Spring" physics for card hover states—a slight scale-up (1.02x) and an increase in the border opacity to 0.2. This makes the glass feel tactile and responsive.