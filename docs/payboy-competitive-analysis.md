# Payboy Singapore: Complete Feature Set Analysis

Exhaustive feature-by-feature breakdown of Payboy (payboy.biz) across all modules, based on their support documentation (support.payboy.biz) and marketing pages.

---

## MODULE 1: PAYROLL

### 1.1 Payroll Settings

| Setting                                     | Type     | Details                                                                                               |
| ------------------------------------------- | -------- | ----------------------------------------------------------------------------------------------------- |
| Payment periods per month                   | Number   | Number of pay periods per month (e.g., 1 = monthly, 2 = bi-monthly)                                   |
| Email notification on payday                | Toggle   | Send email to employees when payslips are published                                                   |
| Advance notification timing                 | Number   | Up to 30 days before payday                                                                           |
| SDL opt-in                                  | Checkbox | Opt-in for Skills Development Levy (0.25% of gross, min $2, max $11.25, capped at first $4,500 wages) |
| SHG opt-in                                  | Checkbox | Opt-in for Self-Help Group contributions                                                              |
| Display payslip IDs                         | Checkbox | Show payslip IDs to employees                                                                         |
| Attach PDF to notification email            | Checkbox | Attach payslip PDF to notification email                                                              |
| Password-protect PDF                        | Checkbox | Password-protect payslip PDF files                                                                    |
| Include employee address on payslip         | Checkbox | Show home address on payslips                                                                         |
| Combine pay items by type                   | Checkbox | Consolidate Salary, Reimbursements, Additions, Deductions into grouped view                           |
| Display paid days                           | Checkbox | Show number of paid days on payslip                                                                   |
| Show leave days remaining                   | Checkbox | Display annual leave balance on payslip                                                               |
| Enable payslip module on employee portal    | Checkbox | Toggle employee access to payslips                                                                    |
| Display countdown to payday                 | Checkbox | Show payday countdown on employee portal                                                              |
| Allow employees to request ad-hoc pay items | Checkbox | Employees can request additional pay items                                                            |
| Allow managers to request ad-hoc pay items  | Checkbox | Managers can request additional pay items for subordinates                                            |

### 1.2 Pay Scheme Templates

| Field                      | Type     | Details                                                                 |
| -------------------------- | -------- | ----------------------------------------------------------------------- |
| Name                       | Text     | Template identifier                                                     |
| Pay Type                   | Dropdown | Monthly, Daily, Hourly                                                  |
| Currency                   | Dropdown | Multi-currency support                                                  |
| Amount                     | Number   | Base pay rate                                                           |
| Pro-rating by attendance   | Toggle   | Prorate salary based on attendance logs                                 |
| Work hours type            | Dropdown | Fixed Work Days, Using Shift Planning, Fixed Timing, Flexible Timing    |
| Has overtime pay           | Checkbox | Enable overtime calculations                                            |
| Base hourly rate           | Number   | For OT calculation                                                      |
| OT rate - normal days      | Number   | Multiplier (e.g., 1.5x)                                                 |
| OT rate - non-working days | Number   | Multiplier (e.g., 2.0x)                                                 |
| OT rate - holidays         | Number   | Multiplier (e.g., 2.0x)                                                 |
| OT recording method        | Dropdown | "After Working Hours" or "After Fixed Hours" (weekly/monthly threshold) |
| Holiday group              | Dropdown | Applicable holiday calendar                                             |

### 1.3 Pay Items

| Field                    | Type     | Details                                        |
| ------------------------ | -------- | ---------------------------------------------- |
| Description/Name         | Text     | Custom pay item name                           |
| Category                 | Dropdown | Classification category                        |
| CPF Type                 | Dropdown | OW (Ordinary Wages) or AW (Additional Wages)   |
| IR8A Code                | Dropdown | IRAS tax classification code                   |
| Unit Type                | Dropdown | $, hours, or days                              |
| Default Amount           | Number   | Per-unit value                                 |
| Shift assignment display | Toggle   | Show when assigning shifts                     |
| Ad-hoc request           | Toggle   | Available for employee-initiated requests      |
| Project costing          | Toggle   | Include/exclude from project cost calculations |
| Archive status           | Toggle   | Deactivate without deletion                    |
| Proration formula        | Config   | Configurable proration method                  |
| Attendance conditions    | Config   | Prerequisites for pay item application         |

**Pay Item Categories (OW - Ordinary Wages):**

- Monthly salary
- Overtime pay (if paid by 14th of following month)
- Monthly commissions
- Allowances (food, shift, transport, etc.)

**Pay Item Categories (AW - Additional Wages):**

- Annual bonuses
- Leave payouts / encashment
- Non-monthly commissions
- Incentives
- Long service awards

### 1.4 Payroll Generation Process

| Step/Field                     | Details                                                                                  |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| Month/Year selection           | Auto-set to current period                                                               |
| Custom date range              | Within payment period settings                                                           |
| Adhoc payroll option           | Generate off-cycle payroll                                                               |
| Exclude unpaid claims checkbox | Exclude unpaid claims from payroll                                                       |
| Enable custom payroll name     | Custom naming for payroll run                                                            |
| Employee selection             | Individual checkboxes, Select All, Search by name/NRIC/dept/position/org/pay scheme/bank |
| Payment receipt date           | Date shown on payslip, typically aligned with GIRO value date                            |
| Salary proration               | Auto-calculated based on days worked vs unpaid days                                      |
| Attendance-based pay           | Calendar icon reveals attendance logs for salary/OT calculation                          |
| Claims integration             | Approved unreimbursed claims auto-included                                               |
| Pay item editing               | Edit, delete, add pay items per employee                                                 |
| Statutory auto-calculation     | CPF, SHG, SDL calculated automatically                                                   |
| Confirmation page              | Shows all statutory levies, deductions, additions before confirm                         |

### 1.5 Payroll Management

| Feature                   | Details                                       |
| ------------------------- | --------------------------------------------- |
| Payroll statuses          | Processing, Unpublished, Published            |
| Edit unpublished payrolls | Full re-editing of unpublished payrolls       |
| CPF/SHG manual adjustment | Edit CPF and/or SHG amounts after generation  |
| View payslip (HTML)       | View individual payslips in browser           |
| Download payslip (PDF)    | Individual PDF download                       |
| Download all PDFs         | Batch PDF download                            |
| Publish immediately       | Instant publish with email notification       |
| Scheduled publish         | Set future date for auto-publish              |
| Delete payslip/payroll    | Permanent, irreversible deletion              |
| Adhoc payments            | Off-cycle payment management                  |
| Payroll variance report   | Compare two months' payrolls and see variance |

### 1.6 CPF Settings & Submission

| Setting/Feature                      | Details                                                            |
| ------------------------------------ | ------------------------------------------------------------------ |
| CPF contribution status per employee | Include, Exclude, or Full Employer CPF (employer pays both shares) |
| CPF OW Monthly Ceiling               | $7,400/month (auto-applied)                                        |
| CPF Annual OW Ceiling                | $102,000/year                                                      |
| CPF Annual Limit                     | $37,740 (voluntary + mandatory combined)                           |
| CSN (CPF Submission Number)          | Format: UEN + Payment Type (PTE, VCT) + Serial Number              |
| Mass Assign CSN                      | Assign CSN to multiple employees at once                           |
| CPF e-submit file generation         | Download file for CPF Board portal upload                          |
| SHG auto-inclusion                   | Auto-included in CPF submission file                               |
| Payment Advice Report                | Verification document for CPF submission                           |
| Manual CPF/SHG adjustment            | Override auto-calculated amounts                                   |
| CorpPass authentication              | Required for CPF portal submission                                 |

### 1.7 GIRO Bank File Generation

| Bank              | Supported | Notes                                                |
| ----------------- | --------- | ---------------------------------------------------- |
| DBS               | Yes       | Requires DBS BusinessCare activation (1800 222 2200) |
| UOB               | Yes       | Requires UOB activation (+65 6259 8188)              |
| OCBC              | Yes       | Requires OCBC activation (+65 6538 1111)             |
| CIMB              | Yes       | Supported                                            |
| HSBC              | Yes       | Supported                                            |
| Maybank           | Yes       | Supported                                            |
| Consolidated GIRO | Yes       | Multi-bank consolidated file                         |
| Brunei Bank File  | Yes       | For Brunei operations                                |

**GIRO Features:**

- Select individual employees or all
- Flexible payment amount control
- Per-employee payment breakdown
- Must submit 1 working day before 6pm of payment date

### 1.8 Tax Filing (IRAS)

| Form        | Method                        | Details                                                         |
| ----------- | ----------------------------- | --------------------------------------------------------------- |
| IR8A        | API (AIS) via APEX + CorpPass | Primary employment income declaration                           |
| IR8S        | Deprecated                    | No longer required as of 2026                                   |
| Appendix 8A | API via APEX                  | Benefits-in-Kind supplementary (only when BIK declared on IR8A) |
| Appendix 8B | Not found                     | Not explicitly documented                                       |
| IR21        | Manual (PDF download)         | For non-citizen employee cessation/overseas posting             |

**IR8A Optional Declaration Fields (manual entry):**

- Directors' Fee Approval Date
- Exempt Or Remission Income Indicator
- Exempt Income amount
- Bonus Declaration Date
- Approval Date (Compensation for loss of office)
- Income For Tax Borne By Employer
- Partial Income Tax Borne By Employee

**Tax Filing Features:**

- Authorized submitting personnel (name, third-party agent flag)
- Year and organisation filtering
- Amendment support with reason/description
- File locking post-submission
- API validation status tracking
- Submission period: 2 January to 1 March annually

### 1.9 Statutory Contributions

**SDL (Skills Development Levy):**

- Rate: 0.25% of total wages
- Minimum: $2 per employee
- Maximum: $11.25 per employee
- Capped at first $4,500 monthly wages
- Round total SDL down to nearest dollar
- Exemptions: no SG services that month, registered students, ministerial order

**SHG (Self-Help Groups) -- 4 funds:**

| Fund  | Eligibility              | Rate Range                     |
| ----- | ------------------------ | ------------------------------ |
| CDAC  | SC/PR, Chinese           | $0.50 - $3.00 by wage bracket  |
| ECF   | SC/PR, Eurasian          | $2.00 - $20.00 by wage bracket |
| MBMF  | SC/PR/Foreign, Muslim    | $3.00 - $26.00 by wage bracket |
| SINDA | SC/PR/EP holders, Indian | $1.00 - $30.00 by wage bracket |

**Community Chest (SHARE Program):**

- Voluntary employee donations via payroll deduction
- Tax-deductible
- Collected by CPF Board

**AMCS & PMBS:**

- Additional Medisave Contribution Scheme checkbox
- Portable Medical Benefits Scheme checkbox
- Enable deduction during payroll generation

**Foreign Worker Levy:**

- Applies to Work Permit and S Pass holders
- Rates set by MOM (not Payboy)
- Factors: worker qualifications, dependency ceiling
- Deducted on 17th of following month via GIRO
- Waiver eligibility: overseas leave (60 days/yr), hospitalization, death, PR conversion

---

## MODULE 2: LEAVE

### 2.1 Leave Settings (Global)

| Setting                                | Type     | Details                                          |
| -------------------------------------- | -------- | ------------------------------------------------ |
| Enable leave module on employee portal | Toggle   | Show/hide leave module for employees             |
| Manager leave creation authority       | Toggle   | Allow managers to create leaves for subordinates |
| Calendar visibility scope              | Dropdown | Controls which colleagues' leaves are visible    |
| Allow hourly leaves                    | Checkbox | Enable time-based leave (minutes/hours)          |
| Hours per full day threshold           | Number   | Hours that equal one full day of leave           |

### 2.2 Leave Types (4 Categories)

| Category        | Use Case                                                                    |
| --------------- | --------------------------------------------------------------------------- |
| Customize       | All custom leave types (annual, off-in-lieu, NS leave, compassionate, etc.) |
| Sick Leave      | Outpatient and hospitalization sick leave                                   |
| Childcare Leave | Singaporean child or non-Singaporean child variants                         |
| Time Off        | Leave in minutes and hours                                                  |

### 2.3 Leave Type Settings (Per Leave Type)

| Setting                                      | Type     | Details                                                            |
| -------------------------------------------- | -------- | ------------------------------------------------------------------ |
| Entitlement applicability                    | Dropdown | All employees or certain positions                                 |
| Entitlement quantity by position             | Config   | Different days per position                                        |
| Entitlement quantity by years of service     | Config   | Incremental entitlement based on tenure                            |
| Entitlement period                           | Dropdown | All at year start, or divided over 1/2/3/4/6 months                |
| Based on                                     | Dropdown | January 1st (calendar year) or employee hire date anniversary      |
| Unused leaves handling                       | Dropdown | Forfeit, Encash, or Carry Forward                                  |
| Carry forward maximum                        | Number   | Max days that can be carried forward                               |
| Carry forward expiry period                  | Duration | When carried-forward days expire                                   |
| Encashment maximum                           | Number   | Max days that can be encashed                                      |
| Gender restriction                           | Dropdown | Restrict to specific gender                                        |
| Proration                                    | Toggle   | Enable/disable proration for partial-year employees                |
| Rounding                                     | Dropdown | Nearest whole, nearest half, round up/down for each                |
| Default for new employees                    | Checkbox | Auto-assign to newly onboarded eligible employees                  |
| Overflow                                     | Checkbox | Allow applications exceeding current balance (within yearly limit) |
| Unpaid leave                                 | Checkbox | Prorate monthly salary for unpaid leave                            |
| Reason required                              | Checkbox | Mandatory justification text                                       |
| Proof required                               | Checkbox | Mandatory file upload (PDF/image)                                  |
| Include non-working days and public holidays | Checkbox | Factor non-working days into leave calculation                     |
| Shift pay item                               | Checkbox | Maintain shift pay item payouts during leave                       |
| Apply to existing employees                  | Checkbox | Retroactively assign to current eligible staff                     |

### 2.4 Proration & Earned Leave

| Setting                   | Details                                                                 |
| ------------------------- | ----------------------------------------------------------------------- |
| Proration formula         | (months worked / 12) x annual entitlement                               |
| Earned leave distribution | Annual entitlement divided across equal periods                         |
| Rounding options          | Round to nearest whole, up/down to whole, nearest half, up/down to half |
| Increment timing          | Anniversary-based or calendar-year-based                                |

### 2.5 Childcare Leave (Singapore-Specific)

| Setting                        | Details                                                    |
| ------------------------------ | ---------------------------------------------------------- |
| Eligibility                    | 3+ continuous months of service                            |
| Singaporean child: Annual days | 6 days (3 employer-paid, 3 government-paid)                |
| Extended childcare leave       | 2 days/year after 7 years continuous, until child age 12   |
| Non-Singaporean child          | Separate entitlement structure                             |
| Assignment methods             | Mass (by company/org/dept/position/employee) or individual |
| Entitlement start date         | Child's birth year                                         |

### 2.6 Sick Leave (Outpatient & Hospitalization)

- Separate tracking for outpatient vs hospitalization days
- MOM-compliant entitlements based on service length
- Medical certificate (MC) upload requirement option

### 2.7 Leave Features

- Leave calendar (visibility configurable by company/org/dept/subordinates/self)
- Leave application workflow with approval groups
- Leave encashment at year-end
- Off-in-lieu for public holidays
- Minutes/hours leave (Time Off)
- Additional leaves (manual add by admin)
- Leave balance tracking per type

---

## MODULE 3: CLAIMS

### 3.1 Claim Settings (Global)

| Setting                                 | Type          | Details                                                                   |
| --------------------------------------- | ------------- | ------------------------------------------------------------------------- |
| Enable claims module on employee portal | Checkbox      | Show/hide claims for employees                                            |
| Manager claim creation authority        | Checkbox      | Allow managers to create claims for subordinates                          |
| Payroll cut-off date                    | Number (1-31) | Latest date for claims approval to be included in current month's payroll |
| Backdated claim limit                   | Months        | Maximum earlier receipt date employees can claim                          |

### 3.2 Claim Type Settings

| Field                     | Type          | Details                                                                         |
| ------------------------- | ------------- | ------------------------------------------------------------------------------- |
| Description/Name          | Text          | Claim type identifier                                                           |
| Default for new employees | Toggle        | Auto-assign to all new employees                                                |
| Limit per claim           | Number        | Maximum amount per single claim                                                 |
| Limit per day             | Number        | Daily claim cap                                                                 |
| Limit per week            | Number        | Weekly claim cap                                                                |
| Limit per month           | Number        | Monthly claim cap                                                               |
| Limit per calendar year   | Number        | Calendar year claim cap                                                         |
| Limit per financial year  | Number        | Financial year claim cap                                                        |
| Limit applicability       | Dropdown      | All employees or specific positions                                             |
| Co-payment (percentage)   | Number        | Employee co-pay as percentage                                                   |
| Co-payment (fixed amount) | Number        | Employee co-pay as fixed amount                                                 |
| Prorating                 | Toggle        | Prorate limits based on months remaining at hire (calendar/financial year only) |
| Remark field              | Toggle        | Enable employee remarks                                                         |
| Remark mandatory          | Toggle        | Make remarks required                                                           |
| Categories                | Dropdown list | Customizable categories employees select when claiming                          |
| Receipt mandatory         | Toggle        | Require receipt upload                                                          |
| Multiple attachments      | Toggle        | Allow up to 5 files (PDF, PNG, JPG)                                             |
| Probationer exclusion     | Toggle        | Prevent probationary employees from claiming                                    |
| Payout type               | Dropdown      | Always Payout, Always No Payout, Allow No Payout                                |
| Foreign currencies        | Toggle        | Enable multi-currency claims                                                    |
| Cost centre linking       | Toggle        | Enable cost centre selection on claims                                          |
| Benefits in Kind          | Toggle        | Subject reimbursement to CPF/IRAS statutory deductions                          |
| Archive                   | Toggle        | Prevent new claims; existing remain accessible                                  |

### 3.3 Claim Types

| Type         | Details                                             |
| ------------ | --------------------------------------------------- |
| Single Claim | Individual reimbursement for a single cost          |
| Group Claim  | Collection of claims (e.g., business trip expenses) |

### 3.4 Group Claims (Flexi-Benefits)

- Group multiple claims under one umbrella
- Approve/deny individual claims within a group
- "Approve All" batch operation
- Filter by status: approved, denied, pending
- Claims with "Always Payout" auto-appear in payroll after approval

### 3.5 Claim Workflow

1. Employee submits claim (with receipt, category, remarks)
2. Manager approves/denies (if approval groups configured)
3. Admin final approval
4. Approved claims auto-included in payroll generation
5. Claims approved after cut-off date roll to next month

---

## MODULE 4: ATTENDANCE

### 4.1 Attendance Settings

| Setting                                     | Type     | Details                                                 |
| ------------------------------------------- | -------- | ------------------------------------------------------- |
| Enable attendance module on employee portal | Toggle   | Employee access to clocking                             |
| Manager attendance creation                 | Toggle   | Managers can create attendance for subordinates         |
| Employee self-logging                       | Toggle   | Clock in/out via web or mobile without external devices |
| Employee self-editing                       | Toggle   | Employees can edit their own attendance records         |
| Mandatory approval before payroll           | Toggle   | Attendance must be approved before payroll calculation  |
| Geofencing (GPS proximity)                  | Toggle   | Require GPS proximity to workplace                      |
| Location radius restrictions                | Config   | Restrict check-in to designated outlets                 |
| Photo evidence requirement                  | Toggle   | Require photo on clock in/out                           |
| Disable mobile check-in/out                 | Toggle   | Force desktop-only attendance                           |
| Outlet selection requirement                | Toggle   | Must select outlet; if omitted, live address captured   |
| Temperature logging                         | Toggle   | Record temperature during clock events                  |
| Remarks/notes during clock                  | Toggle   | Allow text notes on clock events                        |
| Multiple attendance reconciliation per day  | Toggle   | Multiple clock-in/out pairs per day                     |
| Auto clock-out                              | Toggle   | Automatic clock-out after set period                    |
| Buffer time after working hours             | Duration | Time before OT classification                           |
| Minimum interval between clock events       | Duration | Prevent double-clocking                                 |
| Maximum daily working hours                 | Hours    | Cap on daily hours                                      |
| Maximum duration for attendance log         | Duration | Prevent errors from forgotten clock-out                 |
| Clock-out auto-adjustment rounding          | Config   | Off/Up/Down, 5-60 minute intervals                      |
| Rounding application scope                  | Dropdown | All employees, organization-wide, or departmental       |

### 4.2 Lateness Settings

| Setting                     | Type     | Details                                       |
| --------------------------- | -------- | --------------------------------------------- |
| Enable lateness deduction   | Toggle   | Deduct from payroll for lateness              |
| Display lateness in records | Toggle   | Show late status in attendance                |
| Lateness notification       | Toggle   | Send notifications for late arrivals          |
| Notification type           | Dropdown | Email, mobile push, or both                   |
| Grace period                | Minutes  | Buffer before marking as late                 |
| Interval deduction brackets | Config   | Tiered deduction amounts by lateness duration |

### 4.3 Early Clock-Out Settings

| Setting                          | Type     | Details                                       |
| -------------------------------- | -------- | --------------------------------------------- |
| Enable early departure deduction | Toggle   | Deduct from payroll for early departure       |
| Display early departure          | Toggle   | Show in attendance records                    |
| Early departure notification     | Toggle   | Send notifications                            |
| Notification type                | Dropdown | Email, mobile push, or both                   |
| Grace period                     | Minutes  | Buffer before marking as early departure      |
| Interval deduction thresholds    | Config   | Tiered deductions by early departure duration |

### 4.4 Clock In/Out Methods

| Method                    | Details                                   |
| ------------------------- | ----------------------------------------- |
| Mobile app                | GPS-verified, optional photo capture      |
| Web portal (desktop)      | Dashboard clock in/out button             |
| Manual entry (desktop)    | Date, time in, time out, branch selection |
| Third-party biometric     | Fingerprint scanner integration           |
| Facial recognition device | Dedicated hardware integration            |
| Admin/manager manual add  | Create logs on behalf of employees        |
| Mass add (CSV import)     | Bulk import attendance logs               |

### 4.5 Attendance Log Fields

| Field              | Details                        |
| ------------------ | ------------------------------ |
| Employee name      | Auto or selected               |
| Outlet/Branch      | Dropdown or auto-detected      |
| Date               | Clock date                     |
| Time In            | Clock-in timestamp             |
| Time Out           | Clock-out timestamp            |
| Location           | GPS coordinates or branch name |
| Photo              | Camera capture (if required)   |
| Temperature        | Reading (if enabled)           |
| Remarks            | Free text notes                |
| Adjustment remarks | Audit trail for edits          |
| Approval status    | Pending/Approved/Denied        |

### 4.6 Attendance Views

| View               | Details                                      |
| ------------------ | -------------------------------------------- |
| Attendance Logs    | Individual log listing with view/edit/delete |
| Attendance Today   | Real-time view of who's clocked in           |
| Attendance Summary | Aggregated view per employee per period      |
| Attendance Audit   | Audit trail of all changes                   |

---

## MODULE 5: SHIFT/ROSTERING

### 5.1 Rostering Settings

| Setting                                    | Type     | Details                                                       |
| ------------------------------------------ | -------- | ------------------------------------------------------------- |
| Enable rostering module on employee portal | Checkbox | Employees can view planned/published shifts                   |
| Manager scheduling permissions             | Checkbox | Managers can plan shifts using employee account               |
| OT & shift breakdown cutoff date           | Number   | Day of month for OT/shift pay items to be included in payroll |

### 5.2 Shift Templates

| Field                 | Type       | Details                                              |
| --------------------- | ---------- | ---------------------------------------------------- |
| Branch/Outlet         | Dropdown   | Physical location for the shift                      |
| Name                  | Text       | Descriptive shift name                               |
| Non-Working Day (NWD) | Checkbox   | Mark as rest day/off day/holiday (no time required)  |
| Time In               | Time       | Shift start time                                     |
| Time Out              | Time       | Shift end time                                       |
| Specify Break         | Toggle     | Include break time                                   |
| Break type            | Dropdown   | Paid or Unpaid                                       |
| Break determination   | Dropdown   | By Timing (start/end) or Duration (preset durations) |
| Instructions          | Text       | Specific expectations/tasks for employees            |
| Pay Item              | Dropdown   | Pay item to use for shift payout                     |
| Type of Work          | Dropdown   | Work type classification                             |
| Hours and Minutes     | Duration   | Required duration per work type                      |
| Additional breakdowns | Config     | Break hours, overtime hours via "Add Hours"          |
| Total shift hours     | Calculated | Auto-calculated total                                |
| Total breakdown hours | Calculated | Sum of all specified categories                      |
| Unaccounted hours     | Calculated | Discrepancy identification                           |

### 5.3 Shift Planning

| Feature                        | Details                                          |
| ------------------------------ | ------------------------------------------------ |
| Weekly view                    | Shifts displayed in weekly calendar              |
| Create shift                   | Select outlet, template, name, date              |
| Recurring shifts               | "Set Schedule" with frequency selection          |
| Non-recurring shifts           | One-time shift creation                          |
| Additional pay items per shift | Add from dropdown with custom amounts            |
| Publish shifts                 | Distribute roster to employees with notification |

### 5.4 Shift Hourly Rate

| Field             | Type     | Details                     |
| ----------------- | -------- | --------------------------- |
| Name              | Text     | Rate identifier             |
| Branch            | Dropdown | Location where rate applies |
| Hourly rate value | Number   | Base compensation per hour  |
| Overtime amount   | Number   | OT multiplier or flat rate  |

### 5.5 Shift Multiplier

| Field            | Type     | Details                                               |
| ---------------- | -------- | ----------------------------------------------------- |
| Name             | Text     | Multiplier identifier                                 |
| Branch           | Dropdown | Location where multiplier applies                     |
| Multiplier value | Number   | Factor applied to base rate (e.g., 1.25x, 1.5x, 2.0x) |

### 5.6 Additional Overtime Settings

| Setting                             | Type      | Details                                           |
| ----------------------------------- | --------- | ------------------------------------------------- |
| Multiplier rate                     | Number    | Custom multiplier (e.g., 1.5x, 2.0x)              |
| Auto-calculate hourly rate          | Checkbox  | Auto-calculate or manual override                 |
| Time From / Time To                 | Time      | When OT rate activates                            |
| Start Day checkbox                  | Toggle    | For flexible timing, count from first check-in    |
| End Day checkbox                    | Toggle    | For unplanned OT, count to final check-out        |
| Day type                            | Dropdown  | Regular, rest day, public holiday                 |
| Specific day selection              | Dropdown  | Day-of-week specific multipliers                  |
| Pay out additional hours multiplier | Config    | Rate after default working hours                  |
| Multiple OT rate support            | Unlimited | Complex compensation structures across conditions |

### 5.7 Additional Hourly Pay Settings

| Field              | Type     | Details                                          |
| ------------------ | -------- | ------------------------------------------------ |
| Description        | Text     | Short description for the rate condition         |
| Hourly Pay         | Number   | Custom hourly amount                             |
| Days               | Dropdown | Specific workdays (e.g., Monday and Friday only) |
| Time From          | Time     | Rate activation start                            |
| Time To            | Time     | Rate activation end                              |
| Start Day checkbox | Toggle   | Count from initial check-in                      |
| End Day checkbox   | Toggle   | Count through checkout                           |

### 5.8 Shift Attendance

| Feature                    | Details                                                                                                                       |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Filters                    | Employee name/number, branch, dates, org, dept, tags, work day/off day/holiday/rest day, approval state, type, payment status |
| Edit attendance log        | Click timing to navigate to log, edit or add adjustment                                                                       |
| Approve/Deny shift entries | Per-entry approval workflow                                                                                                   |
| Reset approval             | Only original approver can reset                                                                                              |
| Denial notification        | Email to employee on denial                                                                                                   |
| Delete shifts              | Remove assigned shifts                                                                                                        |
| Tag attendance to shifts   | Link attendance logs to specific shifts                                                                                       |

---

## MODULE 6: APPRAISAL

### 6.1 Appraisal Types

| Type             | Details                                                                 |
| ---------------- | ----------------------------------------------------------------------- |
| Ad-hoc Appraisal | One-off for specific employees (e.g., probation confirmation)           |
| Appraisal Period | Batch company-wide appraisal during designated periods (e.g., year-end) |

### 6.2 Appraisal Flow Types

| Flow               | Details                                     |
| ------------------ | ------------------------------------------- |
| Downward appraisal | One reviewer evaluates multiple employees   |
| Upward appraisal   | Multiple reviewers assess a single employee |

### 6.3 Template Configuration

| Section              | Details                                                 |
| -------------------- | ------------------------------------------------------- |
| Header options       | Select employee information fields to display           |
| Body options         | Drag-and-drop interface for question/section placement  |
| Footer options       | Enable weightage display, employee sign-off requirement |
| Import from existing | Duplicate fields from other templates                   |

### 6.4 Appraisal Settings

| Setting                       | Type     | Details                                         |
| ----------------------------- | -------- | ----------------------------------------------- |
| Enable weightage              | Checkbox | Display scores and weightage achieved           |
| Employee sign-off             | Toggle   | Require employee login to acknowledge           |
| Employee view post-submission | Toggle   | Allow employees to see results after submission |
| Reviewer view post-submission | Toggle   | Allow reviewers to see other results            |
| Set as Private                | Toggle   | Restrict visibility to admins only              |
| Save as Draft                 | Feature  | Save progress without submission                |
| Session timeout               | System   | 30-minute idle limit                            |

### 6.5 Appraisal Grading

- Configurable grading scales
- Section-level weightage
- Score calculation by weighted sections

### 6.6 Roles in Appraisal

| Role     | Capabilities                                                         |
| -------- | -------------------------------------------------------------------- |
| Employee | Fill fields marked "Filled by Employee"; cannot edit disabled fields |
| Reviewer | Fill fields marked "Filled by Reviewers"; view employee responses    |
| Admin    | Full template CRUD, report generation, private appraisal access      |

### 6.7 Reporting

- Excel export with multiple sheets per template
- Columns = sections, Rows = employee scores
- Section weightage included

---

## MODULE 7: REPORTS

### 7.1 Payroll Reports (11)

| Report            | Details                                                              |
| ----------------- | -------------------------------------------------------------------- |
| A8A               | IRAS amendment form                                                  |
| Banks             | Payroll segmented by employee banking institution                    |
| CPF               | Summary + breakdown of CPF paid, by month                            |
| Cost Centres      | Expense breakdown by org/dept/outlet with statutory payments summary |
| IRAS              | IR8A form generation                                                 |
| Statutory         | Malaysian entities -- statutory payment breakdown                    |
| Payroll (Monthly) | PDF summary by organisation and department                           |
| Payrolls          | Excel report of amounts per pay item per employee per month          |
| Payslips          | Excel filtered by payment periods                                    |
| Salary (YTD)      | Year-to-date salary summary by month per employee                    |
| Payroll Variance  | Comparison between two months' payrolls with variance                |

### 7.2 Claims Reports (3)

| Report | Details                                                  |
| ------ | -------------------------------------------------------- |
| Excel  | Customizable with paid/unpaid and payout filters         |
| CSV    | General overview, especially claim groups, fewer filters |
| PDF    | Summary with receipts printed                            |

### 7.3 Leave Reports (2)

| Report     | Details                                             |
| ---------- | --------------------------------------------------- |
| Leaves     | All employee leave application records              |
| Leave Type | Leave balances per type with breakdown of additions |

### 7.4 Other Reports (6)

| Report           | Details                                                                   |
| ---------------- | ------------------------------------------------------------------------- |
| Employees        | All personal details with pay scheme details (SHG, CPF)                   |
| Appraisal Period | Excel of appraisal answers by section weightage                           |
| Attendance       | Working hours per employee for custom period                              |
| Shift Attendance | Shift breakdown showing working hours including OT per day                |
| Schedule         | Shift attendance + attendance log + adjusted attendance + shift pay items |
| Project Costings | Costing breakdown per project                                             |

**Total: 22 reports**

---

## MODULE 8: SETTINGS / ADMIN

### 8.1 Company Settings

| Setting                      | Details                                              |
| ---------------------------- | ---------------------------------------------------- |
| Organization name            | Company/subsidiary name                              |
| Login ID                     | Unique, case-sensitive identifier for employee login |
| Subdomain alias              | For employee portal URL                              |
| Business Registration Type   | Type dropdown                                        |
| Business Registration Number | UEN or equivalent                                    |
| Business Address             | Full address                                         |
| CPF Submission Number        | For CPF e-submission                                 |
| AMCS checkbox                | Additional Medisave Contribution Scheme              |
| PMBS checkbox                | Portable Medical Benefits Scheme                     |
| Logo/Letterhead upload       | Per-organization branding                            |

### 8.2 Organization Structure

| Level            | Features                                                                  |
| ---------------- | ------------------------------------------------------------------------- |
| Organizations    | Multiple sub-organizations within one account; payroll generation per org |
| Departments      | Within organizations; enable custom reports, approval groups, rostering   |
| Positions        | Within departments; archivable when inactive                              |
| Branches/Outlets | Physical locations with geofencing                                        |

### 8.3 Branch/Outlet Configuration

| Field                   | Type     | Details                             |
| ----------------------- | -------- | ----------------------------------- |
| Branch name             | Text     | Location identifier                 |
| Check-in radius         | Number   | Geolocation boundary (default 100m) |
| Country                 | Dropdown | Country selection                   |
| Postal code             | Text     | Auto-populates street address       |
| Additional address info | Text     | Supplementary details               |
| Archive option          | Toggle   | Deactivate without deletion         |

### 8.4 Approval Groups

| Setting                        | Details                                                         |
| ------------------------------ | --------------------------------------------------------------- |
| Group name                     | Text identifier                                                 |
| Without rules                  | Any manager in group can approve any application                |
| With rules (One-tier)          | Single level of designated approvers by category                |
| Multiple tiers                 | Up to 2 tiers of sequential approval                            |
| Categories                     | Leaves (by leave type), Claims (by claim type), Attendance Logs |
| Approver type                  | Single employee or approval group                               |
| Additional email notifications | Per category and status, to employees or admins                 |

### 8.5 Holiday Groups

| Feature                         | Details                                               |
| ------------------------------- | ----------------------------------------------------- |
| Default holidays                | Auto-populated by country                             |
| Import holidays                 | Select year + country to import preset calendar       |
| Add custom holidays             | Name + date (single day per entry; repeat for ranges) |
| Multiple holiday groups         | Different groups for different employee segments      |
| Edit/Delete individual holidays | Per-holiday management                                |

### 8.6 Admin Accounts & Permissions

**Hierarchy:**

- Owner: Complete access to all functions, can grant admin creation permissions
- Other Admins: Full or partial access as granted

**Module Permissions (with granular action-level control):**
| Module | Details |
|--------|---------|
| Company | Full module with granular controls |
| Employees | CRUD on employee records |
| Organization | Manage hierarchy and reporting lines |
| Payroll | Process payroll with action-level permissions |
| Claims | Claim submissions and processing |
| Leaves | Leave requests and approvals |
| Rostering | Create and manage work schedules |
| Attendance | Monitor and record attendance |
| Projects | Project allocation and tracking |
| Training | Employee training programs |
| Appraisals | Performance reviews; private appraisals require explicit permission |
| ATS (Applicant Tracking) | Recruitment and candidate management |
| Inventories | Asset tracking |
| Reports | Report generation and access |
| Administration | System-wide settings |
| Dashboard | Analytics and overview |
| Entry Device Access | Physical access point permissions |
| Covid Safe+ | Health compliance tracking |
| Facial Device Access | Biometric system management |

**Access Controls:**

- Admin view permissions: Restrict by organization type
- Employee group permissions: Limit access to specific employee groups
- Custom roles: Create tailored permission sets beyond presets
- Preset permission titles available

### 8.7 Employee Settings

| Setting                          | Type     | Details                                  |
| -------------------------------- | -------- | ---------------------------------------- |
| Enable employee directory        | Toggle   | Allow employees to see colleague list    |
| Directory search scope           | Dropdown | Company or department level              |
| Show email in directory          | Toggle   | Display email addresses                  |
| Show phone in directory          | Toggle   | Display contact numbers                  |
| Profile editing by employee      | Toggle   | Allow self-editing of profile            |
| Document upload by employee      | Toggle   | Allow document uploads                   |
| Change notification emails       | Toggle   | Notify admin of employee profile changes |
| Show alias name only             | Toggle   | Display alias on selected portals        |
| Birthday notifications           | Toggle   | Admin receives birthday alerts           |
| Probation end date notification  | Number   | Days in advance to notify                |
| Internship end date notification | Number   | Days in advance to notify                |
| Work pass expiry notification    | Config   | Send to admin, employee, or both         |
| Document expiry notification     | Config   | Send to admin, employee, or both         |

### 8.8 Calendar Settings

| Event                  | Visibility Options                                    |
| ---------------------- | ----------------------------------------------------- |
| Birthdays              | Company, Organization, Department, Subordinates, Self |
| Leave records          | Company, Organization, Department, Subordinates, Self |
| New hire notifications | Company, Organization, Department, Subordinates, Self |
| Work pass expiry dates | Company, Organization, Department, Subordinates, Self |
| Document expiry dates  | Company, Organization, Department, Subordinates, Self |
| Termination dates      | Company, Organization, Department, Subordinates, Self |
| Colleague leaves       | Company, Organization, Department, Subordinates, Self |

### 8.9 Integrations

| Integration     | Features                                                                                                                  |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- |
| Xero            | Bill creation, manual journal, pay item to Chart of Accounts mapping, auto-sync, payee breakdown, bill status/type config |
| QuickBooks      | Integration and disconnection support                                                                                     |
| Financio        | Accounting integration                                                                                                    |
| Google Calendar | Sync for employee calendar events                                                                                         |
| StaffAny        | Integration support                                                                                                       |

### 8.10 Security & Authentication

| Feature                               | Details                                       |
| ------------------------------------- | --------------------------------------------- |
| Two-Factor Authentication (Admins)    | 2FA for admin accounts                        |
| Two-Factor Authentication (Employees) | 2FA for employee portal                       |
| Audit Logs                            | System audit trail for admin actions          |
| Data Retention Period                 | Configurable retention for resigned employees |

### 8.11 Other Settings

| Feature              | Details                            |
| -------------------- | ---------------------------------- |
| Foreign Currencies   | Configure available currencies     |
| Announcements        | Company-wide announcements         |
| Work Hours           | Global work hours configuration    |
| Pay Item Conditions  | Conditional logic for pay items    |
| Pay Item Permissions | Control who can see/edit pay items |

---

## MODULE 9: EMPLOYEE SELF-SERVICE PORTAL

### 9.1 Employee Capabilities

| Feature                       | Details                                                 |
| ----------------------------- | ------------------------------------------------------- |
| View payslips                 | Access published payslips with PDF download             |
| Apply for leave               | Submit leave applications with reason/proof             |
| View leave balance            | Per leave type balance and history                      |
| View leave calendar           | See own and colleagues' leave (per visibility settings) |
| Submit claims                 | Single and group claims with receipt upload             |
| Clock in/out                  | Mobile app (GPS + photo) or web portal                  |
| View attendance logs          | Personal attendance history                             |
| View published shifts         | Upcoming shift schedule                                 |
| Request inventory items       | Request company assets                                  |
| Acknowledge inventory receipt | Confirm physical receipt of items                       |
| Edit own profile              | If enabled by admin                                     |
| Upload documents              | If enabled by admin                                     |
| Complete appraisals           | Fill employee sections, sign off                        |
| View appraisal results        | If visibility is enabled                                |
| Self-service onboarding       | Complete onboarding in ~5 minutes                       |
| Payday countdown              | If enabled                                              |
| Request ad-hoc pay items      | If enabled                                              |
| Google Calendar sync          | If enabled                                              |

### 9.2 Manager Capabilities

| Feature                            | Details                            |
| ---------------------------------- | ---------------------------------- |
| Approve/deny leave                 | For subordinates in approval group |
| Approve/deny claims                | For subordinates in approval group |
| Approve/deny attendance            | For subordinates in approval group |
| Create leave for subordinates      | If enabled in settings             |
| Create claims for subordinates     | If enabled in settings             |
| Create attendance for subordinates | If enabled in settings             |
| Plan shifts for employees          | If rostering permission enabled    |
| View team records                  | Based on approval group hierarchy  |
| Mobile push notifications          | Alerts for pending approvals       |

### 9.3 Admin Capabilities

| Feature                  | Details                                             |
| ------------------------ | --------------------------------------------------- |
| Full CRUD on all modules | Based on assigned permissions                       |
| Generate payroll         | Process monthly payroll                             |
| Publish payslips         | Immediate or scheduled                              |
| Generate GIRO files      | Bank transfer files                                 |
| CPF e-submission         | Generate and submit CPF files                       |
| Tax filing (IRAS)        | IR8A, A8A, IR21                                     |
| Create/manage employees  | Onboarding and offboarding                          |
| Configure all settings   | Company, payroll, leave, claims, attendance, shifts |
| Generate reports         | All 22 report types                                 |
| Manage approval groups   | Configure approval hierarchies                      |
| Manage admin accounts    | Create admins with custom permissions               |
| Salary adjustments       | Individual or bulk, fixed or percentage             |
| Position reassignments   | With career history tracking                        |
| Inventory management     | Reserve, issue, deny requests                       |
| Project management       | Assign employees, track costs                       |
| Appraisal management     | Create templates, launch periods, view results      |

---

## MODULE 10: PROJECT COSTING

### 10.0 Overview

The Project Module estimates how much the company spends on each project in terms of salaries and claims. It has seven sub-sections: Projects, Employees, Time Sheets, Project Roles, Overheads, Project Calculations, and Project Settings.

**Implementation workflow (8 steps):**

1. Create projects (Projects > + New Project)
2. Configure project fields
3. Assign employees to projects
4. Designate employee assignment types (Timesheet / Attendance / Allocations)
5. Input data via the chosen assignment method
6. Generate payroll for the period
7. Generate Project Calculations (derives cost estimates)
8. Generate Project Costing Report (Excel breakdown)

### 10.1 Project Fields

| Field                     | Type     | Required | Details                                                |
| ------------------------- | -------- | -------- | ------------------------------------------------------ |
| Name                      | Text     | Yes      | Project identifier, max 30 characters                  |
| Start Date                | Date     | Yes      | Supports backdating                                    |
| End Date                  | Date     | No       | Leave blank for ongoing projects                       |
| Description               | Text     | No       | Project explanation                                    |
| Outlet/Branch             | Dropdown | Yes      | Tag for automatic attendance allocation to the project |
| Project Roles             | Multi    | No       | Associate pre-created roles with this project          |
| Auto-assign New Employees | Checkbox | No       | Automatically assign all new employees to this project |
| Archive                   | Checkbox | No       | Mark project as inactive (hides from active lists)     |

### 10.2 Employee Assignment

- Navigate: Projects > Projects > click employee count in "Employees" column
- Displays list of currently assigned employees
- Supports bulk assign/unassign via multi-select + bottom action buttons
- Green banner confirmation on success
- Employees can also be auto-assigned via the project's "Auto-assign New Employees" checkbox

### 10.3 Employee Assignment Types

Three distinct types that determine how labour cost is tracked:

| Assignment Type | Method                     | Details                                                                                          |
| --------------- | -------------------------- | ------------------------------------------------------------------------------------------------ |
| **Time Sheet**  | Manual hour input          | Admin/manager/employee manually enters hours per project per day                                 |
| **Attendance**  | Attendance log import      | Auto-generates time allocation from imported clock-in/out logs; relies on employee check-in data |
| **Allocations** | Percentage or fixed amount | Manual input of salary percentage, nominal amount, or equal-split across projects                |

- Changed via: Projects > Employees > Edit
- Project calculations are broken down by assignment type
- An employee can have different assignment types across different projects

### 10.4 Timesheets

**Purpose:** Track the number of hours each employee contributes to each project.

| Field     | Type     | Required | Details                                                           |
| --------- | -------- | -------- | ----------------------------------------------------------------- |
| Employee  | Dropdown | Yes      | Must be assigned to the project via timesheet assignment type     |
| Date      | Date     | Yes      | The specific date of work                                         |
| Project   | Dropdown | Yes      | Must be an active project already assigned to the employee        |
| Hours     | Number   | Yes      | Whole hours worked on this project                                |
| Minutes   | Number   | Yes      | Additional minutes beyond whole hours                             |
| Rate Type | Dropdown | Yes      | Determines how costing is calculated (e.g., normal rate, OT rate) |

**Who can create timesheets:**

- Admins: Projects > Time Sheet > New Time Sheets
- Managers: Projects > Staff Timesheet (create for subordinates)
- Employees: Projects > My Time Sheet > New Time Sheet (self-service)

### 10.5 Attendance Log Import

- Navigate: Projects > Time Sheets > Import Attendance Logs
- Select month, then submit
- Previous imports for the month are overwritten by new imports
- Prerequisite: attendance logs must exist (created manually or via employee clock-in)
- Attendance-based tracking uses actual clock-in/out timings rather than estimated hours

### 10.6 Project Roles

**Purpose:** Assign specific roles and hourly rates to employees per project. Same employee can have different roles on different projects (e.g., Project Manager on Project A, Advisor on Project B).

| Field              | Type     | Required | Details                       |
| ------------------ | -------- | -------- | ----------------------------- |
| Name               | Text     | Yes      | Role identifier               |
| Hourly Rate        | Currency | Yes      | Rate for the project role     |
| Assign to Projects | Multi    | Yes      | Which projects use this role  |
| Remarks            | Text     | No       | Brief description             |
| Archive            | Checkbox | No       | Mark role as no longer in use |

- Only admins can create, view, and edit project roles
- Navigate: Projects > Project Roles > + New Project Role

### 10.7 Project Overheads

**Purpose:** Ongoing business costs incurred by the company but not directly attributable to the project (rent, utilities, admin costs, etc.).

| Field           | Type     | Required | Details                                                                                                                                           |
| --------------- | -------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Type            | Dropdown | Yes      | **Project-based** (applied to entire project) or **Employee-based** (included only if employee logged time on that project in the selected month) |
| Name            | Text     | Yes      | Overhead identifier                                                                                                                               |
| Description     | Text     | No       | Brief explanation of the overhead purpose                                                                                                         |
| Months          | Multi    | Yes      | One or multiple months the overhead applies to                                                                                                    |
| Amount by Month | Currency | Yes      | Monthly cost value                                                                                                                                |
| Remarks         | Text     | No       | Additional comments                                                                                                                               |

- Navigate: Projects > Overheads > + New Overhead
- Created overheads remain editable after creation

### 10.8 Allocations

**Purpose:** Break down each employee's salary contribution across projects by percentage, fixed amount, or equal split.

| Field            | Type     | Required | Details                                                                                                                          |
| ---------------- | -------- | -------- | -------------------------------------------------------------------------------------------------------------------------------- |
| Employee         | Dropdown | Yes      | The employee to allocate                                                                                                         |
| Month            | Dropdown | Yes      | The time period for the allocation                                                                                               |
| Allocation Type  | Dropdown | Yes      | **Percentage** (manual % per project), **Nominal** (fixed dollar amount), **Equal** (auto-split equally among selected projects) |
| Base Amount Type | Dropdown | Yes      | **Salary** (sum of gross salary + pay items + employer CPF + SDL) or **Custom fixed amount**                                     |
| Projects         | Multi    | Yes      | Which projects receive the allocation                                                                                            |
| Remarks          | Text     | No       | Descriptive notes                                                                                                                |

- "Add Row" button to create multiple allocations for different projects in one submission
- Allocations can be edited and deleted after creation
- Prerequisites: employees must be assigned according to preferred assignment types first

### 10.9 Pay Item Integration

- When creating/editing pay items, there is a checkbox: **"Exclude this pay item from project costing"**
- By default, pay items are included in project cost calculations
- Base salary amount for allocations = gross salary + pay items + employer CPF + SDL (all non-excluded items)

### 10.10 Project Calculations

**Purpose:** Estimate the cost of each project from overheads, employees' salaries, and claims.

| Field           | Type     | Required | Details                                           |
| --------------- | -------- | -------- | ------------------------------------------------- |
| Select Month    | Dropdown | Yes      | Calculation period month                          |
| Select Year     | Dropdown | Yes      | Calculation period year                           |
| Select Projects | Multi    | No       | Specific projects or leave blank for all projects |

**Workflow:**

1. Prerequisite: Payroll must be generated for employees first
2. Navigate: Projects > Project Calculations > + New Calculations
3. All calculations start in **unapproved** status
4. Click eye icon for detailed breakdown of timesheets, allocations, and overheads
5. Click **Approve** to finalize (irreversible)
6. After approval, generate project costing report for consolidated summary

### 10.11 Project Costing Report

| Field | Type     | Required | Details             |
| ----- | -------- | -------- | ------------------- |
| Month | Dropdown | Yes      | Report period month |
| Year  | Dropdown | Yes      | Report period year  |

**Available filters:** Organisations, Departments, Positions, Employees, Projects

- Output format: **Excel (.xlsx)** with full breakdown of project calculations
- Download via cloud icon in top right
- Prerequisites: Project Calculations must be generated and approved first
- Listed in Payboy reports as "Project Costings -- Costing breakdown of each project"

### 10.12 Project Settings

| Setting                             | Type   | Details                                          |
| ----------------------------------- | ------ | ------------------------------------------------ |
| Enable Project Module for Employees | Toggle | Show/hide project module in employee portal      |
| Auto-assign New Projects            | Toggle | Auto-assign new projects to all active employees |

Navigate: Projects > Project Settings

---

## MODULE 11: INVENTORY

### 11.0 Overview

The Inventory module tracks assets and equipment issued to employees with a complete audit trail, approval and acknowledgment process. Designed for onboarding/offboarding asset management and ongoing equipment tracking. Also supports finance team depreciation management when all assets are tracked on a single digital platform.

**Three-tier hierarchy:** Inventory Locations > Inventories > Inventory Items

### 11.1 Setup Step 1: Inventory Locations

Navigate: Inventories > Inventory Locations > Add new inventories location

| Field              | Type     | Required | Details                                                  |
| ------------------ | -------- | -------- | -------------------------------------------------------- |
| Organisation Scope | Dropdown | Yes      | "Specific Organisation" or "All Organisations"           |
| Location Name      | Text     | Yes      | Physical storage area name (e.g., office address, floor) |
| Organisation       | Dropdown | Cond.    | Required if "Specific Organisation" selected             |

### 11.2 Setup Step 2: Inventories (Named Containers)

Navigate: Inventories > Inventories > Add New Inventory

| Field                  | Type     | Required | Details                                                                                                                                   |
| ---------------------- | -------- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Inventory Name         | Text     | Yes      | The category/container name (e.g., "Laptops", "Office Keys")                                                                              |
| Permitted Issuers      | Config   | Yes      | Who can issue items. Options: **Specific Positions** (e.g., "HR executives") and/or **Specific Employees** (exceptions to position rules) |
| Permitted Requesters   | Config   | Yes      | Who can request items. Same options as issuers                                                                                            |
| Require Acknowledgment | Checkbox | No       | If checked, employees must acknowledge receipt via system                                                                                 |

**Key distinction:** "Inventories" is the name/category. "Inventory Items" represent the quantity of each item within that category.

### 11.3 Setup Step 3: Inventory Items

After location and inventory setup, add items to specific inventories.

| Field        | Type     | Required | Details                                 |
| ------------ | -------- | -------- | --------------------------------------- |
| Organisation | Dropdown | Yes      | Which organisation the item belongs to  |
| Location     | Dropdown | Yes      | Which location the item is allocated to |
| Quantity     | Number   | Yes      | Number of this item available           |

**Note:** Payboy's inventory module does NOT have dedicated fields for serial number, category/subcategory, purchase date, purchase price, depreciation schedule, or warranty expiry. Items inherit their parent inventory's permissions. The model is quantity-based, not individual-asset-based.

### 11.4 Item Status States

| Status                     | Description                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| **Available**              | Item ready for any employee; can be reserved or issued                                             |
| **Reserved**               | Admin has pre-allocated item for specific employee but not yet physically issued                   |
| **Issued**                 | Item physically transferred to employee                                                            |
| **Pending Acknowledgment** | Item issued but employee has not yet confirmed receipt (only if Require Acknowledgment is enabled) |

### 11.5 Reserve Workflow

1. Navigate: All Inventory Items > click **Reserve** button next to item
2. Select which employee to reserve the item for
3. Click **Reserve** to confirm
4. Use case: items purchased but not yet arrived (e.g., laptops on order), or pre-staging for new hire onboarding
5. After reservation, admin can **Issue** the item or **Cancel** the reservation

### 11.6 Issue Workflow

1. Navigate: All Inventories > click **Issue** button
2. Select recipient employee + issue timestamp
3. Click confirm
4. If "Require Acknowledgment" is enabled on the parent inventory:
   - Issue Acknowledgment field shows **"Pending"**
   - Employee navigates: Inventory > My Inventory Records
   - Employee clicks **"Acknowledge"** to confirm physical receipt
   - Status updates to fully issued
5. Only one employee per reserved item at issue time

### 11.7 Employee Request Workflow

**Submission (by employee):**

1. Navigate: Inventories > My Inventory Requests > **"+ Request Inventory"**
2. Select inventory item from dropdown
3. "Current available quantity" displays automatically
4. Submit request (allowed even if quantity = 0)
5. Status shows **"Pending"**

**Restrictions:** Employees can only request items belonging to their own organisation.

**Admin/Manager Response:**

1. Navigate: Inventories > Inventory Requests
2. Click request for detail view
3. Three available actions:
   - **Reserve** -- pre-allocate for the employee
   - **Issue** -- directly issue to the employee
   - **Deny** -- reject the request (required: "reason for denying" text field)
4. Employee receives notification with outcome (including denial reason if applicable)

### 11.8 Movement Audit Log

- Access: All Inventory Items > eye icon on specific item
- Tracked data per movement:
  - Date/time stamps
  - Employee recipient identification
  - Complete transfer history (all status transitions)
  - Action performed (reserved, issued, returned, etc.)

### 11.9 What Payboy Inventory Does NOT Have

| Missing Feature              | Details                                                   |
| ---------------------------- | --------------------------------------------------------- |
| Serial number tracking       | No per-unit serial numbers; quantity-based only           |
| Categories/subcategories     | No nested categorisation beyond the inventory name        |
| Purchase date / price        | No financial tracking per item                            |
| Depreciation calculations    | Marketing mentions it but no visible fields in the module |
| Warranty / maintenance dates | Not tracked                                               |
| Barcode / QR code            | No scanning support                                       |
| Item photos                  | Not documented                                            |
| Return workflow              | No explicit return-to-inventory process documented        |
| Bulk import                  | Not documented                                            |
| Custom fields on items       | Not supported                                             |
| Check-out / check-in dates   | Only issue timestamp; no scheduled return date            |
| Condition tracking           | No "new/good/damaged" status                              |

---

## MODULE 12: EMPLOYEE LIFECYCLE

### 12.1 Onboarding

| Field Category          | Fields                                                                                                                                              |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Personal                | Name, Email, DOB, Gender, Marital Status, Religion, Race, Nationality, Citizenship, Contact Number, Home Address, Family Members, Emergency Contact |
| Identification          | Identity Number Type, Identification Number (NRIC, FIN)                                                                                             |
| Organization            | Organization, Country of Work, Department, Position, Employee Number (optional), Tags (optional)                                                    |
| Employment              | Start Date, Employment Type (full-time, part-time, contract, probation)                                                                             |
| Compensation            | Salary Type (Monthly/Hourly/Daily), Currency, Amount, Additional Hourly Rate                                                                        |
| Payment                 | Payment Method (Cash/Cheque/GIRO/Others), Bank Account Details (if GIRO)                                                                            |
| Work Schedule           | Work Hours Config (Fixed Days/Fixed Timing/Shift Planning/Flexible), Holiday Group, OT eligibility                                                  |
| Statutory               | SDL exclusion, AIS exclusion, CPF status (include/exclude/full employer), SHG donation status/fixed amount, MBMF components, Community Chest opt-in |
| System                  | Customized Password                                                                                                                                 |
| Self-service onboarding | Employee can complete in ~5 minutes                                                                                                                 |

### 12.2 Employee Management

| Feature               | Details                                                                   |
| --------------------- | ------------------------------------------------------------------------- |
| Employee transfers    | Move between organizations/departments                                    |
| Position reassignment | Change position with career history record                                |
| Salary adjustment     | Fixed amount, percentage, or decrement; individual or bulk "Apply to All" |
| Salary proration      | Auto-calculated for mid-period changes                                    |
| Employee groups       | Custom groupings for permission/reporting                                 |
| Employee tags         | Free-form labels for organization                                         |
| Employee forms        | Custom form management                                                    |
| Career history        | Tracked changes (cannot delete once payroll generated)                    |
| MoM Form Survey       | Ministry of Manpower survey support                                       |

### 12.3 Offboarding

| Field                          | Type        | Details                                                     |
| ------------------------------ | ----------- | ----------------------------------------------------------- |
| Termination date               | Date        | Employment end date                                         |
| Reason for termination         | Dropdown    | Predefined reasons                                          |
| Elaboration                    | Text        | Optional context                                            |
| Resignation documents          | File upload | Supporting documentation                                    |
| Email notification to employee | Toggle      | Send/suppress offboarding email                             |
| Offboarding instructions       | Text        | Custom text (email content is automated and not modifiable) |
| CC field                       | Email       | Carbon-copy additional recipients                           |
| Employee status                | Auto        | "Terminating" (future date) or "Resigned" (past date)       |
| Cancel offboarding             | Button      | Reverse offboarding action                                  |
| Re-onboarding                  | Feature     | Simplified re-hire using existing records                   |

---

## MODULE 13: COST CENTRES

| Feature                       | Details                                                                           |
| ----------------------------- | --------------------------------------------------------------------------------- |
| Create cost centre            | Name + code                                                                       |
| Assign to employees           | Via Employment Details dropdown                                                   |
| Position reassignment method  | Creates career history record                                                     |
| Claims integration            | Cost centre field on claim submissions; pre-fills from employee's assigned centre |
| Reports integration           | New columns in Employee, Claims, Payroll reports                                  |
| Filter reports by cost centre | Isolate costs to specific centres                                                 |

---

## MODULE 14: ATS (APPLICANT TRACKING SYSTEM)

### 14.0 Overview

The ATS module enables creating job listings with unique application links, consolidating candidates from multiple sources, customizing application forms per role, tracking candidates through a kanban-style pipeline, and directly onboarding hired candidates into the employee system.

**Note:** This is Payboy's lightest module with the least documentation. G2 reviewers note it "lacks features like real-time updates." The information below combines support docs, marketing pages, and a live application form analysis.

### 14.1 Job Listing Creation

Navigate: ATS > New Job Listing

**Process:**

1. Position must first be created under Company > Organization
2. Click "New Job Listing"
3. Fill in job details
4. Configure basic information fields (enable/disable fields, mark as mandatory)
5. Customize application template via drag-and-drop form builder
6. Check "Publish" checkbox to make listing live
7. Submit -- generates a unique URL for the listing

**Job Listing Fields (inferred from live listings and docs):**

| Field           | Type      | Details                                                      |
| --------------- | --------- | ------------------------------------------------------------ |
| Position        | Dropdown  | Must pre-exist in Company > Organization                     |
| Organisation    | Dropdown  | Which company entity the position belongs to                 |
| Department      | Dropdown  | Pre-configured department                                    |
| Employment Type | Text      | e.g., "Permanent, Full-Time"                                 |
| Location        | Text      | e.g., "Island Wide"                                          |
| Job Description | Rich Text | Description of the role                                      |
| Publish         | Checkbox  | Makes listing publicly accessible via unique URL             |
| Unique Link     | Auto      | System-generated URL (e.g., payboy.biz/job_applications/xxx) |

### 14.2 Application Form Fields

The application form is customizable per job listing via drag-and-drop. Based on analysis of live Payboy application forms, the available field categories are:

**Personal Information:**

| Field              | Type     | Details                                                                                           |
| ------------------ | -------- | ------------------------------------------------------------------------------------------------- |
| Full Name          | Text     | Applicant's legal name                                                                            |
| ID Type            | Dropdown | NRIC, FIN, Work Permit, Passport, etc.                                                            |
| ID Number          | Text     | Identity document number                                                                          |
| Email Address      | Email    | Contact email                                                                                     |
| Mobile Number      | Phone    | Primary contact                                                                                   |
| Home Phone         | Phone    | Optional                                                                                          |
| Office Phone       | Phone    | Optional                                                                                          |
| Gender             | Dropdown | Male / Female / Others                                                                            |
| Date of Birth      | Date     | DOB                                                                                               |
| Marital Status     | Dropdown | Single / Married / Divorced / Widowed                                                             |
| Race               | Dropdown | 13 options (Chinese, Indian, Malay, Eurasian, Caucasian, etc.)                                    |
| Religion           | Dropdown | 9 options (Buddhist, Christian, Free Thinker, Hindu, Muslim, Taoist, Sikh, Catholic, None/Others) |
| Nationality        | Dropdown | Comprehensive global list                                                                         |
| Citizenship Status | Dropdown | Citizen / Permanent Resident / Foreigner                                                          |
| Home Address       | Text     | Residential address                                                                               |
| Emergency Contact  | Text     | Emergency contact details                                                                         |

**Employment/Financial:**

| Field          | Type     | Details                              |
| -------------- | -------- | ------------------------------------ |
| Payment Method | Dropdown | GIRO (default), Cash, Cheque, Others |
| Bank           | Dropdown | 35+ Singapore bank options           |
| Bank Account   | Text     | Account number (if GIRO selected)    |

**Custom Questions (per listing):**

| Capability               | Details                                                                          |
| ------------------------ | -------------------------------------------------------------------------------- |
| Custom text questions    | Free-form questions (e.g., "Reason for leaving?")                                |
| Custom text input fields | Short answer (e.g., "Current Drawn Salary?", "Expected Salary", "Notice Period") |
| File upload              | Resume / CV attachment                                                           |
| Mandatory flag           | Each field can be toggled mandatory or optional                                  |
| Enable/disable per field | Admins choose which standard fields appear on each listing                       |

### 14.3 Candidate Pipeline

The ATS uses a **kanban-style board** where applicants can be dragged and dropped between columns.

**Pipeline stages** (exact stage names not documented in support articles, but standard Payboy implementation based on the kanban description and industry pattern):

| Stage (Inferred) | Details                                             |
| ---------------- | --------------------------------------------------- |
| New / Applied    | Initial stage when application is submitted         |
| Screening        | HR reviewing application details                    |
| Shortlisted      | Candidate passes initial screening                  |
| Interview        | Candidate scheduled for interview                   |
| Offered          | Offer extended to candidate                         |
| Hired            | Candidate accepted, ready for onboarding            |
| Rejected         | Candidate not progressing (can happen at any stage) |

**Note:** Payboy allows "creating unique workflows for different roles" suggesting stages may be customizable, but specific documentation on custom stage creation is not publicly available.

### 14.4 Candidate Management

- Click into an applicant to view their submitted form data ("Open Applicant's Form")
- All application data from all job portals consolidated in one view
- Stored application details persist and are accessible for future hiring needs (talent pool)
- Automated resume screening based on predefined criteria (qualifications, experience, skills)
- Collaborative feedback from multiple interviewers with audit trails
- Automated workflows for interview scheduling, candidate follow-ups, and status updates

### 14.5 Direct Onboarding (Candidate to Employee)

When a candidate reaches "Hired" status:

1. Click **"Onboard"** button on the candidate record
2. System redirects to the standard employee onboarding page
3. Candidate's application data pre-fills relevant onboarding fields
4. Complete the normal onboarding process (pay scheme, work schedule, statutory details)
5. Candidate becomes an active employee in the system

**Data flow:** Application fields (name, ID, contact, bank details) carry forward to avoid re-entry.

### 14.6 Job Board Integrations

| Integration          | Details                                           |
| -------------------- | ------------------------------------------------- |
| Unique shareable URL | Generated per listing, can be posted anywhere     |
| Job portal posting   | "Every application from every job portal" claim   |
| LinkedIn             | Referenced by competitor QuickHR (Payboy unclear) |
| Indeed               | Referenced by competitor QuickHR (Payboy unclear) |
| JobStreet            | Referenced by competitor QuickHR (Payboy unclear) |

**Note:** Payboy's documentation says it consolidates from "every job portal" but does not enumerate specific integrations. The unique URL approach means admins manually post the link to external job boards rather than having API-level integrations.

### 14.7 Reports / Analytics

- **No dedicated ATS reports** listed in Payboy's 16-report catalog
- "Tracking reports" mentioned in marketing but no specifics on what metrics are tracked
- No documented dashboards for time-to-hire, pipeline conversion, source effectiveness, etc.

### 14.8 What Payboy ATS Does NOT Have

| Missing Feature             | Details                                                          |
| --------------------------- | ---------------------------------------------------------------- |
| Dedicated ATS reports       | No recruitment-specific reports in the reports module            |
| Real-time status updates    | Noted as missing by G2 reviewers                                 |
| API-level job board posting | Manual URL sharing only; no auto-post to LinkedIn/Indeed         |
| Interview scheduling        | No calendar integration documented (QuickHR has this)            |
| Offer letter templates      | Not documented (marketing mentions "customizable" but no detail) |
| AI-powered screening        | No documented AI/ML features for candidate ranking               |
| Candidate scoring/rating    | Not documented                                                   |
| Email templates             | No documented automated candidate communication                  |
| Career page builder         | No white-label career page; just application form links          |
| Requisition approval flow   | No documented hiring manager approval before posting             |
| Multi-language support      | Not documented                                                   |
| PDPA consent management     | Not documented for candidate data                                |

---

## MODULE 15: ADDITIONAL MODULES

| Module                 | Details                                                                         |
| ---------------------- | ------------------------------------------------------------------------------- |
| COVID Safe+            | Vaccination group tracking, health compliance                                   |
| Entry Devices          | Physical access point management                                                |
| Facial Recognition     | Biometric device integration for attendance                                     |
| Learning & Development | Training program management (referenced in admin guide but limited public docs) |

---

## PRICING MODEL

| Detail                   | Information                            |
| ------------------------ | -------------------------------------- |
| Billing                  | Pay-per-use model                      |
| All 14 modules           | Included for active users              |
| Time & Attendance add-on | $2.50/module/employee/month            |
| Rostering add-on         | $2.50/module/employee/month            |
| Free trial               | 14 days, no credit card                |
| PSG Grant eligible       | Productivity Solutions Grant           |
| NCSS NGO Grant           | Available for non-profits              |
| Migration promotions     | For users switching from other systems |

---

## COMPETITOR COMPARISON: PROJECT COSTING, INVENTORY, ATS

### Competitor: QuickHR (quickhr.co)

**ATS/Recruitment:**

- Multi-portal job posting with API-level integration to LinkedIn, Indeed, JobStreet
- Smart Search and Screening with candidate comparison
- Interview scheduling with calendar integration (Google Cal, iCal, Outlook via ICS)
- Real-time status tracking across all applicants
- Seamless onboarding: hired applicants auto-transfer to Employee Database
- Automated documentation disbursement for digital onboarding
- Talent pipeline for future hiring (persistent candidate database)
- Multilingual support (important for Singapore's diverse workforce)

**Inventory/Equipment:**

- Equipment assignment and tracking
- Date of issue and date of return tracking
- Available across multiple pricing tiers

**Project Costing:** Not offered as a standalone module.

### Competitor: HReasily (hreasilygroup.com)

**Project Costing:** Listed as a feature but with minimal public documentation. Includes GPS/facial recognition attendance which could feed project tracking.

**ATS:** Not prominently featured.

**Inventory:** Not a standalone module.

**Pricing:** Modular from S$1.50/module, full suite from S$10/employee/month. PSG Grant eligible.

### Competitor: Swingvy (swingvy.com)

Focuses on HR Hub, Leave, Claims, Time-tracking, Payroll. Does NOT offer project costing, inventory, or ATS as distinct modules.

### Competitor: Talenox (talenox.com)

Freemium model. Strong payroll and leave. Blog discusses ATS-payroll bridging but no built-in ATS module. No project costing or inventory.

### Competitor: Info-Tech (info-tech.com.sg)

**Asset Management:** Tracks assets assigned to staff, loans, insurance. Transparent tracking from purchase to depreciation to disposal. Limited public detail on specific fields.

**Recruitment:** Basic candidate screening checklists during onboarding/offboarding. No full ATS pipeline.

**Project Costing:** Not documented as a module.

### Industry Best Practices (from dedicated tools)

**Project Costing best practices (from construction/professional services ERP):**

- Budget vs actual tracking with variance analysis
- Billable vs non-billable hour categorization
- Multi-level cost categories (labour, materials, subcontractor, overhead)
- Project profitability analysis with margin calculations
- Time approval workflows before cost allocation
- Integration with invoicing/billing

**Asset Management best practices (from dedicated asset tools like Snipe-IT, InvGate):**

- Individual asset tracking with serial numbers, barcodes, QR codes
- Asset lifecycle: procurement > assignment > maintenance > depreciation > disposal
- Custom fields per asset type
- Check-out/check-in with due dates
- Condition tracking (new/good/fair/damaged/disposed)
- Maintenance scheduling and alerts
- Photo documentation
- Bulk import/export via CSV
- Asset categories and subcategories

**ATS best practices (from dedicated recruitment tools like Greenhouse, Lever):**

- Customizable pipeline stages per job
- Structured interview scorecards
- Multi-channel sourcing with attribution tracking
- PDPA/GDPR consent management for candidate data
- Career page builder with employer branding
- Automated email sequences per stage transition
- Time-to-hire and source-effectiveness dashboards
- Requisition approval workflow before job posting
- Candidate de-duplication
- Referral tracking
- Interview scheduling with calendar integration
- Offer letter generation and e-signature

---

## GAPS / OPPORTUNITIES FOR COMPETITIVE ADVANTAGE

Based on this analysis, areas where Payboy is limited and we can differentiate:

1. **No built-in payroll calculation engine** for FWL -- relies on MOM, no auto-calculation
2. **IR21 is manual** -- no integrated API submission
3. **Appendix 8B not documented** -- potential gap
4. **No multi-level approval** beyond 2 tiers
5. **Single-day holiday entry** -- no date range support
6. **Attendance settings are uniform** -- no per-employee customization
7. **Limited ATS** -- basic job listing + kanban, no recruitment reports, no calendar integration, no job board APIs, no candidate scoring, no PDPA consent
8. **No LMS/training tracking** -- minimal learning & development
9. **No built-in expense analytics/dashboards** -- reports are Excel/PDF only
10. **No AI/advisory features** -- pure transactional HRIS
11. **No government API integrations** (IRAS API only for IR8A, not IR21; no MOM API)
12. **No bank API integrations** -- GIRO files must be manually uploaded to bank portals
13. **No mobile push for leave/claims status** -- email-only notifications for most events
14. **No payroll simulation/preview** before generation
15. **No employee self-service salary history** view
16. **No built-in org chart visualization**
17. **No succession planning or talent management**
18. **No built-in communication/messaging** beyond announcements
19. **No workflow automation builder** -- fixed approval flows only
20. **No API/webhook platform** for third-party integrations beyond Xero/QuickBooks/Financio
21. **Inventory lacks individual asset tracking** -- quantity-based only, no serial numbers, no categories, no purchase price, no depreciation, no condition tracking, no barcode/QR
22. **No inventory return workflow** -- no documented process for employees returning equipment
23. **Project costing lacks budget/actual comparison** -- calculates cost but doesn't compare to project budgets
24. **Project costing has no billable/non-billable distinction** -- no revenue side, only cost tracking
25. **No project profitability analysis** -- shows cost but not margin or profit
26. **Project costing rate types not documented** -- unclear what specific rate types are available
27. **ATS has no career page builder** -- only generates plain application form links
28. **ATS has no structured interview scorecards** -- no standardized evaluation criteria per role
29. **ATS has no candidate source tracking** -- cannot measure which job boards produce best hires
30. **ATS has no referral tracking** -- no employee referral program support
