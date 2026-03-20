# Arbor: The Intelligence Layer

Arbor is not a chatbot. Arbor is not a sidebar you open to "ask the AI." Arbor IS the intelligence that makes an HRIS useful.

Without Arbor, this is a database with forms. With Arbor, it's an HR operations partner that works alongside you.

## The Five Layers of Arbor

### 1. The Ambient Layer — Arbor is always present

Arbor exists as a persistent awareness across every page. Not a chat bubble. A layer — like having an experienced HR manager looking over your shoulder.

- On the **Employees** page, Arbor highlights: "3 work passes expiring within 30 days" with a soft glow on the affected rows
- On the **Payroll** page: "CPF submission deadline in 5 days. March payroll not yet finalized."
- On the **Leave** page: "12 pending leave requests. 3 overlap with the same department."
- On a **Person Detail** page: "This employee's probation ends in 2 weeks. Confirmation letter not generated."

These aren't notifications. They're Arbor's awareness — ambient, contextual, alive.

### 2. The Action Layer — Arbor executes, not advises

When you're looking at a pending leave request, Arbor doesn't say "you can approve it by clicking the approve button." Arbor shows an action strip: **"Approve Sarah's annual leave (3 days, 24-26 Mar)? No conflicts found."** One click. Done.

When you say "onboard John, $5000 salary, starts Monday" — Arbor creates the employee record, generates the KET, assigns default leave balances, sets up payroll, and sends the welcome email. You watch each step complete. You can interrupt at any point.

**PACE Loop** (Preview → Approve → Confirm → Exit):

- **Preview**: Arbor shows what it will do before doing it
- **Approve**: You confirm or modify
- **Confirm**: Arbor executes, shows results
- **Exit**: Undo available for 8 seconds after any action

### 3. The Navigation Layer — Arbor drives the UI

Arbor doesn't return text responses to navigation questions. When you ask "show me employees with expiring work passes," Arbor:

1. Navigates to `/employees`
2. Applies the "work pass expiring" filter
3. Sorts by expiry date
4. Highlights the first result

You watch the interface respond as if your hands were on the keyboard. Arbor IS the user.

### 4. The Memory Layer — Arbor learns you

Not chat logs. Distilled intelligence:

- **Themes**: "You've been focused on payroll setup this week — 8 actions across pay items, schemes, and adhoc runs"
- **Actions taken**: "You onboarded 3 employees, ran 2 payroll previews, approved 15 leave requests"
- **Open threads**: "March payroll is in draft — not yet approved (2 days)"
- **Behavioral patterns**: "You always check attendance before running payroll — should I auto-show attendance summary when you start a payroll run?"

These are shown as Arbor's understanding of you — a living profile that evolves.

### 5. The Proactive Layer — Arbor acts before you ask

Small, contextual nudges that slide in from the edge:

- "CPF submission deadline is Friday. March payroll hasn't been finalized yet."
- "3 employees completed probation this month. Confirmation letters pending."
- "Sarah's maternity leave starts next week — have you assigned cover?"
- "New MOM advisory published: Changes to foreign worker levy rates effective April 1."

Not intrusive. Dismissible. But valuable.

## What the User Experiences

### Morning Login

The dashboard doesn't show generic charts. It shows **Arbor's briefing** — personalized, contextual, actionable:

> "Good morning. Here's what needs attention today:
>
> - **Payroll**: March run is ready for review. $42,580 gross, 12 employees. [Review →]
> - **Leave**: 5 pending requests (2 urgent — overlap with project deadline). [Review →]
> - **Compliance**: Work pass for Ahmad (WP) expires in 14 days. [Renew →]
> - **Reminder**: IR8A filing deadline in 3 weeks. 2 employees missing data. [Complete →]"

### Working on Employees Page

Arbor's ambient strip on the right shows soft contextual dots. Hover: "Ahmad's S Pass quota check shows your company is at 95% of the services sector cap." The dots update as you browse.

### Command Palette (Ctrl+Shift+A)

You type in natural language. The response isn't text — it's action:

- "Run payroll for March" → Arbor shows the payroll preview → You approve → Payroll runs → Payslips generated
- "How many days of leave does Sarah have?" → Arbor queries, shows: "Sarah: 8 days annual, 14 days sick remaining"
- "Generate KETs for all new employees" → Arbor identifies 3 employees without KETs → Generates each → Shows completion

### Arbor Overlay Mode

When executing a multi-step workflow, the main UI dims slightly and Arbor's actions are highlighted with a teal trace (Arbor's identity color). You see it navigate pages, fill forms, select options. You can interrupt at any point.

## Arbor's Identity

When Arbor surfaces information, users know it's Arbor:

- **"Arbor:"** prefix on all insights and suggestions
- **Teal accent** (#0D6E4F — Arbor's secondary color) on all Arbor-generated UI elements
- **Leaf icon** (🌿) as Arbor's mark — small, consistent, recognizable
- **Consistent voice**: professional, clear, action-oriented — never verbose, never uncertain about facts

## Arbor's Trust Envelope

Arbor operates with the **same permissions as the user**. JWT token forwarded. If you're an employee (not admin), Arbor can only do what you can do.

### Trust Levels (per action type)

| Action                          | Trust Level                     | Behavior                             |
| ------------------------------- | ------------------------------- | ------------------------------------ |
| Read data                       | Autonomous                      | Execute immediately, show result     |
| Navigate                        | Autonomous                      | Drive UI directly                    |
| Calculate                       | Autonomous                      | Show result with breakdown           |
| Create record                   | Propose (preview)               | Show PACE preview, wait for approval |
| Update record                   | Propose (preview)               | Show what changes, wait for approval |
| Delete record                   | Always propose                  | Preview + 5-second cooldown          |
| Government submission           | Always propose + double confirm | Two-step approval gate               |
| Financial action (GIRO, payout) | Always propose + double confirm | Two-step with amount verification    |

## Architecture for Productization

The Arbor shadow agent is designed for extraction into kailash-py/kailash-rs:

**80% reusable (framework)**:

- Intent classification pipeline (module + action + entities)
- PACE loop (Preview → Approve → Confirm → Exit)
- Tool registry (maps intents to API calls)
- Memory distillation (observation → preferences → themes)
- Proactive observation engine (deadline tracking, anomaly detection)
- Session tracking (page views, interactions, intent inference)
- Ambient annotation system (contextual dots, inline insights)

**15% configurable (domain adapters)**:

- Module definitions (what modules exist and what they do)
- Tool mappings (which API endpoints map to which intents)
- Observation rules (what constitutes a "deadline" or "anomaly")
- Briefing templates (morning briefing structure)

**5% custom (per deployment)**:

- Branding (Arbor vs Iris vs custom name)
- Domain-specific prompts (Singapore HR law vs impact investing vs anything)
- Trust level overrides (per-organization security policies)
