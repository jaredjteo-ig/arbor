# Ricoh Thailand Context & Demo Strategy

**Date**: 2026-03-24

---

## Ricoh Thailand Profile

### Company Context

- **Parent**: Ricoh Company, Ltd. (Japan) — Fortune Global 500, ~80,000 employees worldwide
- **Business**: Office imaging, IT services, digital workplace solutions, production printing
- **Thailand presence**: Ricoh (Thailand) Ltd — office equipment sales, leasing, service, and IT solutions
- **Workforce**: Estimated 500-2,000 employees in Thailand (sales, service engineers, back-office, management)
- **Structure**: Japanese MNC subsidiary — Thai local staff + Japanese expats, dual reporting culture

### HR Challenges for a Company Like Ricoh Thailand

1. **Bilingual compliance** — Thai labour law + Japanese parent company HR policies that may conflict
2. **Complex workforce mix** — Thai nationals, Japanese expats (work permits), possibly other ASEAN nationals
3. **Service engineer workforce** — Large field workforce with attendance, overtime, shift management needs
4. **Regulatory complexity** — Thai Social Security Fund, personal income tax withholding, Labour Protection Act
5. **Japanese-style HR** — Seniority-based progression, consensus decision-making, extensive documentation requirements
6. **Scaling challenge** — Thailand is often a hub for ASEAN regional operations; HR practices need to scale across countries

### What Would Impress a Ricoh Thailand Executive

1. **AI that understands local labour law** — Not generic ChatGPT, but something that knows the specific provisions
2. **Reduced dependency on expensive HR consultants** — Real cost savings
3. **Compliance confidence** — "Can we trust this?" → Trust lineage and citations answer this
4. **Speed to value** — "How quickly can this be set up for our company?"
5. **Integration potential** — Can it work with their existing systems (SAP, local payroll)?
6. **Multi-country potential** — "If it works for Thailand, can it work for our Vietnam/Indonesia offices?"

---

## Demo Strategy: "The Art of the Possible"

### Narrative Frame

**Don't demo "Arbor for Singapore."** Demo **"what an AI HR copilot looks like"** using Singapore as the proof-of-concept that demonstrates the architecture works.

The story: _"We've built a complete, production-grade AI HR platform. The Singapore version is live and running. The architecture is designed to be jurisdiction-adaptable. Here's what it looks like in action — and here's what it would look like for Thailand."_

### Demo Script (Recommended 45-minute flow)

#### Act 1: The Problem (5 min)

- HR compliance is complex, jurisdiction-specific, and constantly changing
- SMEs and subsidiaries can't afford dedicated compliance teams
- Generic AI (ChatGPT) gives dangerously unreliable employment law answers
- Show an example of ChatGPT giving wrong Singapore employment law advice vs. Arbor giving correct, cited advice

#### Act 2: The Platform (15 min)

Walk through the live production system at `arbor.terrene.foundation`:

1. **Login & Onboarding** — Show the 4-step company setup, how the platform immediately personalizes
2. **Dashboard** — Quick actions, compliance overview, AI-powered advisory access
3. **Advisory Chat** — Ask a real Singapore employment law question live:
   - "What is the minimum notice period for terminating an employee who has worked for 3 years?"
   - Watch SSE streaming, citations appearing, risk tier indicator
   - Show the escalation flow for edge cases
4. **Calculators** — Run a CPF calculation, show how results feed into advisory context
5. **Payroll** — Show the payroll run flow (gross-to-net with statutory deductions)

#### Act 3: The Intelligence Layer (10 min)

6. **Shadow Agent** — Show how AI is embedded in every page, not just the chat:
   - Margin indicators
   - Proactive briefing cards
   - Command surface for quick actions
7. **Trust & Safety** — Show the 13-step safety chain diagram, explain EATP trust lineage
8. **Admin/QA** — Show the admin dashboard with quality metrics, KB management

#### Act 4: The Thailand Story (10 min)

9. **Architecture diagram** — Show the modular design:
   - Regulatory KB is a pluggable layer (swap Singapore law for Thai law)
   - Specialist agents are configurable (swap CPF specialist for SSF specialist)
   - Calculators are modular (swap CPF calculations for Thai SSF calculations)
   - HRIS features (payroll, leave, attendance) are universal
10. **Timeline estimate** — "With the architecture proven, a Thailand adaptation takes X, not Y"
11. **Multi-country vision** — "Build once, adapt per jurisdiction. Thailand, Vietnam, Indonesia..."

#### Act 5: Discussion (5 min)

- What resonated?
- What would their Thai HR team need most?
- Integration questions

---

## What to AVOID in the Demo

| Avoid                                          | Why                                            |
| ---------------------------------------------- | ---------------------------------------------- |
| Claiming Thai law expertise                    | The KB doesn't have it yet — don't oversell    |
| Deep-diving into Singapore-specific provisions | Ricoh doesn't care about Singapore CPF rates   |
| Showing empty/seed-data modules                | Some modules may look sparse without demo data |
| Technical architecture deep-dives              | Focus on outcomes, not how it's built          |
| Showing the 115 pre-existing test failures     | Not relevant to demo                           |
| Comparing to specific competitors by name      | Let the product speak                          |

---

## Key Selling Points for Ricoh Thailand

### 1. "AI That Knows Your Law" (not generic AI)

Unlike ChatGPT/Copilot which gives generic answers, Arbor's advisory engine is grounded in actual legal provisions with citations. Every answer can be traced to a specific section of law. This matters because wrong HR advice has real legal consequences.

### 2. "Free HRIS + Paid Intelligence" (cost story)

The full HRIS is free. The AI advisory layer is the premium value. For a Ricoh Thailand subsidiary, this means replacing their current HRIS cost ($4-10/employee/month) with a free platform that also happens to have AI intelligence built in.

### 3. "Trust You Can Prove" (enterprise governance)

EATP trust lineage means every AI advisory response has a cryptographic audit trail. For a Japanese MNC with strict compliance culture, this is a differentiator — the AI's reasoning and sources are auditable.

### 4. "Scales Across ASEAN" (regional play)

Build the platform for Thailand, adapt it for Vietnam, Indonesia, Philippines. The architecture supports multi-jurisdiction deployment. This makes it a regional strategy, not a single-country tool.

### 5. "Built in Weeks, Not Years" (speed story)

121 milestones completed, 89K lines of production code, live in production — built with the COC methodology. This demonstrates that adapting it for Thailand wouldn't take years.
