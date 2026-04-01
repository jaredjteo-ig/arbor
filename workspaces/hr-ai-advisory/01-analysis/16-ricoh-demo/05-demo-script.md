# Arbor Demo Script — Ricoh Thailand

**Duration**: 45 minutes
**Presenter**: [Name]
**Date**: [Demo date]
**Platform**: https://arbor.terrene.foundation
**Demo account**: demo@arbor.terrene.foundation / [password]
**Pre-warm**: Send one throwaway advisory query 10 minutes before start

---

## Pre-Demo Checklist (30 Minutes Before)

- [ ] Open https://arbor.terrene.foundation in Chrome (incognito for clean state)
- [ ] Log in with demo account, verify dashboard loads with seed data
- [ ] Send a throwaway advisory query to warm the system ("What is annual leave entitlement?")
- [ ] Open a second browser tab to https://arbor.terrene.foundation/advisory (ready for Act 2)
- [ ] Open a third tab to https://arbor.terrene.foundation/calculators (ready for Act 2)
- [ ] Open a fourth tab to https://arbor.terrene.foundation/admin (ready for Act 3)
- [ ] Verify internet connection is stable
- [ ] Have backup hotspot ready
- [ ] Close all notifications, Slack, email — fullscreen browser
- [ ] Set display to 125% zoom for readability on projector

---

## ACT 1: THE PROBLEM (0:00 - 5:00)

> No screen sharing yet. Speak directly to the audience.

### Opening (0:00 - 1:30)

**Say**:

"Thank you for having us. Today I want to show you something we have been building — an AI-powered HR platform — and talk about what it could mean for Ricoh Thailand.

But first, let me set the scene with a problem I think your HR team knows well.

Every country in ASEAN has its own labour law, its own social security system, its own tax rules. Thailand has the Labour Protection Act, the Social Security Fund, the Revenue Code. Singapore has the Employment Act, CPF, IRAS. Malaysia, Vietnam, Indonesia — all different.

For a company like Ricoh, operating across the region, this means your HR teams in each country need to know their local regulations inside and out. And those regulations change — sometimes every year."

### The Pain (1:30 - 3:00)

**Say**:

"What happens in practice? Your HR officers look things up manually. They call external consultants. They search Google. And increasingly, they ask ChatGPT.

Here is the problem with that."

> If you have prepared a ChatGPT screenshot showing a wrong or uncited answer about employment law, show it now. Otherwise, describe the issue verbally.

**Say**:

"When you ask ChatGPT about employment law, you get something that sounds confident and professional. But it often gets details wrong — wrong notice periods, wrong contribution rates, wrong eligibility criteria. And it never tells you which section of which Act it is quoting from. There are no citations. No way to verify.

For general knowledge, that is fine. For HR compliance — where a wrong answer can mean a wrongful dismissal claim, a regulatory penalty, or a lawsuit — that is dangerous."

### The Transition (3:00 - 5:00)

**Say**:

"What if your HR team had a copilot that was grounded in actual legal provisions? That showed you exactly which section of law it was citing? That told you when a question was too risky for AI and needed a human lawyer?

That is what we built. Let me show you."

> Begin screen sharing. Switch to the browser with the dashboard.

---

## ACT 2: THE PLATFORM — LIVE DEMO (5:00 - 20:00)

### Dashboard Walkthrough (5:00 - 7:00)

> **Navigate to**: https://arbor.terrene.foundation/dashboard

**Say**:

"This is the Arbor platform. It is a full HR system — not just an AI chatbot. The demo company here is a Singapore SME with about 30 employees.

On the dashboard you can see:

- **Headcount summary** — how many employees, broken down by type. In Singapore, that means citizens, permanent residents, and work pass holders. For Thailand, this would show Thai nationals and work permit holders.
- **Pending approvals** — leave requests, expense claims, timesheets waiting for sign-off.
- **Compliance alerts** — things the system has flagged, like upcoming work pass expiries or filing deadlines. Think of it as a compliance early-warning system.
- **Quick actions** — one-click access to common HR tasks."

**Thai translation note**: When mentioning work pass types, add: "In Thailand, the equivalent categories would be Thai nationals and foreign workers with work permits from the Department of Employment."

### Employee List — Brief (7:00 - 7:30)

> **Navigate to**: https://arbor.terrene.foundation/employees

**Say**:

"Here is the employee directory. Each record has personal details, employment history, salary information, leave balances — everything you would expect from an HRIS. This is the operational foundation that the AI layer sits on top of."

> Do NOT click into individual employee records unless they have complete data. Scroll the list briefly to show volume.

### Advisory Chat — The Star of the Demo (7:30 - 15:00)

> **Navigate to**: https://arbor.terrene.foundation/advisory

**Say**:

"Now, this is the heart of the platform — the AI advisory engine. Let me ask it a real employment law question."

#### Question 1: Factual + Citations (7:30 - 10:00)

> **Type exactly**: `What is the minimum notice period for terminating an employee who has worked for 3 years?`

**While it streams, say**:

"Watch what happens. The system is searching the knowledge base, identifying the relevant legal provisions, and composing a response. You can see the text streaming in real time."

**After the response appears, say**:

"Notice a few things. First — there are **citations**. It tells you exactly which section of the Employment Act it is referring to. Section 10 of the Singapore Employment Act specifies notice periods based on length of service.

Second — there is a **risk indicator**. This is a green-tier question — factual, well-established law, low risk of giving wrong advice.

Third — there is a **disclaimer** at the bottom explaining the limitations and when to consult a professional.

Now, for your context — in Thailand, the equivalent law is the Labour Protection Act, Section 17. The notice periods work differently — Thailand requires at least one full pay cycle's notice. The point is: the system does not make up answers. It retrieves from a structured knowledge base and shows you the source."

#### Question 2: Calculator Trigger (10:00 - 12:30)

> **Type exactly**: `What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?`

**While it streams, say**:

"This question involves numbers — contribution rates and exact amounts. Watch what happens."

**After the response appears, say**:

"The system detected that this is a calculation question. Instead of asking the AI to guess the numbers, it called the **CPF calculator** — a deterministic tool that computes exact amounts based on the statutory tables.

CPF is Singapore's mandatory savings system — employer and employee each contribute a percentage of salary to retirement, healthcare, and housing funds. For Thailand, the equivalent is the **Social Security Fund** — employer and employee each contribute 5%, capped at 750 baht per month.

The key design principle: the AI never guesses numbers. For anything that has a formula — contribution rates, tax, overtime pay, leave entitlements — the platform uses a **calculator**, not the AI model. The AI then explains the context around those numbers."

#### Question 3: High-Risk Escalation (12:30 - 15:00)

> **Type exactly**: `An employee claims they were wrongfully dismissed after refusing overtime. What should I do?`

**While it streams, say**:

"This is a deliberately difficult question. Wrongful dismissal is a litigation risk. Let us see how the system handles it."

**After the response appears, say**:

"Notice the risk tier changed to **red**. The system recognized this involves potential litigation — wrongful dismissal, refusal of overtime, possible Employment Act violation.

The response does give you relevant information and process guidance, but it prominently recommends consulting a qualified employment lawyer. It does not try to be the lawyer.

This is the difference between Arbor and ChatGPT. ChatGPT would give you the same confident tone regardless of whether the question is simple or legally dangerous. Arbor explicitly tells you: this is a red-tier situation, here is what you should know, but get professional help.

In Thailand, the equivalent situation would involve the Labour Court and potentially the Labour Protection Act, Section 49 on unfair dismissal. Different law, same principle — the system recognises danger and escalates."

### Calculators (15:00 - 16:30)

> **Navigate to**: https://arbor.terrene.foundation/calculators

**Say**:

"These are the deterministic calculators I mentioned. There are seven of them — CPF contributions, leave entitlements, overtime pay, retrenchment benefits, notice periods, cost-to-company, and foreign worker quotas.

Let me run a quick CPF calculation."

> **Click**: CPF calculator. Enter: Age 35, Citizen, Salary $5,000. Submit.

**Say**:

"Exact numbers, computed from the statutory tables. Employee contribution: $1,000. Employer contribution: $850. No AI involved — pure arithmetic from the published rates.

For Thailand, the equivalent calculators would compute Social Security Fund contributions, personal income tax withholding, severance pay, and overtime rates. Different formulas, same principle: the platform calculates, the AI explains."

### Payroll (16:30 - 20:00)

> **Navigate to**: https://arbor.terrene.foundation/payroll

**Say**:

"Arbor is not just an advisory tool — it runs payroll. Here you can see past payroll runs with full gross-to-net breakdowns."

> Scroll through the payroll list to show completed runs. Click into one if data is populated.

**Say**:

"Each payroll run computes:

- **Gross salary** — base pay plus any allowances or overtime
- **CPF deductions** — both employee and employer contributions, computed by those same calculators
- **SDL** — Skills Development Levy, a small employer-paid levy for workforce training. Thailand's equivalent is the Skill Development Fund contribution.
- **FWL** — Foreign Worker Levy, which applies to employers who hire foreign workers on certain pass types.

The net pay is computed deterministically. When a payroll officer has a question about why a particular deduction was applied, they can ask the advisory engine — and it explains the regulation behind the number."

**TRANSITION to Act 3**:

"So far you have seen the operational platform — employee management, advisory chat, calculators, payroll. Now let me show you the intelligence layer that sits underneath."

---

## ACT 3: THE INTELLIGENCE LAYER (20:00 - 30:00)

### Shadow Agent (20:00 - 23:00)

> **Navigate to**: https://arbor.terrene.foundation/leave (or any HRIS page with the shadow agent margin visible)

**Say**:

"On every page of the platform, there is an AI layer running in the background. We call it the **Shadow Agent**. It observes what you are doing and proactively surfaces relevant information."

> Point to the margin indicators or briefing cards if visible on the page.

**Say**:

"See these indicators on the side? The shadow agent has noticed that there are pending leave requests and is providing context — for example, flagging that approving this leave request would leave a department below minimum staffing.

The shadow agent also has a **command surface** — you can type natural-language instructions."

> **If the CommandSurface is available**, click it and type: `show me pending leave requests`

**Say**:

"Instead of clicking through menus, the HR officer can just say what they need. The system interprets the intent, finds the data, and presents it."

### PACE Safety Model (23:00 - 25:00)

**Say**:

"When the shadow agent is about to take an action — like approving a leave request or modifying a record — it follows a safety model called **PACE**: Preview, Approve, Confirm, Exit.

- **Preview**: The system shows you what it is about to do before doing it
- **Approve**: You explicitly approve the action
- **Confirm**: The system confirms the result
- **Exit**: The interaction is complete

This means the AI never takes action without human oversight. It is always a copilot, never an autopilot. For a Japanese corporate culture that values process control and accountability, this is critical."

### Trust & Safety Chain (25:00 - 28:00)

**Say**:

"Let me explain what happens behind the scenes every time someone asks the advisory engine a question. The response goes through a **13-step safety chain**."

> You can describe these verbally, or navigate to https://arbor.terrene.foundation/admin if the QA dashboard shows this visually.

**Say**:

"Every query goes through:

1. **Input sanitisation** — cleaning the input to prevent injection attacks
2. **Rate limiting** — preventing abuse
3. **Query screening** — detecting if someone is trying to circumvent safety rules or asking about something outside the system's scope
4. **Trust genesis** — creating a cryptographic record that this query happened
5. **Anti-amnesia injection** — re-injecting safety constraints so the AI model cannot drift from its instructions
6. **Domain detection** — identifying which area of law the question relates to
7. **Knowledge base retrieval** — finding the relevant legal provisions
8. **Citation validation** — verifying that the citations are real and current
9. **Response generation** — composing the answer grounded in the retrieved provisions
10. **Confidence check** — if the system is not confident, it escalates the risk tier
11. **Content screening** — checking the response for anything inappropriate
12. **Disclaimer generation** — adding the appropriate risk-tier disclaimer
13. **Trust chain recording** — recording the full audit trail

Every single response carries this audit trail. It is called **EATP — Enterprise Agent Trust Protocol**. For any response, you can trace back: which agent contributed, what knowledge base provisions were consulted, what the confidence level was, and what safety checks were applied.

For a company with strict governance and audit requirements — which I know is important in Japanese corporate culture — this is a significant differentiator. No other HR AI product provides this level of traceability."

### Admin QA Dashboard (28:00 - 30:00)

> **Navigate to**: https://arbor.terrene.foundation/admin

**Say**:

"Finally, the admin dashboard. This is where the system administrator monitors the quality of AI advisory responses.

You can see:

- **Response quality metrics** — how many responses were green, amber, or red tier
- **Knowledge base management** — the structured legal provisions the system draws from
- **Conversation browser** — review past advisory conversations for quality assurance

This is important for governance. You are not just trusting the AI blindly — you have tools to monitor, audit, and improve it continuously."

**TRANSITION to Act 4**:

"Now, everything I have shown you is built for Singapore employment law. Let me explain why that matters for Thailand."

---

## ACT 4: THE ARCHITECTURE STORY (30:00 - 40:00)

### The Multi-Jurisdiction Architecture (30:00 - 34:00)

> If you have the architecture diagram (from 07-architecture-diagram.md) as a slide or visual, show it now. Otherwise, describe it verbally.

**Say**:

"The platform is built in layers, and this is the key insight for the Thailand conversation.

At the bottom, you have the **universal HRIS core**. Payroll, leave management, attendance, claims, recruitment, appraisals — these are universal concepts. Every country needs them. This layer does not change between jurisdictions.

Above that is the **calculator layer**. Each jurisdiction has its own statutory calculations — CPF for Singapore, Social Security Fund for Thailand, BPJS for Indonesia. These are modular. You plug in the right calculator for the right country.

Above that is the **knowledge base and specialist agents**. Singapore has 6 regulatory domains — Employment Act, CPF, Foreign Manpower, Fair Employment, Workplace Safety, and Tax. Thailand would have its own set — Labour Protection Act, Social Security Act, Revenue Code, Foreign Employment Act, Labour Relations Act, and Occupational Safety Act. These are configurable per jurisdiction.

At the top is the **trust and safety layer** — EATP, the 13-step safety chain, PACE. This is **universal**. It works the same regardless of jurisdiction. The cryptographic audit trail, the risk tiering, the escalation logic — all of that transfers directly.

The Singapore version is fully built and running in production. It is the proof that this architecture works."

### What Thailand Adaptation Looks Like (34:00 - 37:00)

**Say**:

"So what would it take to create a Thailand version?

The **HRIS core is ready** — payroll, leave, attendance, all of it works today. We would configure it for Thai statutory requirements — different holiday calendar, different leave minimums, different pay cycle conventions.

The **calculators need to be built for Thailand** — Social Security Fund contributions, personal income tax withholding at Thai progressive rates, severance pay calculations under the Labour Protection Act, overtime rates. These are well-defined formulas. Weeks of work, not months.

The **knowledge base needs Thai content** — the Labour Protection Act, Social Security Act, Revenue Code, and other Thai regulations structured in the same format as our Singapore KB. This is content work — legal research and structuring.

The **specialist agents need Thai configuration** — instead of a CPF specialist, you have a Social Security Fund specialist. Instead of an Employment Act specialist, you have a Labour Protection Act specialist. Same architecture, different content.

The trust layer, the safety chain, the admin tools, the shadow agent — all of that **transfers directly** with zero changes.

Our estimate: a functional Thailand version in **4 to 6 weeks** with the architecture already proven. Compare that to building from scratch, which would take a year or more."

### Multi-Country Vision (37:00 - 40:00)

**Say**:

"And Thailand is just the beginning. The same pattern applies to every ASEAN jurisdiction:

- **Vietnam** — Labour Code 2019, Social Insurance, PIT
- **Indonesia** — Omnibus Law, BPJS, PPh 21
- **Malaysia** — Employment Act 1955, EPF/SOCSO/EIS
- **Philippines** — Labour Code, SSS/PhilHealth/Pag-IBIG

Each country requires its own knowledge base, calculators, and specialist configuration. But the platform, the AI architecture, the trust layer, the HRIS core — all of that is built once and reused.

For a company like Ricoh that operates across ASEAN, this means one platform, one governance framework, one audit trail — adapted per jurisdiction. Your regional HR leadership gets a single pane of glass with locally accurate AI advisory in every country."

**TRANSITION to Act 5**:

"That is the vision. Let me open it up for questions and discussion."

---

## ACT 5: DISCUSSION (40:00 - 45:00)

### Opening Questions

**Say**:

"I would love to hear your thoughts. A few questions to start the conversation:

1. **What resonated most?** Was it the advisory engine, the trust and traceability story, the full HRIS, or the multi-country potential?

2. **What does your Thai HR team struggle with most today?** Is it keeping up with regulatory changes, answering employee questions, payroll accuracy, or something else?

3. **What systems does Ricoh Thailand use for HR today?** Understanding your current setup helps us think about how Arbor would fit in — whether as a replacement, a complement, or an overlay.

4. **How important is the multi-country angle?** Is this primarily about Thailand, or is there appetite for a regional rollout?"

### If Asked About Timeline

**Say**:

"For a Thailand proof-of-concept that covers the Labour Protection Act, Social Security Fund, and basic income tax — we could have something demonstrable in 4 to 6 weeks. A production-ready version with full regulatory coverage would be 2 to 3 months. The speed comes from the architecture — we are not building from scratch, we are adapting a proven platform."

### If Asked About Cost

**Say**:

"The HRIS platform itself is free — open source under the Terrene Foundation. The AI advisory intelligence layer is the premium component. We can discuss pricing models — per-employee, per-query, or flat-rate — based on what makes sense for Ricoh Thailand's scale."

### If Asked About Integration

**Say**:

"The platform has a full REST API — 120+ endpoints. It can integrate with existing systems via API. For example, if Ricoh uses SAP globally, the employee data can be synced via the API. The advisory engine can also be exposed as a standalone service — meaning your existing HR system stays in place, and Arbor becomes the intelligence layer on top."

### Closing

**Say**:

"Thank you for your time today. We will send over a brief summarising what you have seen and the architecture story. If there is interest in exploring a Thailand version, we would suggest starting with a focused proof-of-concept — pick the two or three regulatory domains that matter most to your HR team, and we build those first.

We look forward to continuing the conversation."

---

## FALLBACK PLANS

### If the advisory engine is slow (>10 seconds)

**Say** (while waiting): "The system is searching through thousands of legal provisions, cross-referencing across regulatory domains, and composing a cited response. The thoroughness is the point — it is doing in seconds what would take a junior HR officer an hour of manual research."

### If the advisory engine returns an error

**Switch to a pre-prepared backup**: "Let me show you a response we prepared earlier that demonstrates the full capability." Show a screenshot or pre-recorded video of the advisory response.

Alternatively, navigate to a different demo question. The system is likely warm after the first query.

### If the internet drops

Switch to the 5-minute backup video (T497) showing the key demo moments. Say: "Let me show you a recording of the platform in action while we reconnect."

### If a question returns unexpected results

Do not draw attention to the issue. Move to the next question naturally: "Let me show you another type of question that demonstrates a different capability."

### If someone asks a Thailand-specific question

**Say**: "Great question. The system is currently loaded with Singapore law, so I will not type that in — it would flag it as outside the system's jurisdiction, which is actually the correct safety behaviour. But to answer your question about how it would work for Thailand..." and then discuss the Thai legal equivalent verbally.

---

## THINGS TO AVOID

| Do NOT                                                  | Why                                                             |
| ------------------------------------------------------- | --------------------------------------------------------------- |
| Type any Thailand-specific question into the advisory   | Triggers MULTI_JURISDICTION escalation — looks like a rejection |
| Navigate to the Analytics page                          | May be empty or have sparse data                                |
| Navigate to the Clients page                            | "View" button is a dead end                                     |
| Show a cold-start dashboard (no data)                   | Use the pre-seeded demo company                                 |
| Dwell on Singapore acronyms without translating         | Audience is Thai — always give the Thai equivalent              |
| Say "ready for Thailand today"                          | Say "the architecture is ready; content adaptation is needed"   |
| Compare to specific competitors by name                 | Let the product speak for itself                                |
| Show the test suite or code                             | This is a business demo, not a technical review                 |
| Promise specific features without confirming they exist | Stick to what you can show live                                 |
| Rush through the advisory responses                     | The streaming + citations are the key "wow" — let them breathe  |

---

## THAI EQUIVALENTS REFERENCE

Keep this list handy for real-time translation during the demo:

| Singapore Term                  | Thai Equivalent                                             |
| ------------------------------- | ----------------------------------------------------------- |
| CPF (Central Provident Fund)    | Social Security Fund (SSF / ประกันสังคม)                    |
| Employment Act (Cap. 91)        | Labour Protection Act B.E. 2541 (พ.ร.บ.คุ้มครองแรงงาน)      |
| IRAS (Income Tax)               | Revenue Department (กรมสรรพากร)                             |
| MOM (Ministry of Manpower)      | Department of Labour Protection and Welfare (กรมสวัสดิการฯ) |
| SDL (Skills Development Levy)   | Skill Development Fund (กองทุนพัฒนาฝีมือแรงงาน)             |
| FWL (Foreign Worker Levy)       | Work Permit Fee (ค่าธรรมเนียมใบอนุญาตทำงาน)                 |
| TAFEP (Fair Employment)         | Labour Relations Committee / Labour Court                   |
| WSH (Workplace Safety)          | Occupational Safety, Health and Environment Act             |
| Wrongful dismissal (via TADM)   | Unfair dismissal (via Labour Court / ศาลแรงงาน)             |
| S Pass / Employment Pass        | Work Permit (ใบอนุญาตทำงาน) via Department of Employment    |
| Annual leave (7 days minimum)   | Annual leave (6 days minimum under LPA)                     |
| Notice period (1 day - 4 weeks) | Notice period (at least 1 pay cycle under LPA Section 17)   |
| Retrenchment benefit            | Severance pay (30 - 400 days based on tenure under LPA)     |

---

## TIMING SUMMARY

| Act | Time        | Duration | Focus                                     |
| --- | ----------- | -------- | ----------------------------------------- |
| 1   | 0:00-5:00   | 5 min    | The problem — why generic AI is dangerous |
| 2   | 5:00-20:00  | 15 min   | Live demo — dashboard, advisory, payroll  |
| 3   | 20:00-30:00 | 10 min   | Intelligence layer — shadow, trust, admin |
| 4   | 30:00-40:00 | 10 min   | Architecture story — Thailand potential   |
| 5   | 40:00-45:00 | 5 min    | Discussion and next steps                 |
