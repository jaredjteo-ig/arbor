"""Phase 1 document templates — EA-compliant, Singapore employment law.

Each template includes:
- Structured content with placeholder fields in {{FIELD_NAME}} format
- Template metadata (type, category, description)
- Linked provision IDs referencing the knowledge base
- Required fields list for the document generation flow
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateDefinition:
    """A single document template definition."""

    name: str
    template_type: str
    category: str
    description: str
    content: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
    linked_provisions: list[str] = field(default_factory=list)
    compliance_notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Template 1: Employment Contract (Full-Time)
# ---------------------------------------------------------------------------

EMPLOYMENT_CONTRACT_FT = TemplateDefinition(
    name="Employment Contract (Full-Time)",
    template_type="contract",
    category="Contracts",
    description="EA-compliant full-time employment contract including all Key Employment Terms (KET) required under the Employment Act.",
    required_fields=[
        "company_name",
        "company_uen",
        "company_address",
        "employee_name",
        "nric_fin",
        "job_title",
        "department",
        "start_date",
        "basic_monthly_salary",
        "salary_period",
    ],
    optional_fields=[
        "probation_period_months",
        "fixed_allowances",
        "variable_allowances",
        "overtime_rate",
        "notice_period_weeks",
        "work_hours_per_day",
        "rest_day",
    ],
    linked_provisions=[
        "EA-KET",
        "EA-S95-KETs",
        "EA-S88-salary-payment",
        "EA-S10-notice",
        "EA-PART-IV-hours",
        "EA-S88A-payslip",
        "CPF-employer-obligations",
    ],
    compliance_notes=[
        "KET must be issued within 14 days of employment start (EA s95A)",
        "Salary must be paid within 7 days of salary period end (EA s21)",
        "Itemised payslip required every salary payment (EA s88A)",
        "CPF contributions start from first day of employment",
    ],
    content="""EMPLOYMENT CONTRACT

Between: {{company_name}} (UEN: {{company_uen}})
Address: {{company_address}}
(hereinafter "the Employer")

And: {{employee_name}} (NRIC/FIN: {{nric_fin}})
(hereinafter "the Employee")

Date of Contract: {{contract_date}}

─────────────────────────────────────────────────────────
1. KEY EMPLOYMENT TERMS
─────────────────────────────────────────────────────────

1.1 Job Title: {{job_title}}
1.2 Department: {{department}}
1.3 Date of Commencement: {{start_date}}
1.4 Duration of Employment: Permanent (no fixed end date)
1.5 Working Arrangements: Office-based / {{work_arrangement}}

─────────────────────────────────────────────────────────
2. PROBATION
─────────────────────────────────────────────────────────

2.1 The Employee shall serve a probation period of {{probation_period_months}} months from the commencement date.
2.2 During probation, either party may terminate with {{probation_notice_weeks}} week(s) written notice.
2.3 Upon successful completion, the Employee shall be confirmed in writing.

─────────────────────────────────────────────────────────
3. REMUNERATION
─────────────────────────────────────────────────────────

3.1 Basic Monthly Salary: S${{basic_monthly_salary}}
3.2 Salary Period: {{salary_period}}
3.3 Salary Payment Date: By the 7th day after the end of each salary period
3.4 Payment Method: Bank transfer to Employee's designated account
3.5 Fixed Allowances: {{fixed_allowances}}
3.6 Variable Allowances: {{variable_allowances}}
3.7 Overtime Payment: In accordance with Part IV of the Employment Act, where applicable

─────────────────────────────────────────────────────────
4. WORKING HOURS
─────────────────────────────────────────────────────────

4.1 Normal working hours: {{work_hours_per_day}} hours per day, {{work_days_per_week}} days per week
4.2 Rest Day: {{rest_day}} (one rest day per week, per EA s36)
4.3 Overtime: Subject to Part IV of the Employment Act. Overtime is payable at not less than 1.5x the hourly basic rate of pay.
4.4 Maximum overtime: 72 hours per month (EA s38)

─────────────────────────────────────────────────────────
5. LEAVE ENTITLEMENTS
─────────────────────────────────────────────────────────

5.1 Annual Leave: Per the Employment Act schedule (7 days in first year, increasing to 14 days by the 8th year)
5.2 Outpatient Sick Leave: 14 days per year (EA s89)
5.3 Hospitalisation Leave: 60 days per year (inclusive of outpatient sick leave) (EA s89)
5.4 Maternity Leave: 16 weeks (CDCSA, subject to eligibility)
5.5 Paternity Leave: 4 weeks (CDCSA, subject to eligibility, since 1 Jan 2025)
5.6 Childcare Leave: 6 days per year (CDCSA, subject to eligibility)
5.7 Public Holidays: 11 gazetted public holidays per year

─────────────────────────────────────────────────────────
6. CPF CONTRIBUTIONS
─────────────────────────────────────────────────────────

6.1 The Employer shall contribute to the Employee's CPF account in accordance with the rates prescribed by the Central Provident Fund Act.
6.2 The Employee's share of CPF contributions shall be deducted from monthly salary.

─────────────────────────────────────────────────────────
7. TERMINATION
─────────────────────────────────────────────────────────

7.1 Notice Period: {{notice_period_weeks}} weeks written notice by either party (EA s10)
7.2 Either party may terminate immediately by paying salary in lieu of notice.
7.3 Summary Dismissal: The Employer may dismiss the Employee without notice for misconduct after due inquiry (EA s14).
7.4 Upon termination, all outstanding salary, leave encashment, and other payments shall be made within 3 working days.

─────────────────────────────────────────────────────────
8. CONFIDENTIALITY
─────────────────────────────────────────────────────────

8.1 The Employee shall not disclose any confidential information of the Employer during and after employment.

─────────────────────────────────────────────────────────
9. GOVERNING LAW
─────────────────────────────────────────────────────────

9.1 This contract shall be governed by the laws of the Republic of Singapore.
9.2 The Employment Act (Cap 91) applies to this employment relationship.

─────────────────────────────────────────────────────────

SIGNED:

___________________________          ___________________________
For and on behalf of Employer        Employee
Name: {{authorised_signatory}}       Name: {{employee_name}}
Date: {{contract_date}}              Date: {{contract_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 2: Employment Contract (Part-Time)
# ---------------------------------------------------------------------------

EMPLOYMENT_CONTRACT_PT = TemplateDefinition(
    name="Employment Contract (Part-Time)",
    template_type="contract",
    category="Contracts",
    description="EA-compliant part-time employment contract with pro-rated entitlements calculated per the Employment Act (Part-Time Employees) Regulations.",
    required_fields=[
        "company_name",
        "company_uen",
        "employee_name",
        "nric_fin",
        "job_title",
        "start_date",
        "hourly_rate",
        "hours_per_week",
    ],
    optional_fields=["days_per_week", "specific_work_days"],
    linked_provisions=[
        "EA-KET",
        "EA-PT-REGULATIONS",
        "EA-S66A-part-time",
        "CPF-employer-obligations",
    ],
    compliance_notes=[
        "Part-time employee: works <35 hours/week (EA Part-Time Regulations)",
        "Leave entitlements pro-rated based on hours worked vs full-time equivalent",
        "CPF contributions apply at same rates as full-time employees",
    ],
    content="""PART-TIME EMPLOYMENT CONTRACT

Between: {{company_name}} (UEN: {{company_uen}})
And: {{employee_name}} (NRIC/FIN: {{nric_fin}})

1. POSITION: {{job_title}}
2. COMMENCEMENT: {{start_date}}
3. WORKING HOURS: {{hours_per_week}} hours per week, {{days_per_week}} days per week
4. SPECIFIC DAYS: {{specific_work_days}}
5. HOURLY RATE: S${{hourly_rate}}
6. PAYMENT: Monthly, by bank transfer within 7 days of salary period end

7. PRO-RATED ENTITLEMENTS:
   Leave entitlements are pro-rated based on actual hours worked relative to a comparable full-time employee, in accordance with the Employment Act (Part-Time Employees) Regulations.

8. CPF: Contributions at prescribed rates apply.
9. NOTICE: {{notice_period_weeks}} weeks by either party.
10. OTHER TERMS: As per the Employment Act and this company's employment handbook.

SIGNED:
___________________________          ___________________________
Employer                             Employee
Date: {{contract_date}}              Date: {{contract_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 3: Key Employment Terms (Standalone KET)
# ---------------------------------------------------------------------------

KEY_EMPLOYMENT_TERMS = TemplateDefinition(
    name="Key Employment Terms (KET)",
    template_type="ket",
    category="Contracts",
    description="Standalone KET document compliant with EA s95A, issued within 14 days of employment start.",
    required_fields=[
        "company_name",
        "employee_name",
        "job_title",
        "start_date",
        "basic_monthly_salary",
        "salary_period",
        "work_hours_per_day",
        "rest_day",
        "notice_period_weeks",
    ],
    optional_fields=["fixed_allowances", "deductions"],
    linked_provisions=["EA-S95-KETs", "EA-KET", "EA-S88A-payslip"],
    compliance_notes=[
        "Must be issued within 14 days of employment start (EA s95A)",
        "Must include all items listed in EA Fourth Schedule",
        "Non-compliance: Fine up to $5,000 per offence",
    ],
    content="""KEY EMPLOYMENT TERMS
(Issued pursuant to section 95A of the Employment Act)

Employer: {{company_name}}
Employee: {{employee_name}}

1. Job title and main duties: {{job_title}}
2. Date of commencement: {{start_date}}
3. Duration of employment: {{employment_duration}}
4. Working arrangements: {{work_arrangement}}
5. Working hours per day: {{work_hours_per_day}}
6. Number of working days per week: {{work_days_per_week}}
7. Rest day: {{rest_day}}

SALARY:
8. Basic salary: S${{basic_monthly_salary}} per {{salary_period}}
9. Fixed allowances: {{fixed_allowances}}
10. Fixed deductions: {{deductions}}
11. Salary period: {{salary_period}}
12. Overtime payment period: {{overtime_period}}

LEAVE:
13. Annual leave: Per EA schedule (7-14 days based on years of service)
14. Sick leave: 14 outpatient + 60 hospitalisation days (EA s89)
15. Other leave: As per Employment Act and company policy

MEDICAL BENEFITS:
16. Type and amount: {{medical_benefits}}

PROBATION:
17. Period: {{probation_period_months}} months
18. Conditions during probation: {{probation_conditions}}

NOTICE PERIOD:
19. For termination by employer or employee: {{notice_period_weeks}} weeks

Date of issue: {{issue_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 4: Annual Leave Policy
# ---------------------------------------------------------------------------

ANNUAL_LEAVE_POLICY = TemplateDefinition(
    name="Annual Leave Policy",
    template_type="policy",
    category="Policies",
    description="Company annual leave policy aligned with EA leave schedule requirements.",
    required_fields=["company_name"],
    optional_fields=["additional_leave_days", "carry_forward_limit"],
    linked_provisions=["EA-PART-X-annual-leave", "EA-S43-annual-leave"],
    compliance_notes=[
        "Minimum annual leave per EA: 7 days (1st year) to 14 days (8th+ year)",
        "Company may offer more than statutory minimum",
        "Pro-ration applies for incomplete years of service",
    ],
    content="""ANNUAL LEAVE POLICY
{{company_name}}

1. STATUTORY ENTITLEMENT
   All employees covered by the Employment Act are entitled to paid annual leave based on years of service:
   - 1st year: 7 days
   - 2nd year: 8 days
   - 3rd year: 9 days
   - 4th year: 10 days
   - 5th year: 11 days
   - 6th year: 12 days
   - 7th year: 13 days
   - 8th year and above: 14 days

2. ELIGIBILITY
   - Employees must have completed 3 months of service to be entitled to annual leave.
   - For employees with less than 12 months of service, leave is pro-rated.

3. APPLICATION
   - Annual leave must be applied for and approved in advance.
   - Minimum notice: {{min_notice_days}} working days for leave of 3+ days.
   - Leave during peak periods is subject to business needs.

4. CARRY FORWARD
   - Unused leave may be carried forward up to {{carry_forward_limit}} days.
   - Carried-forward leave must be used within Q1 of the following year.

5. ENCASHMENT
   - Annual leave not taken due to operational requirements may be encashed upon approval.
   - Upon termination, unused accrued leave shall be encashed at the gross daily rate of pay.

Effective Date: {{effective_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 5: Sick Leave Policy
# ---------------------------------------------------------------------------

SICK_LEAVE_POLICY = TemplateDefinition(
    name="Sick Leave Policy",
    template_type="policy",
    category="Policies",
    description="Company sick leave and medical certificate policy per EA s89.",
    required_fields=["company_name"],
    optional_fields=["panel_clinic_details"],
    linked_provisions=["EA-S89-sick-leave", "EA-S89-medical-certificate"],
    compliance_notes=[
        "EA s89: 14 days outpatient + 60 days hospitalisation (inclusive)",
        "MC must be from company-designated doctor or government hospital",
        "Employer must not dismiss employee on valid MC",
    ],
    content="""SICK LEAVE POLICY
{{company_name}}

1. ENTITLEMENT (Employment Act s89)
   Employees who have served for at least 6 months are entitled to:
   - 14 days outpatient sick leave per year
   - 60 days hospitalisation leave per year (inclusive of the 14 outpatient days)

   For employees with 3-6 months service, entitlement is pro-rated.

2. MEDICAL CERTIFICATE (MC)
   - A valid MC from a registered medical practitioner is required for all sick leave.
   - MCs from the company's panel clinic(s) are preferred: {{panel_clinic_details}}
   - MCs from government hospitals and polyclinics are always accepted.

3. NOTIFICATION
   - Employees must inform their supervisor as soon as possible, and no later than {{notification_hours}} hours after the start of the working day.
   - The original MC must be submitted to HR within {{mc_submission_days}} working days.

4. PAID SICK LEAVE
   Sick leave is paid at the gross rate of pay.

5. ABUSE
   Abuse of sick leave may result in disciplinary action including termination.

Effective Date: {{effective_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 6: Termination Letter (with notice)
# ---------------------------------------------------------------------------

TERMINATION_LETTER = TemplateDefinition(
    name="Termination Letter (With Notice)",
    template_type="letter",
    category="Letters",
    description="Employer termination letter with notice period per EA s10, including final payment details.",
    required_fields=[
        "company_name",
        "employee_name",
        "job_title",
        "termination_date",
        "last_working_day",
        "notice_period_weeks",
        "reason_for_termination",
    ],
    optional_fields=["encashment_details", "return_of_property"],
    linked_provisions=[
        "EA-S10-notice",
        "EA-S11-salary-in-lieu",
        "EA-S22-final-payment",
    ],
    compliance_notes=[
        "Notice period must match contract or EA minimum (EA s10)",
        "Final salary + leave encashment within 3 working days of last day (EA s22)",
        "Tax clearance (IR21) must be filed with IRAS at least 1 month before cessation",
    ],
    content="""TERMINATION OF EMPLOYMENT

{{company_name}}
Date: {{letter_date}}

Dear {{employee_name}},

RE: TERMINATION OF EMPLOYMENT

We regret to inform you that your employment as {{job_title}} with {{company_name}} will be terminated.

Reason: {{reason_for_termination}}

In accordance with your employment contract, you are hereby given {{notice_period_weeks}} weeks' notice. Your last day of employment will be {{last_working_day}}.

FINAL PAYMENT:
Upon your last working day, you will receive:
- Salary up to and including {{last_working_day}}
- Encashment of {{unused_leave_days}} days unused annual leave
- Any other outstanding payments

Total final payment will be made within 3 working days of your last day, as required under section 22 of the Employment Act.

OBLIGATIONS:
- Please return all company property by {{last_working_day}}
- You remain bound by confidentiality obligations

We thank you for your service and wish you well.

Yours sincerely,

___________________________
{{authorised_signatory}}
{{signatory_title}}
{{company_name}}

Acknowledgement:
I, {{employee_name}}, acknowledge receipt of this letter.

Signature: _______________ Date: _______________
""",
)


# ---------------------------------------------------------------------------
# Template 7: Resignation Acceptance Letter
# ---------------------------------------------------------------------------

RESIGNATION_ACCEPTANCE = TemplateDefinition(
    name="Resignation Acceptance Letter",
    template_type="letter",
    category="Letters",
    description="Formal acceptance of employee resignation with confirmation of last working day and final settlement details.",
    required_fields=[
        "company_name",
        "employee_name",
        "job_title",
        "resignation_date",
        "last_working_day",
    ],
    optional_fields=["handover_instructions"],
    linked_provisions=["EA-S10-notice", "EA-S22-final-payment"],
    compliance_notes=[
        "Confirm last working day aligns with notice period",
        "Final payment within 3 working days (EA s22)",
    ],
    content="""ACCEPTANCE OF RESIGNATION

{{company_name}}
Date: {{letter_date}}

Dear {{employee_name}},

RE: ACCEPTANCE OF RESIGNATION

We acknowledge receipt of your resignation letter dated {{resignation_date}} from your position as {{job_title}}.

We accept your resignation. Your last day of employment will be {{last_working_day}}, following the completion of your notice period.

HANDOVER:
Please ensure all work handover is completed by your last working day.
{{handover_instructions}}

FINAL SETTLEMENT:
Your final salary, leave encashment, and any other outstanding payments will be processed within 3 working days of your last day.

We thank you for your contributions and wish you success in your future endeavours.

Yours sincerely,

___________________________
{{authorised_signatory}}
{{signatory_title}}
{{company_name}}
""",
)


# ---------------------------------------------------------------------------
# Template 8: Warning Letter (1st/2nd/Final)
# ---------------------------------------------------------------------------

WARNING_LETTER = TemplateDefinition(
    name="Warning Letter",
    template_type="letter",
    category="Letters",
    description="Formal warning letter for misconduct or poor performance. Supports 1st, 2nd, and final warning.",
    required_fields=[
        "company_name",
        "employee_name",
        "job_title",
        "warning_level",
        "incident_date",
        "incident_description",
        "expected_improvement",
    ],
    optional_fields=["previous_warnings", "improvement_deadline"],
    linked_provisions=[
        "EA-S14-misconduct-dismissal",
        "TGFEP-fair-dismissal",
    ],
    compliance_notes=[
        "Due inquiry must be conducted before summary dismissal (EA s14)",
        "Progressive discipline recommended (TGFEP)",
        "Keep dated copies of all warnings for records",
    ],
    content="""{{warning_level}} WARNING LETTER

{{company_name}}
Date: {{letter_date}}

Dear {{employee_name}},

RE: {{warning_level}} WARNING — {{incident_category}}

This letter serves as a {{warning_level}} warning regarding the following:

INCIDENT:
Date: {{incident_date}}
Description: {{incident_description}}

{{previous_warnings}}

EXPECTED IMPROVEMENT:
{{expected_improvement}}

You are required to demonstrate improvement by {{improvement_deadline}}.

CONSEQUENCES:
Failure to improve may result in further disciplinary action, up to and including termination of employment.

Please sign below to acknowledge receipt of this warning. Your signature acknowledges receipt only and does not constitute agreement with the contents.

Yours sincerely,

___________________________
{{authorised_signatory}}
{{signatory_title}}

Acknowledgement:
I, {{employee_name}}, acknowledge receipt of this warning letter.

Signature: _______________ Date: _______________
""",
)


# ---------------------------------------------------------------------------
# Template 9: FWA Request Form
# ---------------------------------------------------------------------------

FWA_REQUEST_FORM = TemplateDefinition(
    name="FWA Request Form",
    template_type="form",
    category="Forms",
    description="Flexible Work Arrangement request form per TG-FWAR guidelines with structured request and response workflow.",
    required_fields=[
        "company_name",
        "employee_name",
        "job_title",
        "department",
        "fwa_type",
        "proposed_start_date",
        "reason",
    ],
    optional_fields=["proposed_schedule", "impact_assessment"],
    linked_provisions=[
        "TGFWAR-request-process",
        "TGFWAR-employer-response",
        "TGFWAR-reasonable-grounds",
    ],
    compliance_notes=[
        "Employer must respond within 2 months of receiving FWA request (TG-FWAR)",
        "Rejection must state reasonable business grounds",
        "Employee has right to appeal",
    ],
    content="""FLEXIBLE WORK ARRANGEMENT REQUEST FORM
{{company_name}}

SECTION A: EMPLOYEE DETAILS
Name: {{employee_name}}
Job Title: {{job_title}}
Department: {{department}}
Date of Request: {{request_date}}

SECTION B: FWA REQUEST
Type of FWA requested:
[ ] Flexi-time (varying start/end times)
[ ] Flexi-load (reduced workload/hours)
[ ] Flexi-place (remote/hybrid work)
[ ] Compressed work week
[ ] Job sharing
[ ] Other: {{fwa_type}}

Proposed Start Date: {{proposed_start_date}}
Proposed End Date / Duration: {{proposed_end_date}}

Proposed Schedule:
{{proposed_schedule}}

Reason for Request:
{{reason}}

How I plan to manage my responsibilities:
{{impact_assessment}}

Employee Signature: _______________ Date: _______________

─────────────────────────────────────────────────────────

SECTION C: EMPLOYER RESPONSE (to be completed within 2 months)

Decision: [ ] Approved [ ] Approved with modifications [ ] Rejected

If approved with modifications:
{{modifications}}

If rejected, reasonable business grounds:
{{rejection_grounds}}

Manager: _______________ Date: _______________
HR: _______________ Date: _______________

SECTION D: APPEAL (if applicable)
Employee appeal: {{appeal_text}}
Final decision: {{final_decision}}
""",
)


# ---------------------------------------------------------------------------
# Template 10: FWA Policy
# ---------------------------------------------------------------------------

FWA_POLICY = TemplateDefinition(
    name="Flexible Work Arrangement Policy",
    template_type="policy",
    category="Policies",
    description="Company FWA policy aligned with TG-FWAR guidelines.",
    required_fields=["company_name"],
    optional_fields=["eligible_roles", "excluded_roles"],
    linked_provisions=[
        "TGFWAR-request-process",
        "TGFWAR-employer-response",
        "TGFWAR-reasonable-grounds",
        "TGFWAR-appeal",
    ],
    compliance_notes=[
        "TG-FWAR: All employees can request FWA from 1 December 2024",
        "Employer must respond within 2 months",
        "Rejection must state reasonable business grounds",
    ],
    content="""FLEXIBLE WORK ARRANGEMENT POLICY
{{company_name}}

1. PURPOSE
   This policy sets out the company's framework for Flexible Work Arrangements (FWA) in accordance with the Tripartite Guidelines on FWA Requests (TG-FWAR).

2. TYPES OF FWA
   - Flexi-time: Varying start and end times
   - Flexi-load: Reduced workload or job sharing
   - Flexi-place: Working from home or alternative locations
   - Compressed work week
   - Other arrangements as agreed

3. ELIGIBILITY
   All employees may submit an FWA request. Approval is subject to business needs.

4. REQUEST PROCESS
   a) Submit the FWA Request Form to your direct supervisor and HR
   b) Include: type of FWA, proposed schedule, duration, reason, and impact plan
   c) Employer will respond within 2 months of receiving the request

5. ASSESSMENT CRITERIA
   Requests will be assessed based on:
   - Impact on team productivity and business operations
   - Nature of the role and work requirements
   - Ability to maintain service levels
   - Fair and consistent treatment across similar roles

6. REJECTION
   If a request is rejected, the employer will:
   - Provide reasonable business grounds in writing
   - Discuss alternative arrangements where possible
   - Inform the employee of the right to appeal

7. APPEAL
   Employees may appeal a rejected FWA request within {{appeal_days}} working days.

8. REVIEW
   Approved FWA arrangements will be reviewed every {{review_months}} months.

Effective Date: {{effective_date}}
""",
)


# ---------------------------------------------------------------------------
# Template 11: Expense Claims Form
# ---------------------------------------------------------------------------

EXPENSE_CLAIMS_FORM = TemplateDefinition(
    name="Expense Claims Form",
    template_type="form",
    category="Forms",
    description="Standard expense reimbursement form with receipt requirements and approval workflow.",
    required_fields=["company_name", "employee_name", "department"],
    optional_fields=["expense_categories", "approval_limit"],
    linked_provisions=["EA-S27-deductions"],
    compliance_notes=[
        "EA s27: Deductions from salary require written consent",
        "Keep receipts for tax deduction claims (IRAS)",
    ],
    content="""EXPENSE CLAIMS FORM
{{company_name}}

Employee Name: {{employee_name}}
Department: {{department}}
Claim Period: {{claim_period_start}} to {{claim_period_end}}

─────────────────────────────────────────────────────────
EXPENSES
─────────────────────────────────────────────────────────

| # | Date | Description | Category | Amount (S$) | Receipt |
|---|------|-------------|----------|-------------|---------|
| 1 | {{date_1}} | {{desc_1}} | {{cat_1}} | {{amt_1}} | [ ] |
| 2 | {{date_2}} | {{desc_2}} | {{cat_2}} | {{amt_2}} | [ ] |
| 3 | {{date_3}} | {{desc_3}} | {{cat_3}} | {{amt_3}} | [ ] |
| 4 | {{date_4}} | {{desc_4}} | {{cat_4}} | {{amt_4}} | [ ] |
| 5 | {{date_5}} | {{desc_5}} | {{cat_5}} | {{amt_5}} | [ ] |

TOTAL: S${{total_amount}}

─────────────────────────────────────────────────────────
DECLARATION
I declare that the above expenses were incurred for company business purposes and that all receipts are attached.

Employee Signature: _______________ Date: _______________

─────────────────────────────────────────────────────────
APPROVAL
Supervisor: _______________ Date: _______________
Finance: _______________ Date: _______________
""",
)


# ---------------------------------------------------------------------------
# Template 12: Timesheet Template
# ---------------------------------------------------------------------------

TIMESHEET_TEMPLATE = TemplateDefinition(
    name="Timesheet Template",
    template_type="form",
    category="Forms",
    description="Weekly timesheet for recording working hours, overtime, and rest days per EA Part IV requirements.",
    required_fields=["company_name", "employee_name", "week_starting"],
    optional_fields=[],
    linked_provisions=[
        "EA-PART-IV-hours",
        "EA-S38-max-overtime",
        "EA-S37-overtime-rate",
    ],
    compliance_notes=[
        "EA Part IV: Max 8 hours/day or 44 hours/week",
        "Overtime: max 72 hours/month (EA s38)",
        "Overtime rate: not less than 1.5x hourly basic rate (EA s37)",
        "Applies to workmen (any salary) and non-workmen earning ≤$2,600/month",
    ],
    content="""WEEKLY TIMESHEET
{{company_name}}

Employee: {{employee_name}}
Department: {{department}}
Week Starting: {{week_starting}}

─────────────────────────────────────────────────────────

| Day       | Date | Start | End   | Break | Hours | OT Hours | Notes    |
|-----------|------|-------|-------|-------|-------|----------|----------|
| Monday    |      |       |       |       |       |          |          |
| Tuesday   |      |       |       |       |       |          |          |
| Wednesday |      |       |       |       |       |          |          |
| Thursday  |      |       |       |       |       |          |          |
| Friday    |      |       |       |       |       |          |          |
| Saturday  |      |       |       |       |       |          |          |
| Sunday    |      |       |       |       |       |          | Rest Day |

─────────────────────────────────────────────────────────
TOTALS
Normal Hours: _____ / 44
Overtime Hours: _____ / 72 (monthly limit)
Rest Day Work: _____

Employee Signature: _______________ Date: _______________
Supervisor Signature: _______________ Date: _______________
""",
)


# ---------------------------------------------------------------------------
# All templates collected
# ---------------------------------------------------------------------------

TEMPLATES: list[TemplateDefinition] = [
    EMPLOYMENT_CONTRACT_FT,
    EMPLOYMENT_CONTRACT_PT,
    KEY_EMPLOYMENT_TERMS,
    ANNUAL_LEAVE_POLICY,
    SICK_LEAVE_POLICY,
    TERMINATION_LETTER,
    RESIGNATION_ACCEPTANCE,
    WARNING_LETTER,
    FWA_REQUEST_FORM,
    FWA_POLICY,
    EXPENSE_CLAIMS_FORM,
    TIMESHEET_TEMPLATE,
]


def get_template_by_type(template_type: str) -> list[TemplateDefinition]:
    """Return all templates of a given type (contract, policy, letter, form, ket)."""
    return [t for t in TEMPLATES if t.template_type == template_type]
