# Multi-Jurisdiction Architecture Diagram

**Purpose**: Visual aid for Act 4 of the Ricoh Thailand demo — showing that the platform architecture is jurisdiction-agnostic and Thailand adaptation is a content exercise, not a rebuild.

---

## Architecture Overview

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        ARBOR HR PLATFORM ARCHITECTURE                       ║
║                     Jurisdiction-Pluggable Design                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 5: TRUST & SAFETY (UNIVERSAL — same for every jurisdiction)        │
│                                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  EATP Trust  │  │  13-Step     │  │  PACE        │  │  Risk Tier   │  │
│   │  Lineage     │  │  Safety      │  │  Safety      │  │  System      │  │
│   │              │  │  Chain       │  │  Model       │  │              │  │
│   │ Cryptographic│  │              │  │ Preview →    │  │ GREEN        │  │
│   │ audit trail  │  │ Every query  │  │ Approve →    │  │ AMBER        │  │
│   │ for every    │  │ validated,   │  │ Confirm →    │  │ RED          │  │
│   │ AI response  │  │ screened,    │  │ Exit         │  │              │  │
│   │              │  │ cited        │  │              │  │ Escalation   │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│   Transfers to any jurisdiction with ZERO changes                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 4: AI ADVISORY ENGINE (configurable per jurisdiction)              │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    SPECIALIST AGENTS                                │  │
│   │                                                                     │  │
│   │   ┌─────────────────────────── SINGAPORE (LIVE) ─────────────────┐ │  │
│   │   │ ████████████  ████████████  ████████████  ████████████       │ │  │
│   │   │ Employment    CPF           Foreign       Fair               │ │  │
│   │   │ Act           Act           Manpower      Employment         │ │  │
│   │   │ ████████████  ████████████  ████████████  ████████████       │ │  │
│   │   │ Workplace     Tax/IRAS                                       │ │  │
│   │   │ Safety                                                       │ │  │
│   │   └──────────────────────────────────────────────────────────────┘ │  │
│   │                                                                     │  │
│   │   ┌─────────────────────────── THAILAND (READY TO LOAD) ─────────┐ │  │
│   │   │ ░░░░░░░░░░░░  ░░░░░░░░░░░░  ░░░░░░░░░░░░  ░░░░░░░░░░░░    │ │  │
│   │   │ Labour        Social        Revenue       Foreign            │ │  │
│   │   │ Protection    Security      Code          Employment         │ │  │
│   │   │ ░░░░░░░░░░░░  ░░░░░░░░░░░░  ░░░░░░░░░░░░  ░░░░░░░░░░░░    │ │  │
│   │   │ Labour        Occupational                                   │ │  │
│   │   │ Relations     Safety                                         │ │  │
│   │   └──────────────────────────────────────────────────────────────┘ │  │
│   │                                                                     │  │
│   │   ┌── MALAYSIA ──┐ ┌── VIETNAM ──┐ ┌── INDONESIA ┐ ┌── PH ──────┐ │  │
│   │   │ ░░░░░░░░░░░░ │ │ ░░░░░░░░░░ │ │ ░░░░░░░░░░░ │ │ ░░░░░░░░░ │ │  │
│   │   │ EA 1955      │ │ Labour     │ │ Omnibus     │ │ Labour    │ │  │
│   │   │ EPF/SOCSO    │ │ Code 2019  │ │ Law         │ │ Code      │ │  │
│   │   │ EIS          │ │ SI/SHI     │ │ BPJS        │ │ SSS       │ │  │
│   │   └──────────────┘ └────────────┘ └─────────────┘ └───────────┘ │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   ████ = Built and running       ░░░░ = Architecture ready, content needed │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 3: KNOWLEDGE BASE (pluggable per jurisdiction)                     │
│                                                                             │
│   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐      │
│   │  SINGAPORE       │   │  THAILAND         │   │  OTHER ASEAN    │      │
│   │  ██████████████  │   │  ░░░░░░░░░░░░░░  │   │  ░░░░░░░░░░░░  │      │
│   │                  │   │                   │   │                 │      │
│   │  6,500+ lines    │   │  ~6,000 lines     │   │  Per country   │      │
│   │  6 regulatory    │   │  6 regulatory     │   │  4-6 domains   │      │
│   │  domains         │   │  domains          │   │  each          │      │
│   │                  │   │                   │   │                 │      │
│   │  Employment Act  │   │  Labour Prot Act  │   │  Local labour  │      │
│   │  CPF Act         │   │  Social Sec Act   │   │  law, social   │      │
│   │  EFMA            │   │  Revenue Code     │   │  security,     │      │
│   │  TAFEP           │   │  Foreign Emp Act  │   │  tax code      │      │
│   │  WSH Act         │   │  Labour Rel Act   │   │                 │      │
│   │  IRAS/Tax        │   │  OSH Act          │   │                 │      │
│   │                  │   │                   │   │                 │      │
│   │  PRODUCTION      │   │  4-6 WEEKS        │   │  4-6 WEEKS     │      │
│   │                  │   │  to build          │   │  each          │      │
│   └──────────────────┘   └──────────────────┘   └──────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 2: CALCULATORS (modular per jurisdiction)                          │
│                                                                             │
│   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐      │
│   │  SINGAPORE       │   │  THAILAND         │   │  OTHER ASEAN    │      │
│   │  ██████████████  │   │  ░░░░░░░░░░░░░░  │   │  ░░░░░░░░░░░░  │      │
│   │                  │   │                   │   │                 │      │
│   │  CPF calculator  │   │  SSF calculator   │   │  Local social  │      │
│   │  Leave calc      │   │  PIT withholding  │   │  security      │      │
│   │  Overtime calc   │   │  Severance calc   │   │  Tax calc      │      │
│   │  Retrenchment    │   │  Leave calc       │   │  Leave calc    │      │
│   │  Cost-to-company │   │  Overtime calc    │   │  Overtime calc │      │
│   │  Quota/levy      │   │  (1.5x/3x rules) │   │                 │      │
│   │  Notice period   │   │                   │   │                 │      │
│   │                  │   │                   │   │                 │      │
│   │  7 calculators   │   │  5 calculators    │   │  3-5 each      │      │
│   │  ZERO AI         │   │  ~2 weeks build   │   │                 │      │
│   │  Deterministic   │   │  Deterministic    │   │                 │      │
│   └──────────────────┘   └──────────────────┘   └──────────────────┘      │
│                                                                             │
│   All calculators: pure arithmetic, no LLM, exact statutory formulas       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 1: UNIVERSAL HRIS CORE (same for every jurisdiction)               │
│                                                                             │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│   │ Payroll   │ │ Leave     │ │ Attendance│ │ Claims    │ │ Recruit-  │  │
│   │           │ │ Mgmt      │ │ & Shifts  │ │ & Expense │ │ ment      │  │
│   │ Gross-to- │ │ Apply,    │ │ Clock in/ │ │ Submit,   │ │ Pipeline, │  │
│   │ net with  │ │ approve,  │ │ out, OT,  │ │ approve,  │ │ candidate │  │
│   │ statutory │ │ balance   │ │ schedules │ │ reimburse │ │ tracking  │  │
│   │ deductions│ │ tracking  │ │           │ │           │ │           │  │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                                             │
│   ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐  │
│   │ Appraisals│ │ Projects  │ │ Inventory │ │ Training  │ │ Documents │  │
│   │           │ │ & Tasks   │ │ & Assets  │ │ & Learn   │ │ & Comply  │  │
│   └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘  │
│                                                                             │
│   120+ API endpoints  |  60+ data models  |  35+ dashboard pages           │
│                                                                             │
│   This entire layer works TODAY for any jurisdiction                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   LAYER 0: SHADOW AGENT (UNIVERSAL — same for every jurisdiction)          │
│                                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   │  Intent      │  │  Entity      │  │  Workflow     │  │  Command     │  │
│   │  Classifier  │  │  Resolution  │  │  Composer     │  │  Surface     │  │
│   │              │  │              │  │              │  │              │  │
│   │  Understands │  │  Maps names  │  │  Multi-step  │  │  Natural     │  │
│   │  natural     │  │  to employee │  │  HR task     │  │  language     │  │
│   │  language HR │  │  records     │  │  automation  │  │  interface    │  │
│   │  commands    │  │              │  │              │  │  on every     │  │
│   │              │  │              │  │              │  │  page         │  │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│   Transfers to any jurisdiction with ZERO changes                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Jurisdiction Readiness Summary

```
                    ┌──────────────────────────────────────────────────────┐
                    │         JURISDICTION READINESS MATRIX                │
                    ├───────────┬────────┬────────┬────────┬──────┬───────┤
                    │           │   SG   │   TH   │   MY   │  VN  │  ID   │
                    ├───────────┼────────┼────────┼────────┼──────┼───────┤
                    │ HRIS Core │  ████  │  ████  │  ████  │ ████ │ ████  │
                    │ Trust/EATP│  ████  │  ████  │  ████  │ ████ │ ████  │
                    │ Shadow    │  ████  │  ████  │  ████  │ ████ │ ████  │
                    │ Safety    │  ████  │  ████  │  ████  │ ████ │ ████  │
                    ├───────────┼────────┼────────┼────────┼──────┼───────┤
                    │ KB Content│  ████  │  ░░░░  │  ░░░░  │ ░░░░ │ ░░░░  │
                    │ Agents    │  ████  │  ░░░░  │  ░░░░  │ ░░░░ │ ░░░░  │
                    │ Calculatrs│  ████  │  ░░░░  │  ░░░░  │ ░░░░ │ ░░░░  │
                    │ Filings   │  ████  │  ░░░░  │  ░░░░  │ ░░░░ │ ░░░░  │
                    ├───────────┼────────┼────────┼────────┼──────┼───────┤
                    │ STATUS    │  LIVE  │ 4-6 wk │ 4-6 wk │4-6 wk│4-6 wk │
                    └───────────┴────────┴────────┴────────┴──────┴───────┘

                    ████ = Built and running     ░░░░ = Content needed
```

---

## What Transfers vs What Needs Building

### Transfers Directly (zero changes)

| Component          | Description                               | Lines of Code |
| ------------------ | ----------------------------------------- | ------------- |
| HRIS Core          | Payroll, leave, attendance, claims, etc.  | ~50,000       |
| Trust Layer (EATP) | Cryptographic audit trail                 | ~8,000        |
| Safety Chain       | 13-step validation pipeline               | ~4,000        |
| Shadow Agent       | Intent classifier, PACE, command surface  | ~6,000        |
| Frontend           | React app, design system, all pages       | ~61,000       |
| Admin/QA tools     | Dashboard, KB management, conversation QA | ~5,000        |

### Needs Building Per Jurisdiction

| Component         | Singapore (done)           | Thailand (estimate)     | Effort        |
| ----------------- | -------------------------- | ----------------------- | ------------- |
| Knowledge Base    | 6,500 lines, 6 domains     | ~6,000 lines, 6 domains | 2-3 weeks     |
| Specialist Agents | 6 specialists, 2,800 lines | 6 specialists           | 1-2 weeks     |
| Calculators       | 7 calculators, 2,000 lines | 5 calculators           | 1-2 weeks     |
| Statutory Filings | CPF e-Submit, IR8A         | SSO filing, PND forms   | 1 week        |
| **Total**         | **COMPLETE**               |                         | **4-6 weeks** |

---

## Key Message for Ricoh Thailand

The diagram communicates one central point:

**80% of the platform is jurisdiction-universal and already built. The remaining 20% is jurisdiction-specific content — knowledge base articles, calculator formulas, and specialist agent configuration. For Thailand, that 20% is an estimated 4-6 weeks of focused content work, not a rebuild of the platform.**

The architecture was designed from day one to support multiple jurisdictions. Singapore was the first deployment — the proof that the architecture works. Thailand would be the second — demonstrating that the multi-jurisdiction promise is real.
