# Deep Research: Shadow Agent Evolution

See full analysis in agent output. Key findings summarized below.

## Competitive Landscape Summary

All established Singapore HR SaaS platforms share one universal gap: **none answer "Am I doing HR right?"** They process payroll and manage leave but provide zero regulatory guidance, no compliance monitoring, and no AI advisory.

## Critical Strategic Insight

**Arbor should NOT become an HRIS.** The brief conflates three products:

1. AI advisory engine (built)
2. Shadow agent UX presence (unbuilt)
3. Multi-tenant employee platform (unbuilt — equivalent to building an HRIS)

**Resolution**: Arbor is the **intelligence layer** that works alongside an HRIS. Employee data comes from HRIS integration (third-party APIs), not from building a competing payroll engine.

## Layer Feasibility (by complexity)

| Layer                 | Complexity | Sprint   | Dependencies                     |
| --------------------- | ---------- | -------- | -------------------------------- |
| D: Command Surface    | 4/10       | Sprint 1 | None                             |
| C: Inline Annotations | 5/10       | Sprint 2 | None                             |
| B: Margin             | 6/10       | Sprint 2 | Partial A for full observations  |
| A: Substrate          | 8/10       | Sprint 3 | Multi-tenant model, PDPA consent |

## Phasing

- **Sprint 1**: Command Surface + Shadow Widget + Action Registry (replace chat drawer)
- **Sprint 2**: Margin + Inline Annotations (ambient intelligence on existing pages)
- **Sprint 3**: Enterprise model + Substrate observation + Employee interface

## 5 Decision Points for Stakeholder

1. Payslip strategy: generate or import from HRIS?
2. Leave management: process applications or display-only?
3. Employee pricing: free seat or per-employee charge?
4. Observation consent: opt-in or opt-out?
5. HRIS integration priority: Sprint 3 or separate initiative?
