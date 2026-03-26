# Arbor: PACT-Governed AI HR Department for Singapore SMEs

## The Pivot

Arbor is NOT "HRIS with AI features." Every vendor is doing that. Arbor is **your AI HR department** — agent-filled roles governed by PACT so they can't exceed their authority.

## The Problem

Singapore has ~280,000 SMEs. 70% have fewer than 10 employees. They can't afford:

- HR Manager ($5-8K/month)
- Payroll Officer ($3-5K/month)
- Compliance specialist ($6-10K/month)

But they NEED these functions. Non-compliance with CPF, Employment Act, PDPA has real legal consequences. Today: the boss does everything, Ah Mei does 4 jobs, consultants charge $200-500 per engagement.

## The Solution

PACT enables Arbor to fill HR roles with AI agents. The D/T/R tree becomes the company's agent workforce plan:

```
D1-R1 (Boss) → HUMAN
  D1-R1-D1-R1 (HR Manager) → AGENT
    D1-R1-D1-R1-R2 (Payroll Officer) → AGENT
  D1-R1-D2-R1 (Operations Manager) → HUMAN + SHADOW
```

Each agent role has a PACT operating envelope set by the boss:

- What it CAN do (approve routine leave, calculate CPF, generate payslips)
- What it CANNOT do (terminate employees, submit to MOM, access medical records)
- When it must ASK (unusual leave patterns, salary changes, large claims)

## Ecosystem Position

| Platform  | Market                 | Opening                   | PACT Value                                 |
| --------- | ---------------------- | ------------------------- | ------------------------------------------ |
| Aegis     | Large MNCs             | Enterprise agent platform | Governs human+agent workforce at scale     |
| Astra     | Financial institutions | MAS compliance            | PACT = regulatory evidence                 |
| **Arbor** | **Singapore SMEs**     | **AI HR department**      | **Agent-filled roles at 3% of human cost** |

## What We Build (Following Astra's Pattern)

Domain configuration for HRIS, not governance engine code:

- SME org templates (micro/small/medium)
- 12 HRIS agent role definitions with capability specs
- HR data classification (all 77+ models, EATP levels)
- 12 envelope templates for Singapore HRIS roles
- Gradient calibration per HR module
- Cross-module bridge definitions
- Singapore regulatory mappings (EA, CPF, EFMA, PDPA, WFA, WSH)
- Acceptance tests for agent role-filling scenarios

## The Progressive Story

Week 1: Register, add employees → auto-generate org with vacant HR roles
Week 2: "Want me to handle leave approvals?" → first agent activated
Month 1: "Ready to generate payslips?" → payroll agent
Month 3: Recruitment, onboarding, compliance agents
Month 6: Full AI HR department. Boss reviews held actions. $200/month.

## Success Metric

A 10-person logistics company runs its entire HR function through Arbor agents. Boss spends 15 minutes/week on held actions. Agents handle the rest. Total cost: $200/month instead of $15-20K in HR staffing.
