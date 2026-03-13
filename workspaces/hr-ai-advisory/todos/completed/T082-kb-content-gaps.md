# T082 — Add Missing KB Content for Adversarial Scenario Gaps

**Status**: ACTIVE
**Milestone**: 8 — Quality Rubric and Adversarial Testing
**Priority**: HIGH
**Estimated Effort**: 6h
**Dependencies**: T064, T079

## What to build

The adversarial scenario research identified 10 knowledge gaps — topic areas where the KB has insufficient provisions to support accurate specialist advice. Add or enhance provisions in the KB for each gap using the existing KB pipeline (T014).

## 10 Gaps to Fill

### Gap 1: Compound OT Day Types

- PH falling on a rest day: specific OT/pay rules under Employment Act
- Provisions needed: EA s.36 (rest day), s.38 (overtime), Seventh Schedule (PH)

### Gap 2: Extended Childcare Leave (Ages 7-12)

- Government-paid childcare leave for children aged 7-12 (6 days/year, employer pays first 3)
- Provisions needed: Child Development Co-Savings Act s.12B

### Gap 3: Low-Wage CPF Rules

- Graduated employer CPF contribution rates for low-wage workers (< $750/month)
- Workfare Income Supplement interaction
- Provisions needed: CPF Act Third Schedule, WIS eligibility rules

### Gap 4: Platform Workers Act

- New protections for platform workers (Grab, Foodpanda, etc.) from 2024
- CPF contributions, work injury compensation, minimum income protection
- Provisions needed: Platform Workers Act 2024 key sections

### Gap 5: Constructive Dismissal

- Definition, evidence required, MOM complaint process, burden of proof
- Provisions needed: EA s.14 read with wrongful dismissal framework, Tripartite Guidelines

### Gap 6: PDPA Breach Notification

- 3-calendar-day notification rule for prescribed data breaches
- PDPC notification obligations, affected individual notification
- Provisions needed: PDPA s.26D, PDPC Advisory Guidelines

### Gap 7: Salary Deduction Aggregation Rule

- Total deductions in any wage period cannot exceed certain thresholds under s.27 EA
- Specific categories of permitted deductions and their sub-limits
- Provisions needed: EA s.27 with all sub-clauses

### Gap 8: Part-Time Employee Regulations

- Tripartite Guidelines on part-time employment (pro-rated leave, rest days, OT)
- Provisions needed: Employment Act Part IV read with Tripartite Guidelines on Part-Time Employment

### Gap 9: Mental Health Workplace Obligations

- Employer obligations under Workplace Safety and Health Act for psychosocial hazards
- Tripartite Advisory on Mental Well-Being at Workplaces
- Provisions needed: WSH Act s.12 duty of care, MOM Tripartite Advisory

### Gap 10: AI and Algorithmic Discrimination

- Use of AI in hiring/performance management — TAFEP guidance
- FCF job portal AI-assisted screening compliance
- Provisions needed: TAFEP Advisory on Fair Use of Technology in Hiring

## Acceptance Criteria

- [ ] At least 3 provisions added per gap (total 30+ new provisions)
- [ ] Each provision includes: title, act/source, section reference, effective date, summary text, full_text
- [ ] KB pipeline used for ingestion (not direct DB inserts)
- [ ] Citation validator (T081) can resolve new provision identifiers
- [ ] Integration test: Gap 2 query (childcare leave age 7-12) retrieves relevant provision
- [ ] Integration test: Gap 4 query (platform worker CPF) retrieves relevant provision

## Files

- `src/hr_advisory/kb/` — provision data files per gap
- KB pipeline invocation for each gap's provisions

## Reference

10-adversarial-scenarios.md (gaps identified across all 8 categories)

## Definition of Done

- [ ] All 10 gaps have at least one provision in the KB
- [ ] Adversarial scenarios that were failing due to KB gaps pass after this task
- [ ] No existing provisions overwritten or degraded
