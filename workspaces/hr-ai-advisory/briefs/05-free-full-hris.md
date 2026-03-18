# Brief 05: Free Full-Service HRIS

## Vision

Arbor becomes a **free, complete HR platform** for Singapore — not just advisory, but the full operational suite: payroll calculation, CPF contribution management, leave management, payslip generation, claims processing, attendance tracking, and employee onboarding. Features that paid HRIS platforms charge $4-10/employee/month for, Arbor offers for free.

The AI shadow agent is the differentiator. Traditional HRIS platforms process payroll. Arbor processes payroll AND tells you if you're doing it right, alerts you to regulatory changes, generates your compliance documents, and answers your HR questions with cited legal provisions. Free beats paid. AI beats forms-and-tables.

## Strategic Rationale

1. **Eliminate the "additional cost" objection**: The value audit revealed that SME owners won't pay $99/month for advisory on top of their existing HRIS costs. If Arbor IS the payroll system, the comparison becomes "free + AI" vs "paid + no AI."

2. **Capture the data**: Employee records, salaries, leave balances, and payroll history are the fuel for the shadow agent's contextual intelligence. Building the HRIS in means the data is already there — no need for external integrations.

3. **Network effects**: Every employee invited to the platform is a potential future admin when they start their own company. Free employee access creates viral distribution.

4. **Moat**: The 13-step safety chain, 6-domain KB, trust lineage, and shadow agent architecture are not easily replicable. Making the HRIS free adds a price advantage on top of the technology advantage.

## What to Build (in addition to what exists)

### Payroll Engine

- Monthly payroll calculation (gross → net with CPF, SDL, levies)
- CPF submission file generation (for employer to upload to CPF Board portal)
- IR8A/IR21 tax filing data generation (for IRAS submission)
- Payslip generation (itemised, compliant with EA s88A)
- Salary history tracking

### Leave Management

- Leave application workflow (employee applies → manager approves/rejects)
- Leave balance auto-calculation based on service years (EA s88)
- Leave calendar view
- Public holiday integration (Singapore gazetted holidays)
- Prorated leave for mid-year joiners

### Claims & Expenses

- Employee expense claim submission with receipt upload
- Manager approval workflow
- Category-based tracking (transport, meals, medical, etc.)

### Attendance

- Clock in/out (web and mobile)
- Overtime tracking (Part IV EA employees)
- Timesheet approval workflow

### Employee Lifecycle

- Full onboarding workflow (admin creates employee → system generates KET → employee gets credentials)
- Probation tracking with auto-reminders
- Confirmation workflow
- Resignation/termination processing with final salary calculation
- Exit interview tracking

## Revenue Model (if free)

- **Free tier**: Full HRIS + AI advisory for up to 200 employees
- **Revenue from**: Premium features (advanced analytics, custom document templates, priority specialist escalation, SLA-backed support), Government grants (PSG), Enterprise consulting

## Constraints

- Must comply with Singapore Employment Act for all payroll calculations
- Must generate CPF-Board-compatible submission files
- Must generate IRAS-compatible IR8A data
- Payslips must meet EA s88A itemisation requirements
- All features must work with the shadow agent (voice + command surface)
- Must NOT require any external HRIS integration — this IS the HRIS

## Next Priorities (from previous session, user-confirmed)

1. Observation-to-suggestion personalization (substrate → command surface)
2. Shadow widget attention state triggering
3. Salary encryption at rest
4. Full HRIS feature buildout (this brief)
