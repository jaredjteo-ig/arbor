# Central HR Copilot — Capability Brief

---

## What Is Central?

Central is a production-grade AI-powered HR platform that combines a full HRIS (payroll, leave, attendance, claims, recruitment, appraisals) with an employment law advisory engine grounded in actual legal provisions. It is live today at central.kailash.ai. The platform is built on the open-source Kailash SDK (Apache 2.0, maintained by the Terrene Foundation).

---

## Key Differentiators

1. **Cited, not guessed** — Every advisory response includes specific legal citations (Act, Section, subsection). Unlike general-purpose AI, Central retrieves from a structured knowledge base of verified legal provisions. Answers can be traced back to their source for audit and verification.

2. **Risk-aware AI** — A three-tier risk system (green, amber, red) classifies every query. Routine questions get direct answers. Sensitive situations receive caveats. High-risk legal matters trigger explicit professional referral recommendations. The AI knows when to stop being the advisor.

3. **Deterministic calculations** — Statutory computations (social security contributions, tax withholding, overtime pay, leave entitlements, severance) use purpose-built calculators with zero AI involvement. The numbers are exact, computed from published statutory tables — not inferred by a language model.

4. **Enterprise-grade trust lineage** — Every AI response carries a cryptographic audit trail (EATP — Enterprise Agent Trust Protocol). For any advisory response, you can trace which knowledge base provisions were consulted, which specialist agents contributed, what the confidence level was, and what safety checks were applied. This is designed for organisations with strict governance and audit requirements.

5. **Full platform, not just a chatbot** — Central is a complete HRIS with 120+ API endpoints, 60+ data models, and 35+ dashboard pages. The AI advisory engine is integrated into the operational platform — it can explain the regulation behind a payroll deduction, flag compliance risks in a leave approval, and proactively surface upcoming deadlines.

---

## What Is Built Today

**Singapore — Production-Grade, Live**

- 6 regulatory domains: Employment Act, CPF, Foreign Manpower, Fair Employment, Workplace Safety, Tax
- 6,500+ lines of structured knowledge base content
- 7 deterministic calculators (CPF, leave, overtime, retrenchment, cost-to-company, quota/levy, notice period)
- 13-step safety chain on every advisory query
- Full HRIS: payroll with CPF/SDL/FWL breakdowns, leave management, attendance, claims, recruitment, appraisals
- Shadow agent: AI embedded on every page, proactive compliance alerts, natural-language command surface
- Admin QA dashboard: response quality monitoring, knowledge base management, conversation review

---

## What It Means for Thailand

The Central architecture is jurisdiction-pluggable by design. The universal layers — HRIS core, trust and safety, shadow agent, admin tools — transfer to any jurisdiction with zero changes. The jurisdiction-specific layers — knowledge base content, specialist agents, calculators, statutory filing formats — are modular and configurable.

**Thailand adaptation requires**:

- Knowledge base: Labour Protection Act, Social Security Act, Revenue Code, Foreign Employment Act, Labour Relations Act, Occupational Safety Act
- Calculators: Social Security Fund contributions, personal income tax withholding, severance pay, leave entitlements, overtime rates
- Specialist agents: configured for Thai regulatory domains

**Estimated timeline**: 4-6 weeks for a functional Thailand version, leveraging the proven Singapore architecture. This is content adaptation, not a platform rebuild.

**Multi-country potential**: The same pattern extends to Malaysia (EA 1955, EPF/SOCSO/EIS), Vietnam (Labour Code 2019, Social Insurance), Indonesia (Omnibus Law, BPJS), and the Philippines (Labour Code, SSS/PhilHealth). One platform, adapted per jurisdiction.

---

## Pricing

**Enterprise subscription** (includes platform + AI advisory + support SLA):

- Full platform: USD 8-15 per employee per month
- AI advisory layer only (alongside existing HRIS): USD 3-5 per employee per month
- Proof-of-concept engagement: Fixed fee, 4-6 weeks, 3 regulatory domains

All pricing includes ongoing regulatory updates, knowledge base maintenance, and technical support.

---

## Next Steps

1. **Identify priority domains** — Which 2-3 Thai regulatory areas matter most to your HR team?
2. **Thailand proof-of-concept** — Build a focused demo with those priority domains (4-6 weeks)
3. **Pilot deployment** — Deploy for a subset of your Thai workforce to validate in practice
4. **Regional expansion** — Extend to additional ASEAN jurisdictions based on Ricoh's footprint

---

**Contact**: [Name] | [Email] | [Phone]

**Platform**: https://central.kailash.ai

**Open-source foundation**: Built on the Kailash SDK (Apache 2.0) by Terrene Foundation (terrene.foundation)
