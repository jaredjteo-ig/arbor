# Value Audit: AI-Powered HR Advisory Platform for Singapore SMEs

**Perspective**: Skeptical enterprise buyer / early-stage investor
**Date**: 2026-03-11
**Verdict**: Conditionally viable, but the gap between the pitch and deliverable reality is wide. Several structural risks must be resolved before committing capital.

---

## 1. Value Proposition Critique

### Is "AI replacing a team of HR experts" credible?

**Short answer: No. Not as stated.**

The product brief claims the platform functions as "the equivalent of having a team of top-tier HR consultants, MOM specialists, CPF advisors, union representatives, legal experts, IHRP master practitioners, TAFEP advisors, and trade association professionals on call." This is a dangerous framing for three reasons:

1. **It invites scrutiny you cannot survive.** The moment you claim equivalence to a legal expert, every wrong answer becomes a liability event. A top-tier HR consultant has professional indemnity insurance, regulatory accountability, and decades of case experience. An AI has none of these.

2. **It conflates knowledge retrieval with professional judgment.** Knowing what the Employment Act says about overtime is table stakes. A real consultant's value is in the gray areas: "Your employee's contract says X, but the tripartite guidelines suggest Y, and based on similar MOM enforcement actions I've seen, you should do Z." AI can approximate this with good RAG and prompting, but "approximate" is not "equivalent."

3. **It sets expectations the product cannot meet at launch.** If an SME owner asks about a wrongful dismissal claim expecting "top-tier legal expert" quality, and gets a generic summary of the Employment Claims Tribunal process, trust is destroyed on the first interaction.

**What is credible**: "An AI-powered HR knowledge assistant that helps you understand your obligations, find the right forms, and know when to engage a professional." This is honest, useful, and defensible.

### Would an SME owner trust AI for employment law compliance?

**Not by default. Trust must be earned through a specific chain:**

1. **Accuracy on simple questions first.** If the platform correctly tells them their Part IV obligations, the right CPF contribution rates for their employee's age bracket, and the current foreign worker levy — and they can verify these answers against MOM/CPF websites — trust builds.

2. **Source attribution is non-negotiable.** Every answer must cite the specific section of the Employment Act, the specific MOM advisory, the specific CPF contribution table. "According to our analysis" is worthless. "Per Section 38 of the Employment Act (Cap 91)" is credible.

3. **Knowing when to say "talk to a lawyer."** Paradoxically, an AI that admits its limits builds more trust than one that always has an answer. If the platform says "This situation involves potential wrongful dismissal under the Employment Claims Tribunals Act. Here's what you should know, but I strongly recommend engaging an employment lawyer — here are three that specialize in SME disputes," that is more valuable than a confident but potentially wrong legal analysis.

4. **Endorsement from a recognized body.** An ASME or SBF or SNEF stamp of approval would shortcut the trust problem significantly. An IHRP endorsement would be even stronger.

### Actual cost comparison

| Service                   | Typical Cost | What You Get                                                  |
| ------------------------- | ------------ | ------------------------------------------------------------- |
| HR consultant (ad hoc)    | $200-500/hr  | Expert judgment, accountability, relationship context         |
| Employment lawyer         | $300-800/hr  | Legal privilege, court-ready advice, liability coverage       |
| IHRP practitioner         | $150-400/hr  | Certified HR expertise, practice frameworks                   |
| This platform (projected) | $49-199/mo?  | 24/7 access, instant answers, no judgment on "dumb" questions |
| MOM website (free)        | $0           | Raw regulations, basic FAQs, no contextual application        |
| Google search (free)      | $0           | Unreliable, outdated, no Singapore specificity                |

**The real comparison is not AI vs. consultant.** SME owners with fewer than 25 employees are not hiring HR consultants at $300/hr for routine questions. They are Googling, asking friends, or guessing. The real comparison is:

- **AI platform vs. doing nothing / guessing** — this is where the value is
- **AI platform vs. occasional consultant engagement** — the platform handles 80% of routine questions, the consultant handles the 20% that matter

**Implication for pricing**: The platform must be priced against "the cost of not knowing" (a $5,000 MOM penalty, a $20,000 wrongful dismissal claim) rather than against consultant hourly rates.

### Is the value proposition strong enough vs. free MOM resources?

**Yes, but only if the platform does three things MOM cannot:**

1. **Contextual application.** MOM tells you what the law says. The platform should tell you what it means for YOUR specific situation (sector, headcount, worker mix, existing policies).

2. **Actionable output.** MOM gives you the regulation. The platform should give you the form to fill, the letter template to send, the checklist to follow.

3. **Plain language.** MOM's resources are written by policy officers for policy officers. The platform should translate to "here's what you need to do by when."

If the platform only restates what MOM already publishes, it is worthless.

---

## 2. Use Case Validation

### Use Case A: "Is it legal to reimburse unused sick leave as cash?"

**Complexity**: Medium. This requires understanding:

- Employment Act provisions on sick leave (Section 89) — sick leave is a statutory entitlement
- Whether "reimbursement" constitutes a contractual benefit vs. statutory benefit
- Tax implications (IRAS treatment of sick leave encashment)
- Tripartite guidelines on leave management
- Common contractual practices vs. legal requirements

**Can AI handle this?** Yes, with good RAG. The answer involves interpreting clear statutory provisions and applying known IRAS guidelines. The nuance is: the Employment Act does not prohibit it, but it is not a statutory right either — it depends on the employment contract and company policy. A well-designed system can explain this layering.

**Risk**: If the AI gives a flat "yes" or "no" without explaining the contractual dependency and tax treatment, the answer is dangerously incomplete.

**Verdict**: Good use case for AI. Answerable with proper source material. But the quality bar is "explain the nuance," not "give a yes/no."

### Use Case B: "How do I create a claims form?"

**Complexity**: Low. This is operational, not advisory.

**Can AI handle this?** This is the wrong question. A claims form template adds near-zero value — Google Docs templates, existing HR software, and free downloads from HR community sites already solve this.

**What would add value**: "Here's a claims form template, but based on your company size (>10 employees) and the type of claims you're processing, here's what you must include for IRAS compliance and audit readiness. Also, your current claims process has a gap: you're not capturing GST registration numbers for vendor claims above $1,000, which will cause problems during tax filing."

**Verdict**: Weak use case unless the platform adds contextual compliance intelligence on top of the template. As a standalone feature, this does not justify a subscription.

### Use Case C: "I'm hiring my 6th foreign worker — what are my quota implications?"

**Complexity**: High. This requires:

- Sector identification (services, manufacturing, construction, marine, process)
- Sub-sector rules (e.g., services sector S Pass sub-quota vs. Work Permit quota)
- Current local-to-foreign worker ratio calculation
- Dependency Ratio Ceiling (DRC) for the specific sector
- Levy tier implications (how the 6th worker changes the levy rate for ALL foreign workers)
- Whether the worker is S Pass or Work Permit (different quotas)
- Any upcoming policy changes (MOM regularly adjusts DRCs)

**Can AI handle this?** This is actually where AI can shine — IF the system captures the user's context (sector, current headcount breakdown, worker types) and performs the calculation accurately. This is a multi-step reasoning task with clear rules and formulas. No gray areas, no judgment calls.

**Risk**: The DRC and levy rates change regularly. If the knowledge base is even 3 months stale, the calculation could be wrong, and the SME owner could apply for a work pass they are not entitled to (wasting $hundreds in application fees and weeks of time).

**Verdict**: Strong use case. High value, calculable, verifiable. But demands real-time or near-real-time data currency. This is the kind of feature that could sell the product on its own.

### Use Case D: "An employee filed a wrongful dismissal claim — what do I do?"

**Complexity**: Very high. This involves:

- Employment Claims Tribunals Act procedures and timelines
- Whether the claim is mediated (TADM) first or goes direct to ECT
- Employer's response obligations and deadlines
- Evidence preparation and documentation requirements
- Whether to engage a lawyer (and when legal representation is allowed at ECT)
- Strategic considerations: settle vs. defend, cost-benefit, reputational risk
- Whether the dismissal was actually wrongful (requires factual and legal analysis)

**Can AI handle this?** Partially. The AI can outline the process, explain the timeline, list the documents to gather, and explain TADM mediation. It cannot assess whether the dismissal was wrongful (that requires reviewing the specific facts), it cannot provide legal strategy, and it absolutely should not advise on settlement vs. defense.

**Risk**: This is the highest-liability use case. If the AI says "you should attend the TADM mediation and present X" and the employer follows that guidance and loses, the platform has effectively provided unauthorized legal advice with real financial consequences.

**What should happen**: The platform provides a clear process overview, helps the employer gather documentation, and strongly recommends engaging an employment lawyer. It should offer to connect to vetted employment law firms. This is the "know when to refer" moment that builds trust.

**Verdict**: Dangerous as a primary advisory use case. Excellent as a triage and preparation tool. The platform must have hard guardrails here.

---

## 3. Monetization Reality Check

### What would SMEs actually pay?

**Singapore SME reality check:**

- 99% of Singapore enterprises are SMEs (roughly 300,000 entities)
- Most have 1-10 employees
- They are notoriously cost-conscious — many still use Excel for HR
- Monthly software budgets are often <$500 total for all business tools
- HR is viewed as a cost center, not a strategic function

**Willingness to pay (estimated):**

- Micro SMEs (1-5 employees): $0-29/month — these owners handle everything themselves and resist any new cost
- Small SMEs (6-25 employees): $29-99/month — starting to feel HR pain, may have had a compliance scare
- Medium SMEs (26-200 employees): $99-299/month — likely have at least one HR person who could champion the tool
- HR consultants/practitioners: $49-149/month — as a productivity tool, easier sell

**Total addressable market (realistic)**:

- Maybe 20,000-40,000 SMEs in the "feels HR pain" category
- At 2-5% conversion: 400-2,000 paying customers
- At $79/month average: $380K-$1.9M ARR
- This is a niche product. It is not a venture-scale opportunity unless you expand beyond Singapore.

### Pricing model

| Model            | Fit for This Market     | Rationale                                                                                                                                  |
| ---------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Freemium**     | Best for acquisition    | Free tier: basic FAQ, CPF rate lookup, simple templates. Paid tier: contextual advisory, sector-specific calculations, document generation |
| **Per-query**    | Poor                    | Creates anxiety about cost, discourages exploration, hard to predict revenue                                                               |
| **Subscription** | Best for retention      | Monthly/annual, tiered by company size or query volume                                                                                     |
| **Per-incident** | Possible for high-value | One-time fee for wrongful dismissal guidance package, termination compliance package — like "buying" a mini-consultation                   |

**Recommendation**: Freemium-to-subscription with a per-incident upsell for high-stakes scenarios. The free tier is the trust-building engine. The subscription is the revenue engine. The per-incident model captures willingness to pay at crisis moments (which is when SME owners are least price-sensitive).

### Government grant viability

**Strong potential here:**

- **Productivity Solutions Grant (PSG)**: Up to 50% support for qualifying SMEs adopting IT solutions. HR software is an eligible category. The platform would need to be listed on the IMDA SME Go Digital catalogue.
- **SME Go Digital Programme**: Specifically supports digital adoption. An AI-powered HR compliance tool fits the narrative well.
- **Enterprise Development Grant (EDG)**: For the platform's own development, up to 50% of qualifying costs.
- **SkillsFuture Enterprise Credit (SFEC)**: Some overlap if the platform includes learning/development components.

**Critical implication**: If the platform is PSG-listed, the effective cost to the SME drops by 50%. A $99/month subscription becomes $49.50/month after grant. This dramatically improves conversion.

**Action required**: PSG listing involves IMDA evaluation, deployment track record, and compliance with grant conditions. Plan for a 3-6 month approval process.

### Association/chamber distribution model

**This is potentially the strongest go-to-market channel:**

- **ASME** (Association of Small & Medium Enterprises): ~12,000 members. If the platform is offered as a member benefit or at a discounted member rate, instant distribution + credibility.
- **SBF** (Singapore Business Federation): Broader membership, more established enterprises.
- **SNEF** (Singapore National Employers Federation): Specifically focused on employment and HR issues. Natural alignment.
- **Sector-specific associations**: Restaurant Association of Singapore, Singapore Contractors Association, etc. — these could sponsor sector-specific modules.

**Model**: Association pays a bulk license, members get access as a benefit. Platform charges $3-10/member/month in bulk. With 5,000 members: $180K-$600K/year from a single association deal.

**This is probably the right first move** — an association partnership provides distribution, credibility, and revenue in one deal. It also provides a built-in feedback loop from real SME owners.

---

## 4. Trust and Liability

### Handling wrong advice

**This is the existential risk for the product.**

A framework:

1. **Classification of advice risk levels:**
   - **Green (informational)**: CPF rates, public holiday dates, statutory leave entitlements — factual, verifiable. Wrong answers are embarrassing but low-consequence.
   - **Amber (guidance)**: Best practices, policy recommendations, process advice — wrong answers lead to suboptimal decisions but not legal liability.
   - **Red (compliance/legal)**: Employment Act obligations, termination procedures, discrimination law — wrong answers can lead to MOM penalties, tribunal claims, or lawsuits.

2. **Response protocol by risk level:**
   - Green: Answer directly with source citation.
   - Amber: Answer with "best practice" framing and note that professional advice may differ.
   - Red: Answer with full source citation, explicit disclaimer, and recommendation to verify with a qualified professional. For high-stakes red queries (dismissal, claims, discrimination), include a "connect to a professional" CTA.

3. **Liability limitation:**
   - Terms of service must clearly state the platform provides information, not legal advice.
   - Professional indemnity insurance for the platform (yes, this exists for digital advisory services).
   - Incident response process for identified wrong answers: notify affected users, correct the information, document the correction.

### Regulatory barriers to AI legal advice in Singapore

**This is a real concern, but navigable:**

- The Legal Profession Act (Cap 161) restricts the practice of law to qualified persons. Providing "legal advice" without being a qualified lawyer is a criminal offence.
- **However**: There is a distinction between "legal information" (explaining what the law says) and "legal advice" (telling someone what they should do in their specific situation). This platform must operate firmly in the "legal information" space.
- The Ministry of Law has been supportive of legal technology (LawNet, CLAS, Community Justice Centre). There is no blanket prohibition on AI providing legal information.
- **Key risk**: If the platform's responses cross from information to advice — especially for individual disputes — regulatory exposure increases.

**Mitigation**: Frame all outputs as "information and guidance," not "advice." Include persistent disclaimers. Build in hard stops for high-risk scenarios that redirect to professionals.

### Building credibility without IHRP/legal backing

**You cannot. You need at least one institutional endorsement.**

Options (in order of impact):

1. **IHRP endorsement**: Most directly relevant. If IHRP validates the platform's HR content, this is the single highest-value credibility signal for the target market.
2. **Law firm partnership**: A named employment law firm reviews and validates legal compliance content. Their name appears on the platform.
3. **Association endorsement**: ASME/SBF/SNEF says "we've reviewed this and recommend it to our members."
4. **MOM/TAFEP collaboration**: If MOM or TAFEP officially partners or allows use of their content, this is definitive.
5. **Advisory board of named practitioners**: Visible names of real HR/legal professionals who stand behind the product.

Without at least one of these, the platform is just another AI chatbot. The market will not differentiate it from ChatGPT with a prompt.

### Disclaimer paradox

**Real tension here.** Too few disclaimers = liability exposure. Too many disclaimers = the product feels useless ("why am I paying for something that says 'don't rely on this' after every answer?").

**Resolution**: Contextual disclaimers, not blanket ones.

- For factual/informational queries: No disclaimer needed beyond a general ToS.
- For guidance queries: Light disclaimer ("This reflects current guidelines; consult a professional for your specific situation").
- For high-risk queries: Strong, specific disclaimer with professional referral.
- Never: A persistent banner on every page saying "This is not legal advice." That undermines the entire product.

---

## 5. Build vs. Buy Decision

### Build from scratch vs. existing platforms

**Do not build from scratch.** The core AI capability is commodity (LLM + RAG). The value is in the knowledge base, the contextual engine, and the user experience.

**Recommended architecture:**

- **AI layer**: Use existing LLM APIs (already mandated by .env model configuration). Kaizen agent framework for multi-domain routing.
- **Knowledge base**: This IS the product. Curated, structured regulatory content with version tracking. This must be built and maintained. DataFlow for structured regulatory data.
- **Calculation engine**: Foreign worker quotas, CPF rates, levy calculations — these are deterministic. Do not use AI for math. Build proper calculation modules.
- **Frontend**: Web-based, mobile-responsive. Nothing fancy needed. The interface is a conversation + dashboard.
- **Distribution**: Nexus for multi-channel (web, API for integration with HR software, potentially WhatsApp for SME accessibility).

### Minimum viable product

**MVP scope (prove value in 4-6 weeks):**

1. **One sector only** (services — largest SME segment)
2. **Three capability areas only:**
   - Employment Act obligations lookup (contextual, by company size)
   - CPF contribution calculator (by employee age, wage, citizenship)
   - Foreign worker quota calculator (services sector DRC, levy tiers)
3. **Basic conversational interface** — ask a question, get an answer with source citation
4. **10-20 curated templates** — employment contracts, termination letters, claims forms — with contextual guidance
5. **Hard stops on high-risk queries** — redirect to professional services

**What the MVP proves:**

- Can the AI answer routine HR questions accurately enough to be trusted?
- Will SME owners actually use it (engagement metrics)?
- Will they pay for it after a free trial?
- What questions do they actually ask? (This data is gold for product development.)

### Riskiest assumption to test first

**"SME owners will trust an AI platform enough to act on its guidance for HR compliance decisions."**

This is riskier than the technical challenge. You can build the platform. The question is whether the target user — who is typically a business owner wearing ten hats, dealing with HR reluctantly, and scared of MOM penalties — will use it AND follow its guidance AND pay for it.

**How to test it**: Build a concierge MVP. Use a WhatsApp Business number. Let 50 SME owners send HR questions. Have a human HR professional answer using AI-assisted research. Measure:

- What questions do they ask?
- Do they act on the answers?
- Do they come back?
- Would they pay?

This test costs almost nothing and answers the most important question before any engineering investment.

---

## 6. Red Flags — Every Reason This Could Fail

### 1. Knowledge accuracy and currency (CRITICAL)

Singapore's employment regulations change frequently. MOM issues new advisories, CPF rates adjust, foreign worker policies shift with economic conditions. A knowledge base that is even one quarter behind is dangerous.

**Failure scenario**: Platform states the wrong DRC for the services sector after a Budget announcement changes it. SME owner hires based on wrong quota information. MOM rejects work pass application. Owner blames platform.

**Mitigation cost**: Ongoing content maintenance — at least one dedicated person monitoring regulatory changes. This is a recurring operational cost that never goes away.

### 2. Regulatory risk of AI legal advisory (HIGH)

If the platform is perceived as providing legal advice, the Legal Profession Act creates criminal liability. Even if the platform carefully frames outputs as "information," a single aggressive complaint to the Law Society could trigger scrutiny.

**Failure scenario**: SME owner follows platform guidance on a termination, employee files a claim, employer loses at ECT, employer's lawyer argues the platform provided unauthorized legal advice. Media picks it up.

**Mitigation**: Robust legal framing, insurance, legal counsel review of output templates, hard stops on high-risk queries.

### 3. Trust deficit (HIGH)

SME owners making HR decisions are often dealing with stressful, personal situations (firing someone, handling a harassment complaint, facing a claim). Trust in these moments requires more than a good UI — it requires perceived authority. An unknown AI startup has no authority.

**Failure scenario**: Platform launches, gets some signups, but users only use it for low-stakes lookups and still call their accountant/lawyer/uncle for anything that matters. Platform fails to demonstrate value beyond what Google provides.

**Mitigation**: Institutional endorsement (ASME, IHRP, law firm partner). Without this, the trust gap may be unbridgeable.

### 4. Market too small (MEDIUM-HIGH)

Singapore has ~300,000 SMEs. The realistic addressable market (SMEs with 6-200 employees who feel HR pain and are willing to pay for software) is maybe 20,000-40,000. At realistic conversion rates, this caps revenue at low-single-digit millions ARR. This is a viable small business but not a venture-scale opportunity.

**Failure scenario**: Investors expect venture returns. The math does not support it in Singapore alone. Regional expansion (Malaysia, Hong Kong, other ASEAN) requires completely different regulatory knowledge bases — it is essentially building a new product for each market.

**Mitigation**: Accept this as a niche business. Or: build the platform as a white-label product and license the architecture to HR associations/firms in other markets who provide their own content.

### 5. SME unwillingness to pay (MEDIUM-HIGH)

Singapore SMEs under-invest in HR systematically. Many view compliance as a checkbox exercise, not a strategic investment. The platform is competing for budget against "my accountant handles that" and "I'll figure it out when I need to."

**Failure scenario**: Thousands of free-tier users, single-digit percent conversion to paid. Unit economics never work.

**Mitigation**: PSG grant listing (cuts effective cost by 50%). Association distribution (removes the individual purchasing decision). Focus marketing on "cost of non-compliance" — a single MOM penalty can exceed a year of subscription fees.

### 6. Competition from established players (MEDIUM)

Existing HR software platforms are adding AI features. If any incumbent bolts on an AI advisory layer, they have an existing user base, existing payment relationships, and existing trust.

**Failure scenario**: An established HRIS platform launches "AI HR Advisor" as a feature within their existing payroll platform. SMEs who already use their software get it bundled. Standalone advisory platform cannot compete.

**Mitigation**: Move fast. The window for a dedicated advisory platform may be 12-18 months before incumbents catch up. Alternatively, position as a B2B2B product — license the advisory engine TO existing HR software platforms rather than competing with them.

### 7. Complexity of keeping content current (MEDIUM)

The product brief lists an enormous scope: all HR pillars, all sectors, all regulatory bodies. Keeping this comprehensive AND current is a full-time content operation, not a one-time build.

**Failure scenario**: Platform launches with comprehensive content, but 6 months later half of it is stale. Users lose trust. Churn accelerates.

**Mitigation**: Start narrow (one sector, core compliance topics only). Expand based on actual user demand. Build content update processes before building content.

### 8. "Just use ChatGPT" problem (MEDIUM)

GPT-4, Claude, and other general-purpose AI models already answer HR questions reasonably well. The platform must demonstrate clearly superior accuracy and contextual understanding for Singapore-specific questions. If the delta is small, price-sensitive SME owners will use the free alternative.

**Failure scenario**: An SME owner asks ChatGPT the same question, gets a 70% good answer for free, and decides the platform's 90% good answer is not worth $99/month.

**Mitigation**: The platform's advantage must be in verified accuracy (source citations), calculations (quota/levy/CPF), contextual personalization (remembers the user's sector, headcount, worker mix), and actionable outputs (templates, forms, checklists). General-purpose AI cannot do these things well.

### 9. Founder/team capability gap (UNASSESSED)

Building this product requires deep expertise in Singapore employment law AND AI engineering AND SME go-to-market. This combination is rare. If the team lacks any of these three, execution risk is high.

### 10. Single-country dependency (MEDIUM)

The product is entirely dependent on Singapore's regulatory environment. Any change in government policy (e.g., a government-built free HR advisory tool, which is not implausible given MOM's digital push) could undermine the entire business model overnight.

---

## Summary Assessment

| Dimension             | Rating                                   | Key Issue                                                                |
| --------------------- | ---------------------------------------- | ------------------------------------------------------------------------ |
| Value proposition     | Moderate                                 | Must be reframed from "expert replacement" to "knowledge assistant"      |
| Use case viability    | Strong for routine, weak for high-stakes | Good on compliance lookups and calculations; dangerous on legal disputes |
| Monetization          | Challenging but feasible                 | Association model + PSG grants make unit economics work                  |
| Trust/liability       | High risk                                | Institutional endorsement is a prerequisite, not a nice-to-have          |
| Market size           | Niche                                    | Viable small business, not venture-scale in Singapore alone              |
| Competitive moat      | Narrow                                   | 12-18 month window before HR software incumbents add AI advisory         |
| Technical feasibility | High                                     | This is a content + UX challenge, not a technology challenge             |

### Three Things to Do Before Writing Code

1. **Validate demand with a concierge test.** 50 SME owners, WhatsApp, human-assisted AI answers. 4 weeks. Proves trust, willingness to pay, and reveals what questions people actually ask.

2. **Secure one institutional endorsement.** ASME, SNEF, or IHRP. Without it, the platform has no credibility differentiator versus ChatGPT.

3. **Confirm PSG listing feasibility.** If the platform can be PSG-listed, the go-to-market cost drops dramatically and SME price resistance is halved.

### Bottom Line

The underlying need is real: Singapore SME owners make HR decisions without adequate guidance, and the consequences of getting it wrong are increasing. But the product as described in the brief overreaches on its claims, underestimates the trust problem, and has not yet validated its most critical assumption (that SME owners will trust AND pay for AI-driven HR guidance).

The right path is: narrow scope, institutional backing, concierge validation, then build. Not: build everything, then find customers.
