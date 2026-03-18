---
name: sg-employment-law
description: "Singapore employment law reference for Arbor. Use when working on KB content, domain classification, provision accuracy, or regulatory compliance."
---

# Singapore Employment Law Reference

Quick reference for the six regulatory domains served by the Arbor platform.

## Domain Map

| Domain           | Legislation                         | KB Domain ID       | Default Risk |
| ---------------- | ----------------------------------- | ------------------ | ------------ |
| Employment Act   | Employment Act 1968 (Cap 91)        | `employment_act`   | GREEN        |
| CPF              | Central Provident Fund Act (Cap 36) | `cpf`              | GREEN        |
| Foreign Manpower | EFMA (Cap 91A)                      | `foreign_manpower` | AMBER        |
| Fair Employment  | TAFEP Guidelines + WFA              | `fair_employment`  | AMBER        |
| Workplace Safety | WSH Act (Cap 354A) + WICA           | `wsh`              | GREEN        |
| Tax              | Income Tax Act + IRAS guidelines    | `tax`              | GREEN        |

## Authority Levels

| Level            | Meaning                       | Legal Force                                   |
| ---------------- | ----------------------------- | --------------------------------------------- |
| `statutory`      | Primary legislation           | Legally binding, penalties for non-compliance |
| `subsidiary`     | Regulations under parent acts | Same force as statutes                        |
| `tripartite`     | TAFEP/Tripartite guidelines   | Not binding but MOM monitors compliance       |
| `administrative` | MOM/CPF Board circulars       | Operational guidance                          |
| `best_practice`  | Industry standards            | Recommended, not required                     |

## Key Cross-Domain Interactions

**Termination**: EA (notice) + CPF (final contributions) + IRAS (tax clearance IR21)

**Foreign Hiring**: EFMA (pass) + CPF (no contributions for WP/S Pass) + EA (same protections)

**Retrenchment**: EA (benefits) + TAFEP (fair selection) + MOM (notification for 10+)

**Maternity**: EA (leave entitlement) + CPF (contributions during leave) + IRAS (government-paid portion)

## Escalation Triggers (RED Risk Tier)

These query patterns MUST trigger RED escalation in `src/hr_advisory/workflows/guardrails.py`:

- `tadm\s+claim` — TADM claim
- `wrongful\s+dismissal` — Wrongful dismissal
- `unfair\s+dismissal` — Unfair dismissal
- `mediation\s+claim` — Mediation claim
- `ect\s+claim` — ECT claim
- Criminal matters (theft, fraud, assault)
- Active discrimination complaints

## Part IV Coverage (Employment Act)

Part IV (rest days, hours, overtime) applies to:

- **Workmen** earning up to $4,500/month
- **Non-workmen** earning up to $2,600/month

Part IV employees get overtime at 1.5x hourly rate, capped at salary thresholds.

## Implementation Files

- `src/hr_advisory/kb/` — Provision content and loaders
- `src/hr_advisory/workflows/classification/` — Domain detection
- `src/hr_advisory/workflows/guardrails.py` — Escalation patterns
- `src/hr_advisory/models/` — Act, Domain, Provision, CrossReference models
- `docs/01-architecture.md` — Full domain and KB documentation

## Consult Agent

For deep domain questions: `sg-employment-law-expert`
