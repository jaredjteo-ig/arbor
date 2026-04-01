# ChatGPT vs Arbor — Side-by-Side Comparison

**Purpose**: Demonstrate why a purpose-built, grounded advisory engine is fundamentally different from a general-purpose LLM for HR compliance questions.

**Usage**: Show during Act 1 of the demo, or keep as a leave-behind reference.

---

## Scenario 1: Factual Question — CPF Contribution Rates

**Question**: "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000 per month?"

### ChatGPT Response (Typical)

> For a Singapore citizen aged 35, the CPF contribution rates are:
>
> - Employee: 20% of ordinary wages
> - Employer: 17% of ordinary wages
>
> So for a $5,000 salary:
>
> - Employee contribution: $1,000
> - Employer contribution: $850
> - Total: $1,850
>
> These rates apply to employees aged 55 and below. The rates decrease for older employees.

**What is missing**:

- No citation to the CPF Act or any specific statutory table
- No mention of which CPF Act section or schedule defines these rates
- No indication of which wage ceiling applies (Ordinary Wage ceiling is $6,800/month as of 2024)
- No breakdown by CPF account (Ordinary, Special, Medisave)
- No mention that rates change with age bands (not just "55 and below")
- No confidence indicator — presented with the same certainty as if asking about the weather
- If the rates were wrong, there would be no way to verify without independent research

**Risk**: The top-line numbers happen to be approximately correct for this common case, which makes ChatGPT seem reliable. But for edge cases — a 58-year-old PR in their 3rd year, an employee earning above the Additional Wage ceiling — ChatGPT frequently gives incorrect rates with no indication of uncertainty.

### Arbor Response

> **[GREEN risk tier]**
>
> For a Singapore citizen aged 35 earning $5,000/month, the CPF contribution rates are:
>
> **Employee contribution**: 20.00% = **$1,000.00**
> **Employer contribution**: 17.00% = **$850.00**
> **Total CPF**: **$1,850.00**
>
> Breakdown by account:
>
> - Ordinary Account (OA): $575.00 (23.00% of total wage)
> - Special Account (SA): $175.00 (7.00% of total wage)
> - Medisave Account (MA): $200.00 (8.00% of total wage)
>
> _[Calculator: calculate_cpf — deterministic computation from CPF contribution rate tables]_
>
> **Legal basis**: CPF Act (Cap. 36), First Schedule — Rates of contributions. The rates above apply to employees aged 35 and below who are Singapore citizens, for ordinary wages up to the OW ceiling of $6,800/month.
>
> **Disclaimer**: This is for general information. For complex cases involving multiple employers, additional wages above the AW ceiling ($102,000/year), or voluntary contributions, consult CPF Board directly.

**What Arbor provides that ChatGPT does not**:

| Dimension                | ChatGPT       | Arbor                                                  |
| ------------------------ | ------------- | ------------------------------------------------------ |
| **Source citation**      | None          | CPF Act (Cap. 36), First Schedule                      |
| **Calculation method**   | LLM inference | Deterministic calculator (zero AI, exact arithmetic)   |
| **Account breakdown**    | Not provided  | OA/SA/MA split with exact amounts                      |
| **Wage ceiling context** | Not mentioned | OW ceiling of $6,800 noted as boundary condition       |
| **Risk tier**            | None          | GREEN — factual, well-established, low risk            |
| **Edge case warning**    | None          | Disclaimer about multi-employer, AW ceiling, voluntary |
| **Verifiability**        | Cannot verify | Citation points to exact statutory table for audit     |
| **Audit trail**          | None          | EATP trust chain — who asked, what was retrieved, when |

---

## Scenario 2: Guidance Question — Termination Process

**Question**: "What is the minimum notice period for terminating an employee who has worked for 3 years?"

### ChatGPT Response (Typical)

> In Singapore, the minimum notice period for terminating an employee depends on the length of service:
>
> - Less than 26 weeks: 1 day
> - 26 weeks to less than 2 years: 1 week
> - 2 years to less than 5 years: 2 weeks
> - 5 years or more: 4 weeks
>
> For an employee who has worked for 3 years, the minimum notice period is **2 weeks**.
>
> Note that the employment contract may specify a longer notice period, which would take precedence.

**What is missing**:

- No citation to the Employment Act or specific section
- No mention that this applies to employees covered by the Employment Act (there are exclusions)
- No mention that notice must be the same for both employer and employee
- No mention of payment in lieu of notice as an alternative
- No guidance on what constitutes valid notice (written? verbal?)
- No risk assessment — termination is inherently a sensitive HR action
- No warning about wrongful dismissal risk if proper process is not followed

**Risk**: The numbers are correct for this case. But the answer implies that giving 2 weeks notice is sufficient — it says nothing about the process requirements, documentation needs, or the distinction between termination with cause vs. without cause. An HR officer who relies on this answer alone could follow the letter (2 weeks notice) while missing critical process steps.

### Arbor Response

> **[AMBER risk tier]**
>
> For an employee with 3 years of continuous service, the minimum notice period is **2 weeks**, per Section 10(2) of the Employment Act (Cap. 91).
>
> **Notice period table** (Employment Act, Section 10):
> | Service Length | Minimum Notice |
> | ------------------------- | -------------- |
> | Less than 26 weeks | 1 day |
> | 26 weeks to < 2 years | 1 week |
> | 2 years to < 5 years | 2 weeks |
> | 5 years or more | 4 weeks |
>
> **Important considerations**:
>
> 1. **Contract prevails if longer**: If the employment contract specifies a longer notice period, the contract period applies (Section 10(3)).
> 2. **Payment in lieu**: Either party may pay salary in lieu of notice (Section 11).
> 3. **Written notice**: Notice should be given in writing for documentation purposes.
> 4. **No notice required for cause**: Termination for misconduct under Section 14 does not require notice, but a formal inquiry must be conducted first.
>
> **Legal basis**: Employment Act (Cap. 91), Sections 10-11. This applies to employees covered under the Employment Act.
>
> **Disclaimer**: Termination carries legal risk. If the circumstances involve any dispute, performance issues, or potential claims of wrongful dismissal, consult a qualified employment lawyer before proceeding.

**What Arbor provides that ChatGPT does not**:

| Dimension                   | ChatGPT                       | Arbor                                                  |
| --------------------------- | ----------------------------- | ------------------------------------------------------ |
| **Source citation**         | None                          | Employment Act (Cap. 91), Sections 10-11               |
| **Risk tier**               | None                          | AMBER — termination is inherently sensitive            |
| **Process guidance**        | Minimal ("contract prevails") | Written notice, inquiry for cause, payment in lieu     |
| **Wrongful dismissal flag** | Not mentioned                 | Explicit warning to consult lawyer if disputed         |
| **Coverage scope**          | Not mentioned                 | Notes EA coverage requirement                          |
| **Professional referral**   | None                          | Explicit recommendation to consult lawyer when at risk |

---

## Scenario 3: High-Risk Question — Wrongful Dismissal

**Question**: "An employee claims they were wrongfully dismissed after refusing to work overtime. What should I do?"

### ChatGPT Response (Typical)

> If an employee claims wrongful dismissal after refusing overtime, here are some steps you should consider:
>
> 1. **Review the employment contract** to check if overtime is a contractual requirement
> 2. **Check the Employment Act** — under Part IV, employees cannot be required to work more than 72 hours of overtime per month
> 3. **Document everything** — keep records of the overtime request, the refusal, and the dismissal decision
> 4. **Consider mediation** — you can approach TADM (Tripartite Alliance for Dispute Management) for mediation
> 5. **Seek legal advice** if the matter escalates
>
> It's important to note that dismissing an employee solely for refusing overtime could be considered wrongful dismissal under Singapore law.

**What is missing**:

- No risk classification — this is treated with the same casual tone as a question about leave entitlement
- No citation to specific sections (which part of Part IV? what section governs overtime limits?)
- No mention of Section 38 (overtime limits) or Section 14 (dismissal for misconduct — and why refusal of overtime may NOT qualify as misconduct)
- No mention of potential penalties or employer liability
- No structured action plan with priorities and deadlines
- No mention of the Employment Claims Tribunal (ECT) process
- No mention that the employer's next actions are legally significant — wrong moves now could strengthen the employee's claim
- The tone suggests this is a routine matter when it is in fact a legal minefield

**Risk**: This is the most dangerous scenario. The answer sounds reasonable and gives broadly correct directional advice. But an HR officer following these steps in order — reviewing the contract first, then checking the Act — is wasting critical time. The immediate priority should be: stop all further adverse action against the employee, preserve all records, and engage legal counsel. ChatGPT's casual bullet-point format does not communicate the urgency or legal risk.

### Arbor Response

> **[RED risk tier]**
>
> **This situation involves significant legal risk. The following information is for general awareness only. You should engage a qualified employment lawyer before taking any further action regarding this employee.**
>
> **Immediate actions (do these now)**:
>
> 1. **Do not take any further adverse action** against the employee — no further communications about the dismissal, no changes to access or benefits until you have legal advice
> 2. **Preserve all records** — the overtime request, the employee's refusal, all communications leading to the dismissal decision, the termination letter
> 3. **Engage a qualified employment lawyer** experienced in wrongful dismissal claims
>
> **Legal context**:
>
> The employee may have grounds for a wrongful dismissal claim under Section 14 of the Employment Act. Key considerations:
>
> - **Overtime limits**: Under Section 38 of the Employment Act, an employee covered by Part IV cannot be required to work more than 72 hours of overtime per month. If the overtime request exceeded this limit, the employee's refusal was legally protected.
> - **Misconduct standard**: Dismissal under Section 14 requires the employee to have committed misconduct. Refusing overtime that exceeds statutory limits is NOT misconduct.
> - **Wrongful dismissal claim**: The employee can file a claim with the **Tripartite Alliance for Dispute Management (TADM)** within one month of dismissal. If mediation fails, the matter proceeds to the **Employment Claims Tribunal (ECT)**.
> - **Employer liability**: If the dismissal is found to be wrongful, the employer may be ordered to reinstate the employee or pay compensation.
>
> **Legal basis**: Employment Act (Cap. 91), Sections 14 (dismissal), 38 (overtime limits), Part IV (conditions of service). Tripartite Guidelines on Wrongful Dismissal.
>
> **Professional referral**: This matter requires qualified legal counsel. Contact the Law Society of Singapore (tel: 6538 2500) for a referral, or approach TADM directly (tel: 6838 7969).
>
> **Disclaimer**: This information is for general awareness only and does not constitute legal advice. The specific circumstances of the dismissal, the employee's coverage under the Employment Act, and the details of the overtime request all affect the legal position. Do not rely on this information alone.

**What Arbor provides that ChatGPT does not**:

| Dimension                   | ChatGPT                          | Arbor                                                     |
| --------------------------- | -------------------------------- | --------------------------------------------------------- |
| **Risk classification**     | None — same tone as any question | RED — immediately signals danger                          |
| **Urgency communication**   | Casual bullet list               | "Do these now" with prioritised immediate actions         |
| **Specific legal sections** | Vague ("Part IV")                | Sections 14, 38, Part IV with specific applicability      |
| **TADM/ECT process**        | Mentioned in passing             | Timeline (one month), escalation path, contact numbers    |
| **Protective guidance**     | None                             | "Do not take further adverse action" — legally critical   |
| **Professional referral**   | Generic "seek legal advice"      | Specific contacts: Law Society, TADM with phone numbers   |
| **Disclaimer prominence**   | None                             | Prominent, risk-appropriate disclaimer                    |
| **Audit trail**             | None                             | EATP trust chain — traceable if this matter goes to court |

---

## Summary: Why This Matters

| Capability                     | ChatGPT         | Arbor                                    |
| ------------------------------ | --------------- | ---------------------------------------- |
| **Risk awareness**             | None            | 3-tier system (GREEN / AMBER / RED)      |
| **Legal citations**            | None            | Specific sections of specific Acts       |
| **Deterministic calculations** | LLM-generated   | Calculator tools (zero AI, exact math)   |
| **Professional referral**      | Generic         | Specific contacts with phone numbers     |
| **Escalation for danger**      | Never           | Automatic for litigation, discrimination |
| **Audit trail**                | None            | EATP cryptographic trust lineage         |
| **Knowledge base currency**    | Training cutoff | Structured KB with version tracking      |
| **Safety chain**               | None            | 13 steps, every query, every time        |
| **Disclaimer appropriateness** | None            | Risk-tiered, legally calibrated          |

The core difference: ChatGPT gives you an answer. Arbor gives you an answer you can **trust, verify, and defend** — with a clear signal when you should stop trusting the AI and call a lawyer.
