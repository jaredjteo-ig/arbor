# Shadow Agent UX Design: Component Specifications

**Design Authority**: Brief 04 (Shadow Agent) + Impact-Verse Shadow Agent Blueprint
**Design System**: Arbor Design System (`globals.css` tokens, `design-system/` components)
**Target**: Next.js 16 + Tailwind v4 + Lucide icons

---

## Table of Contents

1. [Design Tokens: Shadow Agent Extension](#1-design-tokens)
2. [Shadow Widget](#2-shadow-widget)
3. [Command Surface](#3-command-surface)
4. [Margin Presence](#4-margin-presence)
5. [Inline Annotations](#5-inline-annotations)
6. [Employee Interface](#6-employee-interface)
7. [AppShell Integration](#7-appshell-integration)
8. [Animation Specifications](#8-animation-specifications)
9. [Responsive Behavior Matrix](#9-responsive-behavior-matrix)
10. [Accessibility Requirements](#10-accessibility-requirements)

---

## 1. Design Tokens: Shadow Agent Extension {#1-design-tokens}

New CSS custom properties added to `:root` in `globals.css`. These extend the existing token system without modifying any existing tokens.

```css
:root {
  /* Shadow Agent — AI presence colors */
  --shadow-glow: rgba(
    30,
    58,
    95,
    0.1
  ); /* Tinted bg for AI areas (uses primary hue) */
  --shadow-accent: #2a6fa8; /* Interactive AI elements */
  --shadow-pulse: #4a90c4; /* Animated pulse indicator */
  --shadow-border: rgba(30, 58, 95, 0.2); /* Borders on AI-annotated elements */
  --shadow-text: var(
    --foreground
  ); /* AI text = normal text (no special color) */

  /* Shadow Agent — surfaces */
  --shadow-surface: rgba(30, 58, 95, 0.04); /* Lightest AI background tint */
  --shadow-surface-hover: rgba(30, 58, 95, 0.08); /* AI surface hover */
  --shadow-mark-bg: var(--color-primary-bg); /* Shadow mark icon background */

  /* Shadow Agent — layout */
  --shadow-margin-collapsed: 48px;
  --shadow-margin-expanded: 320px;
  --shadow-widget-size: 44px; /* Meets 44px minimum touch target */
  --shadow-widget-inner: 36px; /* Visual circle inside touch target */

  /* Shadow Agent — animation timing */
  --shadow-pulse-duration: 3s;
  --shadow-attention-duration: 5s;
  --shadow-transition-fast: 150ms;
  --shadow-transition-normal: 200ms;
  --shadow-transition-slow: 300ms;

  /* Shadow Agent — z-index layer */
  --z-shadow-margin: 30;
  --z-shadow-widget: 35;
  --z-shadow-command: 50;
  --z-shadow-annotation: 20;
}
```

**Rationale**: The shadow agent's color identity is derived from `--color-primary` (#1E3A5F) rather than introducing an entirely new hue. This keeps the AI presence within the existing brand palette while the translucent, glowing treatments distinguish it from standard platform elements. The reference architecture uses an "ocean" palette for Impact-Verse; Arbor adapts this to its navy primary.

---

## 2. Shadow Widget {#2-shadow-widget}

The Shadow Widget replaces the current floating AdvisoryFAB button. It is the persistent entry point to the command surface.

### 2.1 Component Hierarchy

```
ShadowWidget (root)
  ShadowWidgetButton
    ShadowMark (icon)
    PulseRing (ambient animation)
    AttentionRipple (conditional, when agent has content)
  ShadowWidgetTooltip (hover/focus)
```

### 2.2 Visual States

#### Resting State

- **Container**: `44px` touch target (invisible padding), `36px` visible circle
- **Background**: `var(--color-primary)` at `opacity: 0.55`
- **Icon**: Custom shadow mark SVG, 16px, white at `opacity: 0.8`
- **Position**: Fixed, bottom-right corner. `bottom: 24px; right: 24px`
- **When margin is visible** (desktop): Widget moves into the margin strip, positioned at the bottom of the 48px margin column. `bottom: 24px; right: 12px` (centered in margin)
- **Shadow**: None (the widget itself is subtle, not elevated)
- **Cursor**: `pointer`

```
Tailwind classes:
  "fixed z-[var(--z-shadow-widget)]"
  "flex items-center justify-center"
  "w-[var(--shadow-widget-size)] h-[var(--shadow-widget-size)]"
  "rounded-full cursor-pointer"
  "transition-all duration-[var(--shadow-transition-normal)]"
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
```

Inner circle:

```
  "w-[var(--shadow-widget-inner)] h-[var(--shadow-widget-inner)]"
  "rounded-full"
  "bg-[var(--color-primary)] opacity-55"
  "flex items-center justify-center"
```

#### Hover State

- **Opacity**: Circle rises to `1.0`
- **Scale**: `scale(1.08)` on the inner circle
- **Tooltip**: Appears above or left of widget. Text: "Ask Arbor" with keyboard shortcut badge `Ctrl+Shift+A`
- **Transition**: `200ms ease-out`

```
hover:opacity-100 hover:scale-108
```

#### Focus State (keyboard navigation)

- Same visual treatment as hover
- Plus `outline: 2px solid var(--color-primary); outline-offset: 2px`

#### Attention State

When the shadow agent has a pending insight, compliance alert, or proactive suggestion:

- **Ripple animation**: A single concentric ring expands outward from the widget, `opacity: 0.3` to `0`, over 1.5 seconds. Repeats once every 5 seconds (not continuous).
- **Color**: `var(--shadow-pulse)` at 30% opacity for the ripple
- **Inner circle**: Background shifts to `var(--color-primary)` at full opacity
- **No badge**: No number badge, no red dot. The ripple communicates "something is here" without urgency or count.

```css
@keyframes shadowAttentionRipple {
  0% {
    transform: scale(1);
    opacity: 0.3;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}

.shadow-widget-attention::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 9999px;
  border: 2px solid var(--shadow-pulse);
  animation: shadowAttentionRipple 1.5s ease-out;
  animation-delay: 0s;
  /* Repeats on a 5s interval via JS toggling the class */
}
```

#### Active / Pressed State

- **Scale**: `scale(0.95)` on inner circle
- **Duration**: `100ms`
- Opens the command surface

#### Disabled / Degraded State

When the AI backend is unavailable (API key invalid, service down):

- **Opacity**: `0.3`
- **No pulse animation**
- **Tooltip**: "Arbor is temporarily unavailable"
- **Click behavior**: Shows a small toast explaining the issue rather than opening the command surface

### 2.3 Shadow Mark Icon

A custom SVG, not a Lucide icon. Geometric abstraction: a small filled circle (the "self") with a gradient trailing edge to the right (the "shadow"). This avoids anthropomorphism while creating a recognizable identity.

```svg
<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
  <circle cx="6" cy="8" r="4" fill="currentColor"/>
  <ellipse cx="10.5" cy="10" rx="4" ry="2.5" fill="currentColor" opacity="0.25"/>
</svg>
```

The mark is used consistently across: Shadow Widget, Command Surface header, Margin cards, and inline annotation disclosure.

### 2.4 Reduced Motion Fallback

```css
@media (prefers-reduced-motion: reduce) {
  .shadow-widget-pulse,
  .shadow-widget-attention::after {
    animation: none !important;
  }
  /* Attention state: static opacity change only */
  .shadow-widget-attention .shadow-widget-inner {
    opacity: 1;
    /* Subtle static indicator replaces ripple */
    box-shadow: 0 0 0 3px var(--shadow-pulse);
  }
}
```

### 2.5 Mobile Behavior

- **Position**: `bottom: 16px; right: 16px` (closer to edge on mobile)
- **Touch target**: Already 44px, meets minimum
- **No margin integration** on mobile (margin does not exist; see Section 4.6)
- **Attention state**: Same ripple but at 50% frequency (every 10s) to reduce distraction on small screens

---

## 3. Command Surface {#3-command-surface}

The command palette overlay. Invoked by clicking the Shadow Widget or pressing `Ctrl+Shift+A`.

### 3.1 Component Hierarchy

```
CommandSurface (portal, renders at document root)
  CommandBackdrop (dimmed overlay)
  CommandPanel
    CommandHeader
      ShadowMark
      KeyboardShortcutBadge
      CloseButton
    CommandInput
      SearchIcon (left)
      TextInput (autofocus)
      ClearButton (when has content)
    CommandBody
      CommandSuggestions (default state)
        RecentCommands
        ContextualSuggestions
        CapabilityMatches (as user types)
      CommandResult (after submission)
        ResultContent (markdown, tables, calculations)
        ResultCitations (provision pills)
        ResultActions (pin to margin, navigate, etc.)
      CommandLoading (thinking state)
        StreamOfThought steps
    CommandFooter
      DisclaimerText
      EscapeHint
```

### 3.2 Layout

#### Desktop (viewport >= 768px)

```
+──────────────────────────────────────────────────+
|  backdrop: bg-black/40, blur(2px)                |
|                                                  |
|     +──────────────────────────────────────+     |
|     |  Command Panel                       |     |  <- Top 1/3 of screen
|     |  max-w-2xl, mx-auto                  |     |
|     |  mt-[15vh]                           |     |
|     |  rounded-xl                          |     |
|     |  shadow-[var(--shadow-modal)]        |     |
|     |  bg-[var(--color-surface-card)]      |     |
|     |  max-h-[60vh], overflow-y-auto       |     |
|     +──────────────────────────────────────+     |
|                                                  |
|     (remaining screen: dimmed content)           |
+──────────────────────────────────────────────────+
```

- **Panel width**: `max-w-2xl` (672px) centered horizontally
- **Panel offset**: `margin-top: 15vh` (top third positioning)
- **Panel max height**: `max-h-[60vh]` with internal scroll
- **Panel radius**: `rounded-xl` (12px, matching AppCard)
- **Panel shadow**: `var(--shadow-modal)`
- **Panel border**: `border border-[var(--color-gray-200)]`

#### Mobile (viewport < 768px)

Full-screen overlay, bottom-anchored:

```
+──────────────────────────────+
|  backdrop: bg-black/40       |
|                              |
|  +──────────────────────────+|
|  | Command Panel            ||  <- Bottom sheet
|  | rounded-t-xl             ||
|  | h-[85vh]                 ||
|  | bg-[var(--color-surface- ||
|  |   card)]                 ||
|  |                          ||
|  | [Input at top]           ||
|  | [Results below]          ||
|  +──────────────────────────+|
+──────────────────────────────+
```

- **Panel**: Full width, `rounded-t-xl`, slides up from bottom
- **Height**: `max-h-[85vh]`
- **Drag handle**: 40px x 4px rounded bar at top center for swipe-to-dismiss

### 3.3 Command Input

The single-line input that receives natural language commands.

```
+──────────────────────────────────────────────────────+
| [Shadow Mark]  > What notice period for 3 years? [x] |
+──────────────────────────────────────────────────────+
```

- **Left**: Shadow mark icon (16px, `var(--color-gray-400)`)
- **Prompt character**: `>` in `var(--color-gray-400)`, `text-body`, `font-mono`
- **Input**: Full width, `text-body-lg` (16px), no border (borderless within the panel)
- **Placeholder**: "Ask a question or give a command..." in `var(--color-gray-400)`
- **Right**: Clear button (X icon) when input has content
- **Autofocus**: Input receives focus immediately on open
- **Submit**: `Enter` key sends. `Shift+Enter` does nothing (single-line input).
- **Padding**: `px-5 py-4` for the input row
- **Border-bottom**: `1px solid var(--color-gray-200)` separating input from body

### 3.4 Suggestion List (Default State)

Shown when the command surface opens and the input is empty.

```
CommandSuggestions
  SuggestionGroup "Recent"
    SuggestionItem (icon + text + timestamp)
    SuggestionItem
    SuggestionItem
  SuggestionGroup "Suggested for you"
    SuggestionItem (contextual, based on current page + user patterns)
    SuggestionItem
  SuggestionGroup "Common actions"
    SuggestionItem "Calculate CPF contributions"
    SuggestionItem "Check compliance status"
    SuggestionItem "Show notice period rules"
```

Each **SuggestionItem**:

- **Layout**: `flex items-center gap-3 px-5 py-3`
- **Icon**: Lucide icon matching the action type (Calculator, Shield, FileText, etc.), 16px, `var(--color-gray-400)`
- **Text**: `text-body` (14px), `var(--color-gray-700)`
- **Timestamp** (recent only): `text-caption` (12px), `var(--color-gray-400)`, right-aligned
- **Hover**: `bg-[var(--color-gray-50)]`
- **Active/Selected**: `bg-[var(--color-primary-bg)]`
- **Keyboard navigation**: Arrow keys move selection highlight. Enter submits the selected item.
- **Touch target**: min-height `44px`

**SuggestionGroup** label:

- `text-micro` (11px), `var(--color-gray-400)`, uppercase, `tracking-wider`
- `px-5 pt-4 pb-1`

### 3.5 Capability Matching (As User Types)

As the user types, the suggestion list is replaced by matched capabilities:

```
> Calculate CPF
  ├─ Calculate CPF for a specific salary       [Calculator]
  ├─ What are the 2026 CPF rates?              [KB Lookup]
  └─ Calculate CPF for all my employees        [Bulk Action]
```

- Matching occurs client-side against a static capability registry
- Matched text segments are highlighted with `font-semibold` and `var(--color-primary)`
- Non-matching suggestions fade out with `opacity: 0.5`
- Maximum 8 matches shown

### 3.6 Result Rendering

After the user submits a command, results replace the suggestion list.

#### Text Results (KB lookups, advisory answers)

```
CommandResult
  ResultHeader
    [AI badge] "Based on 3 provisions"
  ResultBody
    [Markdown content — same rendering as SystemMessage]
    [Streaming cursor if still generating]
  ResultCitations
    [SourceCitation pills — reuse existing component]
  ResultActions
    [Pin to margin] [Open in Advisory] [Copy]
```

- **AI badge**: Same `text-[10px] font-medium bg-[var(--shadow-surface)] text-[var(--color-primary)] px-1.5 py-0.5 rounded` badge used in SystemMessage
- **Content**: Rendered with ReactMarkdown + rehypeSanitize (same pipeline as `SystemMessage`)
- **Citations**: Reuse `SourceCitation` component from `design-system/`
- **Risk tier**: If the response has a risk tier, show `RiskTierBadge` (reuse from design system)
- **Padding**: `px-5 py-4`

#### Calculation Results (CPF, quotas, leave)

```
CommandResult
  ResultHeader
    [Calculator icon] "CPF Calculation Result"
  CalculationTable
    Row: "Employee CPF (20%)"  "$1,000.00"
    Row: "Employer CPF (17%)"  "$850.00"
    Row: "Total CPF"           "$1,850.00"  (bold)
  ResultNotes
    "Based on 2026 rates. Ordinary Wages ceiling: $6,800/month."
  ResultActions
    [Open in Calculators] [Copy] [Pin to margin]
```

- **Table**: Simple 2-column layout with `text-body` sizing
- **Bold row**: `font-semibold` for totals
- **Notes**: `text-caption` (12px), `var(--color-gray-500)`, with provision citations inline

#### Navigation Confirmations

When the command matches a page navigation:

```
CommandResult
  NavigationCard
    [PageIcon] "Compliance Check"
    "Opening the compliance self-assessment page"
    [Navigate button]
```

- Auto-navigates after 1s delay (with visible countdown)
- User can click "Navigate now" to skip the delay
- User can press Escape to cancel navigation

#### Action Plan Results (document generation, onboarding workflows)

```
CommandResult
  ActionPlanCard
    Title: "Generate KET Document"
    Steps:
      1. "Gather employee details"       [checkbox]
      2. "Generate document from template" [checkbox]
      3. "Preview for your review"         [checkbox]
    Actions:
      [Start] [Adjust] [Cancel]
    Reasoning (expandable):
      "This action will create a Key Employment Terms..."
```

- Follows the Action Plan pattern from the reference architecture
- `[Start]` uses `AppButton variant="primary" size="sm"`
- `[Cancel]` uses `AppButton variant="text" size="sm"`
- Steps use `StepIndicator` component from design system

### 3.7 Thinking State (Stream of Thought)

While the agent processes a command, show structured thinking steps:

```
CommandThinking
  ThinkingStep (completed) "Searching knowledge base..."    [check]
  ThinkingStep (active)    "Analysing provisions..."        [spinner]
  ThinkingStep (pending)   "Generating response..."         [dot]
```

- **Completed step**: `var(--color-gray-400)` text, `CheckCircle2` icon (12px, `var(--color-success)`)
- **Active step**: `var(--color-gray-700)` text, `Loader2` icon (12px, `var(--color-primary)`, spinning)
- **Pending step**: `var(--color-gray-300)` text, `Circle` icon (12px, `var(--color-gray-300)`)
- **Step text**: `text-caption` (12px)
- **Layout**: `flex flex-col gap-2 px-5 py-4`

This replaces the bouncing dots from the current `ThinkingIndicator` in `ChatContainer`. The bouncing dots are appropriate for chat; structured steps are appropriate for a command palette.

### 3.8 Transition Animations

**Opening**:

1. Backdrop fades in: `opacity 0 -> 1`, `150ms ease-out`
2. Panel slides down: `translateY(-8px) -> translateY(0)` + `opacity 0 -> 1`, `200ms ease-out`, `50ms delay`
3. Input receives focus: `50ms` after panel animation completes

**Closing (Escape or backdrop click)**:

1. Panel fades out: `opacity 1 -> 0`, `150ms ease-in`
2. Backdrop fades out: `opacity 1 -> 0`, `150ms ease-in`, simultaneous

**Mobile opening**:

1. Backdrop fades in: `150ms`
2. Panel slides up from bottom: `translateY(100%) -> translateY(0)`, `250ms ease-out`

**Mobile closing**:

1. Panel slides down: `translateY(0) -> translateY(100%)`, `200ms ease-in`
2. Backdrop fades out: `150ms`

**Reduced motion**:

```css
@media (prefers-reduced-motion: reduce) {
  .command-surface-panel,
  .command-surface-backdrop {
    transition: none !important;
    animation: none !important;
  }
  /* Instant show/hide */
}
```

### 3.9 Keyboard Shortcuts

| Key                  | Action                                                     |
| -------------------- | ---------------------------------------------------------- |
| `Ctrl+Shift+A`       | Open/close command surface (global)                        |
| `Escape`             | Close command surface; if streaming, stop generation first |
| `Enter`              | Submit command or select highlighted suggestion            |
| `Arrow Up/Down`      | Navigate suggestion list                                   |
| `Tab`                | Move focus to result action buttons                        |
| `Ctrl+C` (in result) | Copy result text                                           |

The global shortcut `Ctrl+Shift+A` is registered via a `useEffect` on the `AppShell` component. It does not conflict with any browser default shortcut.

### 3.10 Command Surface vs Advisory Page

The command surface is **not** a replacement for the Advisory page. It is transient and stateless in presentation.

| Attribute    | Command Surface                             | Advisory Page                                         |
| ------------ | ------------------------------------------- | ----------------------------------------------------- |
| Entry        | Widget click or `Ctrl+Shift+A`              | Sidebar "Advisory" link                               |
| Persistence  | Escape dismisses; no history visible        | Full conversation history with sidebar                |
| History      | No visible thread; each invocation is fresh | Scrollable message thread with search, rename, delete |
| Citations    | Inline `SourceCitation` pills               | Full `ProvisionViewer` modal on click                 |
| Escalation   | "Connect to specialist" as action button    | Full `EscalationDialog` with form fields              |
| Depth        | Quick questions, single-turn                | Extended multi-turn research conversations            |
| Visual style | Floating command palette                    | Full-page split layout                                |

Both share the same backend advisory pipeline, safety chain, KB, and trust chain.

---

## 4. Margin Presence {#4-margin-presence}

A 48px-wide persistent strip along the right edge of every page (desktop only). This is not a sidebar -- it is a margin. It occupies minimal space and communicates peripheral awareness.

### 4.1 Component Hierarchy

```
ShadowMargin (root)
  MarginCollapsed (48px state)
    ShadowPulse (top)
    ContextThread (middle)
      ContextDot (0-5 instances)
    ActionSeed (bottom, conditional)
    ShadowWidget (repositioned into margin bottom)
  MarginExpanded (320px state)
    MarginHeader
      "Insights" title
      CollapseButton
    InsightCard (top — most relevant)
    ActionCards (proposed actions)
    MemoryThread (recent observations)
    QuickCommandBar (single-line input)
```

### 4.2 Collapsed State (48px)

```
+----+
| .  | <- Shadow pulse (8px circle, animated opacity)
|    |
|    |
| .  | <- Context dot 1
| .  | <- Context dot 2
| .  | <- Context dot 3
|    |
|    |
| [w]| <- Shadow widget (repositioned)
+----+
  48px
```

**Container**:

- `width: 48px`, full height of main content area
- `bg-transparent` (no background -- it's a margin, not a panel)
- `border-left: 1px solid var(--color-gray-200)` (subtle separator)
- `z-index: var(--z-shadow-margin)`
- `position: relative` (within the AppShell flex layout)
- `display: flex; flex-direction: column; align-items: center; padding: 16px 0`

#### Shadow Pulse

- **Element**: 8px circle
- **Color**: `var(--shadow-pulse)`
- **Position**: `margin-top: 16px`, centered horizontally
- **Animation**: Opacity oscillates between 0.3 and 0.6 on a 3-second `ease-in-out` cycle
- **Attention variation**: When agent has content, opacity rises to 1.0 over 500ms, holds 3s, returns to ambient. No size change.

```css
@keyframes shadowPulseAmbient {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.6;
  }
}

.shadow-pulse {
  width: 8px;
  height: 8px;
  border-radius: 9999px;
  background: var(--shadow-pulse);
  animation: shadowPulseAmbient var(--shadow-pulse-duration) ease-in-out
    infinite;
}

.shadow-pulse-attention {
  animation: none;
  opacity: 1;
  transition: opacity 500ms ease-in-out;
}

@media (prefers-reduced-motion: reduce) {
  .shadow-pulse {
    animation: none;
    opacity: 0.5;
  }
  .shadow-pulse-attention {
    opacity: 1;
  }
}
```

#### Context Dots

- **Layout**: Vertical column, centered, `gap: 12px`, positioned in the middle third of the margin
- **Each dot**: 6px circle, `bg-[var(--color-gray-300)]`
- **New dot**: Appears with `var(--shadow-accent)` color, fades to `var(--color-gray-300)` over 2 seconds
- **Maximum**: 5 visible dots. When a 6th arrives, the oldest fades out.
- **Hover**: Shows a tooltip to the left of the dot with one-line context text

**Tooltip**:

```
Tailwind:
  "absolute right-full mr-2 px-3 py-1.5 rounded-lg"
  "bg-[var(--color-gray-900)] text-white text-xs"
  "whitespace-nowrap shadow-[var(--shadow-raised)]"
  "opacity-0 group-hover:opacity-100"
  "transition-opacity duration-150"
  "pointer-events-none"
  "max-w-[240px] whitespace-normal"
```

Example tooltip texts:

- "Your KET compliance gap has been open for 30 days"
- "CPF rates updated for 2026 -- affects 3 employees"
- "Foreign worker levy deadline is end of month"

#### Action Seed

- **Visibility**: Only shown when the agent has a proposed action ready
- **Element**: Single icon, 20px, `var(--color-primary)`, centered
- **Icon mapping**:
  - Calculator icon -> calculation ready
  - Shield icon -> compliance alert
  - FileText icon -> document suggestion
  - AlertTriangle icon -> urgent compliance issue (uses `var(--color-risk-amber)`)
- **Hover**: Scale 1.1, tooltip showing action summary
- **Click**: Expands the margin to show the action card
- **Position**: Above the Shadow Widget, `margin-bottom: 16px`

### 4.3 Expanded State (320px)

Triggered by clicking anywhere in the collapsed margin, clicking a context dot, clicking the action seed, or pressing `Ctrl+Shift+I`.

```
+──────────────────────────────────────────+──────────────────────+
|                                          |                      |
|       Main Content Area                  |  Shadow Margin       |
|       (compressed to make room)          |  320px               |
|                                          |                      |
|                                          |  [Insights]  [<]     |
|                                          |                      |
|                                          |  +────────────────+  |
|                                          |  | Top Insight    |  |
|                                          |  | "2 compliance  |  |
|                                          |  |  gaps — fine   |  |
|                                          |  |  risk $10,000" |  |
|                                          |  +────────────────+  |
|                                          |                      |
|                                          |  +────────────────+  |
|                                          |  | Action: Run    |  |
|                                          |  | compliance     |  |
|                                          |  | check          |  |
|                                          |  | [Do it] [Skip] |  |
|                                          |  +────────────────+  |
|                                          |                      |
|                                          |  Memory thread:      |
|                                          |  - "You check CPF    |
|                                          |    monthly"          |
|                                          |  - "Last compliance  |
|                                          |    check: 14 days"   |
|                                          |                      |
|                                          |  +────────────────+  |
|                                          |  | > Quick command |  |
|                                          |  +────────────────+  |
+──────────────────────────────────────────+──────────────────────+
```

**Container**:

- `width: 320px`
- `bg-[var(--color-surface-card)]`
- `border-left: 1px solid var(--color-gray-200)]`
- `transition: width 250ms ease-in-out`
- `overflow-y: auto; overflow-x: hidden`
- `display: flex; flex-direction: column`
- `padding: 0`

**Header**:

- `flex items-center justify-between px-4 py-3 border-b border-[var(--color-gray-200)]`
- Title: "Insights" — `text-sm font-semibold text-[var(--color-gray-900)]`
- Collapse button: `ChevronRight` icon, 44px touch target, right-aligned

**Insight Card** (top card):

- Uses `AppCard variant="flat"` with a left border accent
- Left border: `2px solid var(--shadow-accent)`
- Background: `var(--shadow-surface)`
- Content: `text-body` (14px), `var(--color-gray-700)`
- AI disclosure: Shadow mark icon (12px) + "AI insight" label in `text-micro`
- Padding: `px-4 py-3`

**Action Cards**:

- Same structure as Insight Card but with action buttons
- Button row: `flex gap-2 mt-3`
- Primary action: `AppButton variant="primary" size="sm"`
- Dismiss: `AppButton variant="text" size="sm"`
- "Reasoning" expandable: Chevron toggle, `text-caption`, `var(--color-gray-500)`

**Memory Thread**:

- Section label: "Recent observations" in `text-micro`, uppercase
- Each observation: `text-caption` (12px), `var(--color-gray-600)`, with "Not right" link
- "Not right" link: `text-caption`, `var(--color-gray-400)`, underline on hover
- Clicking "Not right" shows a single-line correction input
- Each observation has a small `x` button to dismiss

**Quick Command Bar**:

- Sticks to the bottom of the expanded margin
- `border-t border-[var(--color-gray-200)] px-4 py-3`
- Single-line input with `>` prompt character
- `Enter` submits (same backend as command surface)
- Results appear above the input in the margin, replacing the card stack temporarily

### 4.4 Transition: Collapse to Expand

- **Width transition**: `48px -> 320px`, `250ms ease-in-out`
- **Main content**: Compresses to accommodate. The AppShell's main area flex-shrinks.
- **Content fade-in**: Expanded margin content fades in `opacity 0 -> 1` over `200ms`, starting at `100ms` delay (after width transition begins)
- **Reduced motion**: Width changes instantly (no transition). Content appears instantly.

### 4.5 Integration with AppShell Layout

The current `AppShell` layout is:

```
<div class="flex h-screen">
  <NavigationSidebar />       <!-- left -->
  <div class="flex-1">        <!-- main area -->
    <TopBar />
    <main>{children}</main>
  </div>
</div>
```

With the Shadow Margin, this becomes:

```
<div class="flex h-screen">
  <NavigationSidebar />       <!-- left -->
  <div class="flex-1 flex">   <!-- main area + margin -->
    <div class="flex-1 flex flex-col min-w-0">
      <TopBar />
      <main>{children}</main>
    </div>
    <ShadowMargin />          <!-- right, 48px or 320px -->
  </div>
</div>
```

The `ShadowMargin` is a flex sibling of the main content column. When it expands from 48px to 320px, the main content column (`flex-1 min-w-0`) naturally compresses. The `min-w-0` prevents the main content from overflowing.

### 4.6 Mobile Behavior

The margin does not exist on mobile (`viewport < 768px`). Instead:

- **Context dots** appear as a subtle horizontal row above the Shadow Widget, visible only when the widget is in attention state
- **Expanded margin content** transforms into a **bottom sheet** (same pattern as mobile command surface but with margin content)
- **Trigger**: Long-press on the Shadow Widget (500ms) opens the bottom sheet margin view
- **Bottom sheet**: `rounded-t-xl`, draggable, `max-h-[70vh]`, contains the same card stack as the expanded margin

---

## 5. Inline Annotations {#5-inline-annotations}

AI insights embedded directly within existing pages. These appear as part of the page content, not in a separate panel.

### 5.1 Component Hierarchy

```
ShadowAnnotation (generic wrapper)
  AnnotationDisclosure (shadow mark icon, 12px)
  AnnotationContent (text content)
  AnnotationDismiss (x button, visible on hover)
```

### 5.2 Visual Treatment

All inline annotations share a common visual language:

- **Background**: `var(--shadow-surface)` — a 4% tint of the primary color
- **Left border**: `2px solid var(--shadow-border)` — a 20% opacity primary border
- **Text**: `text-caption` (12px) or `text-body` (14px), `var(--color-gray-700)` — same as platform text
- **Disclosure icon**: Shadow mark (12px), `var(--color-gray-400)`, at the start of the annotation
- **Dismiss**: Small `x` (12px), `var(--color-gray-400)`, opacity 0, appears on hover
- **Border radius**: `rounded-lg` (8px)
- **Padding**: `px-3 py-2`

```
Tailwind:
  "rounded-lg px-3 py-2"
  "bg-[var(--shadow-surface)]"
  "border-l-2 border-l-[var(--shadow-border)]"
  "text-caption text-[var(--color-gray-700)]"
  "flex items-start gap-2"
  "group"
```

### 5.3 Compliance Page Annotations

Appear below each compliance checklist item that has AI context.

**Risk annotation on checklist item**:

```
+──────────────────────────────────────────────────────────────+
| [Shield] Employment Act — KETs                    [Red]      |
|                                                              |
|   +────────────────────────────────────────────────────────+ |
|   | [mark] Mandatory — fine up to $5,000 per offence.      | |
|   |        EA s95A. 3 of 8 items require action.           | |
|   +────────────────────────────────────────────────────────+ |
|                                                              |
+──────────────────────────────────────────────────────────────+
```

- **Integration point**: Inserted as a child element below each compliance domain card
- **Condition**: Only shown when the AI has contextual information for that domain
- **Citation**: Provision references are clickable `SourceCitation` pills inline
- **Persistence**: Persists until dismissed. Dismissal is per-user, stored in localStorage

**Progress annotation**:

```
  +────────────────────────────────────────────────────────────+
  | [mark] 3 of 8 items compliant. Priority: KET documents    |
  |        (highest penalty risk).                             |
  +────────────────────────────────────────────────────────────+
```

### 5.4 Calculator Result Annotations

Appear below calculator output when the AI has contextual notes.

```
Calculator Result:
  Employee CPF (20%): $1,000.00
  Employer CPF (17%): $850.00

  +────────────────────────────────────────────────────────────+
  | [mark] This employee crosses the OW ceiling ($6,800).      |
  |        Additional wages above this are not subject to      |
  |        CPF. [CPF Act s.7]                                  |
  +────────────────────────────────────────────────────────────+
```

- **Integration point**: Appended below the calculator result card
- **Content**: Contextual notes based on the calculation inputs + user's company profile
- **Citations**: Inline provision pills linking to relevant CPF Act sections
- **Dynamic**: Re-generates when calculator inputs change

### 5.5 Dashboard Briefing Card

The existing dashboard becomes a "living briefing" powered by the shadow agent.

**Current state** (what exists): Static metric cards + compliance preview + quick actions.

**Evolution**: A new `ShadowBriefingCard` replaces or augments the greeting section.

```
ShadowBriefingCard
  BriefingHeader
    TimeOfDayGreeting ("Good morning, Sarah")
    ShadowMark (12px, disclosure)
  BriefingPriorities
    PriorityItem (compliance gap — high risk)
    PriorityItem (CPF deadline — 14 days)
    PriorityItem (new regulatory change affecting your sector)
  BriefingQuickAction
    "Run compliance check" -> navigates to /compliance
  BriefingFooter
    LastUpdated timestamp
    "Updated throughout the day" label
```

**Visual treatment**:

- Uses `AppCard variant="elevated"` for prominence
- Top accent: `border-t-2 border-t-[var(--shadow-accent)]`
- Background: `var(--color-surface-card)` (standard, not tinted — this is a primary surface element)
- AI disclosure: Shadow mark + "AI Briefing" label in `text-micro`
- Priority items: Each has a `RiskTierBadge` (reuse existing component) + `text-body` description
- Layout: Replaces the `<h1>` greeting + subtitle section at the top of the dashboard
- Max width: Same as dashboard content (`max-w-4xl`)

**Time-of-day adaptation**:

- Morning (before 12pm): Shows priorities and upcoming deadlines
- Afternoon (12pm-5pm): Shows progress on today's items + new developments
- Evening (after 5pm): Shows summary of what changed today
- The content is generated server-side based on the user's company compliance status and activity patterns

### 5.6 Animation: Annotation Appearance

- **Entry**: `translateX(4px) -> translateX(0)` + `opacity 0 -> 1` over `200ms ease-out`
- **Background fade**: `var(--shadow-surface)` fades in over `300ms` (slightly slower than the text, creating a "filling in" effect)
- **Dismiss**: `opacity 1 -> 0` over `150ms ease-in`, then height collapses over `200ms`

**Reduced motion**:

- Instant appearance (no translate, no fade)
- Instant dismiss (no animation)

---

## 6. Employee Interface {#6-employee-interface}

When the authenticated user has the `employee` role (not `admin` or `owner`), the platform shows a simplified view.

### 6.1 Navigation Changes

The `NavigationSidebar` conditionally renders different nav items based on role.

**Admin navigation** (current, unchanged):

```
Core: Dashboard, Advisory, Compliance
Tools: Calculators, Documents
Management: Clients, Analytics
Bottom: Emergency, Settings, Help
```

**Employee navigation** (new):

```
Core: My Dashboard, Ask Arbor
My Work: My Leave, My Payslips
Info: Company Policies, My Terms
Bottom: Settings, Help
```

**Implementation**: The `NavigationSidebar` receives a `role` prop (or reads from `useAuth`). Two separate nav item arrays are defined:

```typescript
const employeeNavItems: NavItem[] = [
  { label: "My Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Ask Arbor", href: "/advisory", icon: MessageSquare },
];

const employeeWorkItems: NavItem[] = [
  { label: "My Leave", href: "/leave", icon: Calendar },
  { label: "My Payslips", href: "/payslips", icon: Receipt },
];

const employeeInfoItems: NavItem[] = [
  { label: "Company Policies", href: "/policies", icon: BookOpen },
  { label: "My Terms", href: "/terms", icon: FileText },
];
```

Icons: `LayoutDashboard`, `MessageSquare`, `Calendar`, `Receipt` (from lucide-react), `BookOpen`, `FileText`.

### 6.2 Employee Dashboard ("My Dashboard")

A simplified dashboard focused on the employee's personal information.

```
EmployeeDashboard
  EmployeeGreeting
    "Good morning, Sarah"
    ShadowBriefingCard (employee variant)
      "Your annual leave balance is 14 days. You've used 3."
      "Next payslip: 28 March 2026"
  EmployeeSummaryCards (grid: 2 columns on desktop, 1 on mobile)
    SummaryCard: Leave Balance
      14 days remaining
      "3 used, 0 pending"
    SummaryCard: Next Payslip
      "$4,200 (est.)"
      "28 March 2026"
  QuickLinks (grid: 2 columns)
    "Apply for leave" -> /leave/apply
    "View my payslips" -> /payslips
    "Ask a question" -> /advisory (or opens command surface)
    "Company policies" -> /policies
```

**Visual treatment**:

- Same `AppCard` variants as admin dashboard
- Same `max-w-4xl mx-auto` layout
- Same metric card pattern but with employee-specific data
- Shadow Briefing Card uses employee-scoped data (own leave, own terms, own payslips)

### 6.3 Shadow Agent Behavior Differences

| Behavior                 | Admin                                                           | Employee                                                        |
| ------------------------ | --------------------------------------------------------------- | --------------------------------------------------------------- |
| **Scope of knowledge**   | All company data, all employees, all compliance domains         | Own employment terms, own leave, own payslips, company policies |
| **Proactive surfacing**  | Compliance gaps, regulatory changes, deadline reminders         | Leave balance reminders, payslip availability, policy changes   |
| **Command capabilities** | All platform actions (calculators, compliance, documents, etc.) | View own data, ask HR questions, apply for leave                |
| **Inline annotations**   | On compliance page, calculators, dashboard                      | On My Terms page, leave page, payslip page                      |
| **Margin context dots**  | Company-wide observations                                       | Personal observations only                                      |
| **Advisory depth**       | Full KB access, multi-domain queries                            | Scoped to employee-relevant provisions                          |
| **Action trust levels**  | Can run compliance checks, generate documents, manage employees | Can apply for leave (propose), view data (autonomous)           |

### 6.4 Data Isolation

The shadow agent's backend enforces tenant isolation at the API level:

- Employee's advisory pipeline only receives context from their own employment record
- Employee's command surface capability registry excludes admin-only actions
- Employee's margin observations are scoped to their own data patterns
- The KB (Singapore employment law) is shared -- it is the same law for everyone

---

## 7. AppShell Integration {#7-appshell-integration}

### 7.1 Modified AppShell Structure

The `AppShell` component gains two new children: `ShadowMargin` and `ShadowWidget`.

```
AppShell (modified)
  NavigationSidebar (unchanged)
  MainArea
    TopBar (unchanged)
    MainContent
      <main>{children}</main>
    ShadowMargin (new — desktop only, right edge)
  ShadowWidget (new — fixed position, all viewports)
  CommandSurface (new — portal, rendered when open)
```

### 7.2 Component Props Flow

```typescript
interface AppShellProps {
  children: React.ReactNode;
}

// Internal state managed by AppShell:
// - sidebarCollapsed: boolean (existing)
// - mobileOpen: boolean (existing)
// - marginExpanded: boolean (new)
// - commandSurfaceOpen: boolean (new)
// - shadowAttention: boolean (new — agent has pending content)
// - shadowDegraded: boolean (new — AI backend unavailable)
```

### 7.3 State Management

The shadow agent's state is managed by a React context provider:

```typescript
interface ShadowAgentState {
  // Presence
  hasAttention: boolean; // Agent has content to surface
  attentionType: "insight" | "action" | "alert" | null;
  contextDots: ContextDot[]; // 0-5 observations
  pendingAction: ShadowAction | null;

  // UI state
  marginExpanded: boolean;
  commandOpen: boolean;

  // Agent status
  status: "active" | "degraded" | "offline";

  // User role
  role: "admin" | "employee";

  // Actions
  toggleMargin: () => void;
  openCommand: () => void;
  closeCommand: () => void;
  dismissDot: (id: string) => void;
  dismissAction: () => void;
}
```

This context is provided by a `<ShadowAgentProvider>` wrapping the AppShell's children. It manages:

1. Polling the shadow agent API for new observations (every 60s)
2. WebSocket/SSE connection for real-time margin updates
3. Keyboard shortcut registration (`Ctrl+Shift+A` for command, `Ctrl+Shift+I` for margin)
4. Graceful degradation when the AI backend is unavailable

### 7.4 Z-Index Layering

```
Layer                   z-index
─────────────────────────────────
Command Surface         50  (var(--z-shadow-command))
Shadow Widget           35  (var(--z-shadow-widget))
Shadow Margin           30  (var(--z-shadow-margin))
Mobile sidebar overlay  40  (existing)
Mobile sidebar          50  (existing)
Inline annotations      20  (var(--z-shadow-annotation))
Provision Viewer        50  (existing)
Toast notifications     60  (existing)
```

Note: The Command Surface shares z-index 50 with the mobile sidebar and Provision Viewer. These never coexist: the command surface closes before the provision viewer opens, and the mobile sidebar and command surface are mutually exclusive interactions.

---

## 8. Animation Specifications {#8-animation-specifications}

All animations consolidated with their reduced-motion fallbacks.

### 8.1 New Keyframes (added to globals.css)

```css
/* Shadow Widget — ambient pulse */
@keyframes shadowPulseAmbient {
  0%,
  100% {
    opacity: 0.3;
  }
  50% {
    opacity: 0.6;
  }
}

/* Shadow Widget — attention ripple */
@keyframes shadowAttentionRipple {
  0% {
    transform: scale(1);
    opacity: 0.3;
  }
  100% {
    transform: scale(2.2);
    opacity: 0;
  }
}

/* Shadow Margin — context dot entry */
@keyframes shadowDotEnter {
  0% {
    opacity: 0;
    transform: translateY(4px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Inline annotation — entry */
@keyframes shadowAnnotationEnter {
  0% {
    opacity: 0;
    transform: translateX(4px);
  }
  100% {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Command surface — panel entry */
@keyframes shadowCommandEnter {
  0% {
    opacity: 0;
    transform: translateY(-8px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Command surface — mobile panel entry */
@keyframes shadowCommandMobileEnter {
  0% {
    transform: translateY(100%);
  }
  100% {
    transform: translateY(0);
  }
}

/* Command surface — backdrop */
@keyframes shadowBackdropEnter {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}
```

### 8.2 Reduced Motion Override

The existing `globals.css` already has a comprehensive reduced-motion media query:

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This handles all shadow agent animations automatically. No additional reduced-motion rules are needed beyond the static visual fallbacks described in each component section (e.g., shadow-pulse attention uses a static `box-shadow` ring instead of the ripple animation).

### 8.3 Animation Duration Reference

| Animation                | Duration      | Easing      | Trigger                      |
| ------------------------ | ------------- | ----------- | ---------------------------- |
| Widget ambient pulse     | 3s (loop)     | ease-in-out | Always (resting state)       |
| Widget attention ripple  | 1.5s (single) | ease-out    | Every 5s when attention=true |
| Widget hover scale       | 200ms         | ease-out    | Mouse enter                  |
| Widget press scale       | 100ms         | ease-in     | Mouse down                   |
| Context dot entry        | 300ms         | ease-out    | New observation arrives      |
| Context dot fade (color) | 2s            | linear      | After dot entry              |
| Annotation entry         | 200ms         | ease-out    | Annotation mounted           |
| Annotation bg fill       | 300ms         | ease-out    | 100ms after entry            |
| Annotation dismiss       | 150ms         | ease-in     | User clicks dismiss          |
| Command backdrop         | 150ms         | ease-out    | Command surface opens        |
| Command panel (desktop)  | 200ms         | ease-out    | 50ms after backdrop          |
| Command panel (mobile)   | 250ms         | ease-out    | After backdrop               |
| Margin width change      | 250ms         | ease-in-out | Collapse/expand toggle       |
| Margin content fade      | 200ms         | ease-out    | 100ms after width starts     |
| Result stream            | Per token     | -           | SSE token events             |
| Action card entry        | 200ms         | ease-out    | Card mounted                 |

---

## 9. Responsive Behavior Matrix {#9-responsive-behavior-matrix}

### 9.1 Breakpoint Definitions

Using the existing breakpoints from the AppShell:

| Breakpoint   | Width          | Name       |
| ------------ | -------------- | ---------- |
| Mobile       | < 768px        | sm/default |
| Tablet       | 768px - 1023px | md         |
| Desktop      | >= 1024px      | lg         |
| Wide Desktop | >= 1280px      | xl         |

### 9.2 Component Behavior by Breakpoint

| Component              | Mobile (< 768px)                                   | Tablet (768-1023px)               | Desktop (>= 1024px)                                        |
| ---------------------- | -------------------------------------------------- | --------------------------------- | ---------------------------------------------------------- |
| **Shadow Widget**      | Fixed, bottom-right, 16px inset                    | Fixed, bottom-right, 24px inset   | In margin (bottom), or fixed bottom-right if margin hidden |
| **Command Surface**    | Bottom sheet, full width, 85vh                     | Floating panel, max-w-xl, mt-15vh | Floating panel, max-w-2xl, mt-15vh                         |
| **Margin (collapsed)** | Hidden                                             | Hidden                            | Visible, 48px                                              |
| **Margin (expanded)**  | Bottom sheet, 70vh                                 | Bottom sheet, 70vh                | Inline, 320px, pushes content                              |
| **Inline Annotations** | Full width, below parent                           | Full width, below parent          | Full width, below parent                                   |
| **Briefing Card**      | Full width, single column                          | Full width                        | Full width, max-w-4xl                                      |
| **Context Dots**       | Horizontal row above widget (attention state only) | Hidden (no margin)                | Vertical in margin                                         |
| **Keyboard shortcuts** | Disabled                                           | Active                            | Active                                                     |

### 9.3 Mobile-Specific Patterns

**Bottom Sheet Pattern** (reused for margin and command surface on mobile):

```
BottomSheet
  DragHandle (40px x 4px, centered, var(--color-gray-300))
  SheetContent
    [content varies by usage]
```

- Swipe down to dismiss (>100px gesture threshold)
- Backdrop click to dismiss
- `rounded-t-xl`
- `border-t border-[var(--color-gray-200)]`
- Spring physics on drag (overdamped, 200ms settle)

**Reduced motion on mobile**: Same rules as desktop. Swipe gesture remains functional (it is a user-initiated input, not a decorative animation).

---

## 10. Accessibility Requirements {#10-accessibility-requirements}

### 10.1 WCAG AA Compliance Checklist

| Requirement               | Implementation                                                                                                                                                                                                         |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Touch targets (44px)**  | Shadow Widget: 44px. All buttons: min-h-[44px] min-w-[44px]. Context dots: 44px touch area with 6px visual (padding-based).                                                                                            |
| **Focus indicators**      | All interactive elements use existing `focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]`.                                                                           |
| **Color contrast**        | All text meets 4.5:1 ratio. `var(--color-gray-700)` on `var(--shadow-surface)` = 5.2:1. `var(--color-gray-400)` on white = 3.1:1 (used only for decorative elements, never for essential information).                 |
| **Screen reader support** | Shadow Widget: `aria-label="Open Arbor assistant (Ctrl+Shift+A)"`. Command Surface: `role="dialog" aria-modal="true" aria-label="Arbor command palette"`. Margin: `role="complementary" aria-label="AI insights panel"`. |
| **Keyboard navigation**   | Full keyboard support for all interactions. `Ctrl+Shift+A` for command, `Ctrl+Shift+I` for margin, `Escape` to close overlays. Tab order follows visual order.                                                         |
| **Reduced motion**        | All animations respect `prefers-reduced-motion: reduce` via existing global CSS rule. Static fallbacks provide equivalent information.                                                                                 |
| **Text sizing**           | All text uses the existing `--text-size-multiplier` system. AI text uses the same type scale as platform text.                                                                                                         |
| **Live regions**          | New insights in margin: `aria-live="polite"`. Streaming results: `aria-live="polite" aria-atomic="false"`. Attention state change: `aria-live="polite"` announcement.                                                  |

### 10.2 ARIA Roles and Properties

**Shadow Widget**:

```html
<button
  type="button"
  aria-label="Open Arbor assistant (Ctrl+Shift+A)"
  aria-expanded="{commandOpen}"
  aria-haspopup="dialog"
></button>
```

When in attention state, add:

```html
aria-description="Arbor has new insights available"
```

**Command Surface**:

```html
<div role="dialog" aria-modal="true" aria-label="Arbor command palette">
  <input
    role="combobox"
    aria-expanded="{hasSuggestions}"
    aria-haspopup="listbox"
    aria-autocomplete="list"
    aria-controls="command-suggestions"
    aria-activedescendant="{selectedSuggestionId}"
    aria-label="Enter a command or question"
  />
  <ul id="command-suggestions" role="listbox">
    <li role="option" id="{id}" aria-selected="{selected}">...</li>
  </ul>
</div>
```

**Margin (expanded)**:

```html
<aside role="complementary" aria-label="AI insights panel">
  <section aria-label="Current insight">...</section>
  <section aria-label="Proposed actions">...</section>
  <section aria-label="Recent observations">...</section>
  <div role="search" aria-label="Quick command">
    <input aria-label="Enter a quick command" />
  </div>
</aside>
```

**Inline Annotations**:

```html
<div role="note" aria-label="AI insight" class="shadow-annotation">
  <button aria-label="Dismiss this insight" class="annotation-dismiss">
    <X />
  </button>
  <p>{annotation text}</p>
</div>
```

### 10.3 Screen Reader Announcements

| Event                         | Announcement                                            | Method                                   |
| ----------------------------- | ------------------------------------------------------- | ---------------------------------------- |
| New insight arrives in margin | "New AI insight available"                              | `aria-live="polite"` region              |
| Attention state activated     | "Arbor has new insights to share"                        | `aria-live="polite"` on widget           |
| Command surface opens         | Focus moves to input; dialog is announced automatically | `role="dialog"`                          |
| Result arrives                | "Result: {first 100 chars}"                             | `aria-live="polite"` on result container |
| Thinking step completes       | "{step text} complete"                                  | `aria-live="polite"`                     |
| Navigation confirmation       | "Navigating to {page name}"                             | `aria-live="assertive"`                  |
| Error state                   | "Arbor is temporarily unavailable"                       | `aria-live="polite"`                     |

### 10.4 Motion Sensitivity

Beyond `prefers-reduced-motion`, the design accommodates users who find ambient animations distracting:

- **Settings > Accessibility > Shadow Agent Animations**: Toggle to disable all shadow agent animations (independent of OS-level reduced motion)
- When disabled: Shadow pulse is a static dot (opacity 0.5), no attention ripple, no annotation slide-in, command surface appears instantly
- The attention state is communicated through a static visual change (box-shadow ring) rather than animation

---

## Component File Map

When implemented, these components should be organized as:

```
apps/web/src/components/
  shadow/
    ShadowWidget.tsx          — Entry point widget (Section 2)
    ShadowMark.tsx            — SVG icon component
    CommandSurface.tsx         — Command palette overlay (Section 3)
    CommandInput.tsx           — Command bar input
    CommandSuggestions.tsx     — Suggestion list with matching
    CommandResult.tsx          — Result rendering (text, calc, nav, action)
    CommandThinking.tsx        — Stream of thought display
    ShadowMargin.tsx          — Right-edge margin strip (Section 4)
    MarginCollapsed.tsx        — 48px collapsed state
    MarginExpanded.tsx         — 320px expanded state
    ShadowPulse.tsx           — Animated pulse dot
    ContextDot.tsx            — Single context observation dot
    InsightCard.tsx           — AI insight card for margin
    ActionCard.tsx            — Proposed action card
    MemoryThread.tsx          — Editable observation list
    ShadowAnnotation.tsx      — Generic inline annotation wrapper (Section 5)
    ShadowBriefingCard.tsx    — Dashboard briefing card
    BottomSheet.tsx           — Mobile bottom sheet pattern
    ShadowAgentProvider.tsx   — React context provider
    hooks/
      useShadowAgent.ts       — Context consumer hook
      useKeyboardShortcuts.ts — Global shortcut registration
      useShadowObserver.ts    — Client-side observation aggregation
      useBottomSheet.ts       — Bottom sheet gesture handling
    types.ts                  — TypeScript interfaces
    index.ts                  — Barrel exports
```

---

## What This Replaces

| Current Component                                  | Replaced By                             | Migration Path                                                                   |
| -------------------------------------------------- | --------------------------------------- | -------------------------------------------------------------------------------- |
| `AdvisoryFAB` (floating button on all pages)       | `ShadowWidget`                          | Remove FAB, mount ShadowWidget in AppShell                                       |
| `AskArborButton` (contextual entry points)          | `ShadowAnnotation` + inline annotations | Replace static buttons with dynamic annotations                                  |
| Quick Actions "Ask a question" button on dashboard | `ShadowBriefingCard` command entry      | Briefing card includes a command shortcut                                        |
| Advisory page chat-first layout                    | Unchanged                               | Advisory page remains for deep research; command surface handles quick questions |

---

## Design Decisions Log

| Decision                                | Choice                                       | Rationale                                                                                                   |
| --------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Shadow agent color from primary palette | `--color-primary` derivatives, not a new hue | Keeps AI presence within brand identity; avoids visual fragmentation                                        |
| No notification badge on widget         | Ripple animation only                        | Brief 04 explicitly states "not a notification badge -- a shift in ambient energy"                          |
| 44px widget with 36px visual            | Padding-based touch target                   | Meets WCAG 44px touch minimum while keeping the visual element subtle                                       |
| Command surface, not chat drawer        | Centered floating palette                    | Brief 04 mandate: "Not a chat drawer. A command palette."                                                   |
| Margin at 48px, not full sidebar        | Narrow strip                                 | Brief 04: "Not a sidebar -- a margin." Minimal screen real estate cost                                      |
| No margin on mobile                     | Bottom sheet alternative                     | 48px is too narrow to be useful on mobile; bottom sheet provides equivalent function                        |
| Same typography for AI text             | No italic, no special font                   | Reference architecture: "AI content uses the same type system as the platform. No italic. No special font." |
| Background tint, not colored text       | `var(--shadow-surface)`                      | Reference architecture: "AI content uses tinted backgrounds, not colored text."                             |
| Context dots max 5                      | Oldest fades out                             | Prevents margin clutter; forces prioritization by the agent                                                 |
| `Ctrl+Shift+A` shortcut                 | Not `Cmd+K` or `Ctrl+K`                      | Avoids conflict with browser search. Brief uses `Ctrl+Shift+A` as the example.                              |
| Employee nav items                      | Separate arrays, role-conditional            | Clean separation; no admin-only items leak to employee view                                                 |
