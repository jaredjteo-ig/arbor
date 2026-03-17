# T109: Shadow Agent Design Tokens and CSS Extensions

## What

Add new CSS custom properties to `globals.css` for the shadow agent presence system. These extend the existing token system without modifying any existing tokens.

## Where

- `apps/web/src/app/globals.css` — Add new `:root` variables under a "Shadow Agent" section

## Tokens to Add

```css
/* Shadow Agent — AI presence colors */
--shadow-glow: rgba(30, 58, 95, 0.1);
--shadow-accent: #2a6fa8;
--shadow-pulse: #4a90c4;
--shadow-border: rgba(30, 58, 95, 0.2);
--shadow-text: var(--foreground);
--shadow-surface: rgba(30, 58, 95, 0.04);
--shadow-surface-hover: rgba(30, 58, 95, 0.08);
--shadow-mark-bg: var(--color-primary-bg);

/* Shadow Agent — layout */
--shadow-margin-collapsed: 48px;
--shadow-margin-expanded: 320px;
--shadow-widget-size: 44px;
--shadow-widget-inner: 36px;

/* Shadow Agent — animation timing */
--shadow-pulse-duration: 3s;
--shadow-attention-duration: 5s;
--shadow-transition-fast: 150ms;
--shadow-transition-normal: 200ms;
--shadow-transition-slow: 300ms;

/* Shadow Agent — z-index layers */
--z-shadow-annotation: 20;
--z-shadow-margin: 30;
--z-shadow-widget: 35;
--z-shadow-command: 50;
```

Also add keyframe animations:

- `@keyframes shadow-breathe` — opacity oscillation 0.4 to 0.7, 3s cycle
- `@keyframes shadow-ripple` — scale + opacity ring effect for attention state
- `@keyframes shadow-fade-in` — opacity 0 to 1, 200ms

All animations must have `prefers-reduced-motion` fallbacks (already handled by the global rule).

## Evidence Required

- [ ] New tokens visible in globals.css
- [ ] No existing tokens modified
- [ ] Animations defined with reduced-motion support
- [ ] TypeScript build passes (no CSS errors)

## Dependencies

None — this is the foundation task.
