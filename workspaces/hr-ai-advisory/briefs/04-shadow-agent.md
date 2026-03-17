# Brief 04: Shadow Agent — The Omnipresent AI Interface

## Vision

Replace the floating chatbot ("Ask AITE") with a shadow agent — an AI presence that permeates every feature, learns from every interaction, and acts as each user's always-available institutional memory and platform operator. Not a chatbot bolted onto a tool. The intelligence layer of the platform itself.

This is the defining product differentiator. Every HR SaaS competitor (Payboy, Talenox, HReasily) is a forms-and-tables tool. AITE with a shadow agent is a tool that thinks alongside you.

## Reference Architecture

The shadow agent design follows the CO (Cognitive Orchestration) five-layer architecture and adapts the presence model from Impact-Verse's shadow agent blueprint (`/Users/esperie/repos/tpc/impact-verse/workspaces/network-intel/01-analysis/08-product-evolution/08-shadow-agent-design.md`).

---

## Part 1: Why Not a Chat Interface

The current "Ask AITE" floating button opens a slide-out drawer. This is a chatbot — the same pattern as every competitor's AI bolt-on. Three problems:

1. **Chat is a mode switch.** Opening a drawer is a context switch. The user leaves what they're doing and enters "AI conversation mode." Then they describe in words what they were looking at. This is friction, not assistance.

2. **Chat creates a second interface.** The drawer becomes a parallel universe. Compliance data exists on the left, the AI response exists on the right. The user becomes a translator between two systems that should be one.

3. **Chat is pull-only until it becomes annoying.** Chat AI waits until summoned. The alternative is proactive notifications, which degrade into noise. There's no graceful middle ground in a chat paradigm.

---

## Part 2: Four Presence Layers

The shadow agent manifests through four layers, each with increasing visibility:

### Layer A: The Substrate (Always Active, Never Visible)

Continuously observes and processes in background. No visual representation.

**What it observes:**

- Which regulations the user asks about and how often
- Which calculators they use and with what parameters
- Which compliance gaps they revisit vs ignore
- Time patterns (compliance checks on Mondays, CPF calculations at month-end)
- Intent signals (viewing 3 emergency guides = probable crisis situation)

**What it does NOT do:**

- Record keystrokes or form field content before submission
- Store raw behavioral data — only extracted intent patterns
- Track anything for any purpose other than improving the user's experience

**Privacy contract:** "AITE learns your work patterns to provide better assistance. All learned preferences are visible in Settings > AI Memory and can be edited or deleted at any time."

### Layer B: The Margin (Persistent, Peripheral)

A narrow strip along the right edge of every page. Not a sidebar — a margin.

**Collapsed state (48px):**

- **Shadow pulse** (top): Subtle breathing glow indicating the agent is active. Brightens when the agent has something to surface. Not a notification badge — a shift in ambient energy.
- **Context thread** (middle): Small dots representing recent observations. Maximum 5. Hover shows one-line tooltip: "Your KET compliance gap is still open" or "CPF rates updated for 2026 — affects 3 employees."
- **Action seed** (bottom): When the agent has a proposed action, a single icon appears. Calculator icon for a calculation. Shield icon for a compliance alert. Document icon for a template suggestion. No badge count. Just the icon.

**Expanded state (320px, triggered by clicking margin or keyboard shortcut):**
Not a chat interface. A contextual card stack:

- **Top card**: Most relevant insight ("You have 2 compliance gaps that could result in fines up to $10,000")
- **Action cards**: Proposed actions with one-click approval
- **Memory thread**: Recent observations, editable
- **Quick command bar**: Single-line input for direct instructions

### Layer C: Inline Annotations (Contextual, Embedded)

The shadow agent annotates the existing interface rather than creating its own:

**On the Compliance page:**

- Risk annotations on checklist items: "Mandatory — fine up to $5,000 per offence (EA s95A)"
- Progress indicators: "3 of 8 items compliant. Priority: KET documents (highest penalty)."

**On Calculator results:**

- Contextual notes: "Note: this employee crosses the OW ceiling ($8,000). Additional wages above this are not subject to CPF."
- Cross-references: "Based on 2026 rates. PR Year 1 graduated rates apply for the first year."

**On the Dashboard:**

- Living briefing card: Morning shows priorities. Updates throughout the day. "2 compliance items need attention. CPF deadline is end of month."

**On Emergency guides:**

- Sector-specific annotations: "Your sector (Technology) has a 15% MOM inspection rate. Priority: WSH documentation."

### Layer D: The Command Surface (On Demand, Overlay)

Not a chat drawer. A command palette — like Cmd+K search, but for AI interaction.

**Entry point — The Shadow Widget:**
A small, unobtrusive widget at the bottom-right of every page. Not the current floating chat button — a minimal animated element:

- **Resting state**: A subtle 36px circle with the shadow mark icon, semi-transparent (`opacity: 0.6`), with a slow breathing animation (2s pulse cycle). Positioned in the margin area if the margin is visible, or bottom-right corner if not.
- **Hover state**: Circle solidifies (`opacity: 1.0`), slight scale up, tooltip shows "Ask AITE (Ctrl+Shift+A)".
- **Attention state**: When the agent has something to surface, a gentle ripple emanates from the widget once every 5 seconds (not continuously — not a notification). The ripple uses `--color-primary` at low opacity.
- **Click or keyboard shortcut**: Opens the command surface.

**Command surface appearance:**
A centered, floating command bar at the top third of the screen. Overlays content with subtle backdrop dim. Not a modal dialog — a command palette.

```
+--------------------------------------------+
|                                            |
|   +------------------------------------+   |
|   | > What notice period for 3 years?  |   |  <- Command bar
|   +------------------------------------+   |
|   | Recent commands                     |   |
|   | - Calculate CPF for $5,000 salary   |   |  <- Suggestion list
|   | - Check my compliance status        |   |
|   | - Show me the TADM emergency guide  |   |
|   +------------------------------------+   |
|                                            |
|        (dimmed main content below)         |
+--------------------------------------------+
```

**Behaviour:**

- Natural language input. As user types, matched capabilities appear below.
- Results render inline with rich formatting — tables, calculations, provision cards.
- User can pin any result to the margin for persistent reference.
- Escape dismisses. Transient by design — no conversation history visible.
- The agent uses session context to interpret commands, but the interface doesn't create the illusion of a conversation.

**Why not chat:** No conversation history visible. No thread. No "AI said / I said" alternation. Each invocation is a fresh command, like a search query. Stateless in presentation, contextful in intelligence.

---

## Part 3: Action Model

### Action Categories and Trust Levels

| Action Type                             | Default Trust     | Can User Upgrade?    | Preview Required?   |
| --------------------------------------- | ----------------- | -------------------- | ------------------- |
| Information retrieval (KB lookup)       | Autonomous        | —                    | No                  |
| Analysis (compliance check, calculator) | Autonomous        | —                    | No (results inline) |
| Navigate to page                        | Autonomous        | —                    | No                  |
| Generate document draft                 | Propose & preview | Yes (opt-in)         | Yes by default      |
| Submit escalation to specialist         | Always propose    | Cannot be autonomous | Yes, always         |
| Modify company profile                  | Always propose    | Cannot be autonomous | Yes, always         |
| Delete data                             | Always propose    | Cannot be autonomous | Yes, always         |
| Bulk actions                            | Always propose    | Cannot be autonomous | Yes, always         |

**Hard guardrails (server-side, non-negotiable):**

- Shadow agent can draft but never send/submit without explicit confirmation
- Shadow agent can calculate but never modify employee records without confirmation
- Shadow agent ALWAYS runs the 13-step safety chain for any regulatory advisory
- Shadow agent ALWAYS cites provisions — no regulatory statement without a source

### Platform Action Registry

Every action the shadow agent can take, mapped to platform features:

| Command Pattern                              | Action                               | Target Page            |
| -------------------------------------------- | ------------------------------------ | ---------------------- |
| "Calculate CPF for [salary] [age]"           | Runs CPF calculator                  | /calculators           |
| "What's my compliance status?"               | Runs compliance self-assessment      | /compliance            |
| "Show me the [topic] emergency guide"        | Navigates to emergency guide         | /emergency             |
| "What notice period for [years] of service?" | KB lookup + EA s.10 citation         | Advisory               |
| "Generate a KET document"                    | Opens document generator             | /documents             |
| "Am I compliant with [regulation]?"          | Compliance check for specific domain | /compliance            |
| "How many foreign workers can I hire?"       | Quota calculator                     | /calculators           |
| "What are the CPF rates for 2026?"           | KB lookup + CPF rate table           | Advisory               |
| "Take me to [page]"                          | Navigation                           | Any page               |
| "What should I do about [emergency]?"        | Emergency guide + escalation offer   | /emergency             |
| "Help me onboard a new employee"             | Guided onboarding workflow           | /onboarding (employee) |
| "Show me my employee list"                   | Navigate to employee management      | /employees             |

---

## Part 4: Multi-Tenant Enterprise Model

### The Payboy Paradigm

AITE evolves from "HR advisory tool for the owner" to "HR platform for the enterprise." This means:

**Two user types, one platform, same shadow agent:**

| Role                 | What They Do                                                                                             | Shadow Agent Behaviour                                                                                                                                                                      |
| -------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Admin/HR Manager** | Company setup, compliance management, employee onboarding, policy management, advisory queries           | Full platform access. Shadow agent knows company profile, compliance status, all employee data. Proactively surfaces compliance gaps, deadline reminders, regulatory changes.               |
| **Employee**         | View own employment terms, check leave balance, access company policies, ask HR questions, view payslips | Limited access. Shadow agent knows the employee's specific terms, leave balance, applicable regulations. Answers questions about their employment rights. Cannot see other employees' data. |

### Enterprise Onboarding Flow

1. **First user registers** → becomes company admin (owner)
2. **Admin sets up company profile** → sector, headcount, foreign workers
3. **Admin invites employees** → email invitations with role assignment
4. **Employee registers** → sees their personalised dashboard with employment terms, leave balance, company policies
5. **Shadow agent adapts** → Admin's shadow agent knows the whole company. Employee's shadow agent knows only their own data.

### Employee Interface (New)

A simplified view of the platform for employees:

| Page                 | Purpose                                              | Shadow Agent Role                                                |
| -------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| **My Dashboard**     | Employment summary, leave balance, next payslip date | "Your annual leave balance is 14 days. You've used 3."           |
| **My Terms**         | KETs, employment contract summary, notice period     | "Your notice period is 2 weeks (contract clause 5.2)."           |
| **My Leave**         | Apply for leave, view history, check entitlements    | "You have 11 days remaining. Public holidays: 4 more this year." |
| **My Payslips**      | View itemised payslips, CPF breakdown                | "Your CPF this month: employer $765, employee $900."             |
| **Company Policies** | View company handbook, safety policies, FWA policy   | "Your company offers 3 days WFH per week under the FWA policy."  |
| **Ask AITE**         | Shadow agent command surface                         | "What's my sick leave entitlement?" → instant cited answer       |

### Tenant Isolation

- Company data is strictly isolated — Company A cannot see Company B's data
- Within a company, role-based access: admin sees all, employee sees only own
- Shadow agent respects these boundaries — employee's agent cannot access other employees' data
- KB (Singapore employment law) is shared across all tenants — it's the same law

---

## Part 5: Advisory Page Evolution

The current Advisory page (`/advisory`) becomes the **deep workspace** — the full-screen view for extended multi-turn research conversations. Same shadow agent, different presentation:

| Feature         | Command Surface (Layer D)           | Advisory Deep Workspace                                       |
| --------------- | ----------------------------------- | ------------------------------------------------------------- |
| **Purpose**     | Quick questions and actions         | Extended research and investigation                           |
| **Persistence** | Transient — Escape to dismiss       | Persistent — full conversation history                        |
| **History**     | No visible thread                   | Full conversation sidebar with search, rename, delete, export |
| **Citations**   | Inline provision pills              | Full ProvisionViewer modal with formal text                   |
| **Escalation**  | "Connect to specialist" action card | Full EscalationDialog with details form                       |
| **Entry point** | Shadow widget or Ctrl+Shift+A       | Sidebar "Advisory" link                                       |

Both use the same backend advisory pipeline, same safety chain, same KB, same trust chain.

---

## Part 6: CO Five-Layer Mapping

| CO Layer             | AITE Shadow Agent Implementation                                                                                                                                                                                        |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **L1: Intent**       | Supervisor agent routes to: Search Agent (KB lookup), Calculator Agent (deterministic calculations), Compliance Agent (gap analysis), Action Agent (navigate, generate, escalate), Advisory Agent (multi-turn research) |
| **L2: Context**      | User's company profile + compliance status + employee data + conversation history + learned preferences injected into every interaction                                                                                 |
| **L3: Guardrails**   | 13-step safety chain on every advisory query + action trust levels + hard guardrails on data modification + anti-amnesia constraint injection                                                                           |
| **L4: Instructions** | Action Plan pattern — every significant action shows preview → approve/adjust/cancel. Phase-level gates for multi-step workflows (employee onboarding, document generation).                                            |
| **L5: Learning**     | Session observation → preference distillation → user-governed memory. Weekly digest. Institutional knowledge (company-level defaults) proposed to admin for approval.                                                   |

---

## Part 7: What This Replaces

| Current Feature                         | Becomes                                                                     |
| --------------------------------------- | --------------------------------------------------------------------------- |
| Ask AITE floating button + drawer panel | Shadow widget + command surface (Layer D)                                   |
| Ask AITE conversation in panel          | Command surface for quick queries; Advisory page for deep research          |
| AdvisoryFAB on every page               | Shadow widget (unobtrusive, animated, always present)                       |
| AskAITEButton (contextual entry points) | Inline annotations (Layer C) with one-click actions                         |
| Advisory page                           | Advisory deep workspace (same page, enhanced with shadow agent integration) |

---

## Constraints

- **Must work on mobile** — margin collapses to bottom sheet, command surface becomes full-screen overlay
- **Must respect prefers-reduced-motion** — all animations have static fallbacks
- **Must maintain WCAG AA** — all interactive elements meet 44px touch targets
- **Must not break existing features** — shadow agent is additive, not destructive
- **Must maintain 13-step safety chain** — no shortcuts on regulatory advisory
- **Must cite provisions** — every regulatory statement links to a source
- **OpenAI API key must be valid** — shadow agent quality depends on LLM availability; graceful degradation to KB-only when unavailable

---

## Success Criteria

1. A new user can ask "What notice period must I give?" from any page and get a cited answer in under 3 seconds
2. An admin can say "Onboard a new employee" and be guided through the complete workflow
3. An employee can ask "How many leave days do I have left?" and get their exact balance
4. The shadow agent proactively surfaces "Your KET compliance gap has been open for 30 days — fine risk increasing" without being asked
5. An enterprise buyer sees a fundamentally different product from Payboy/Talenox — not a better form, but a platform that thinks
