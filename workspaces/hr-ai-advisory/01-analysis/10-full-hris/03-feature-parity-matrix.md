# Feature Parity Matrix: Payboy vs Talenox vs AITE

## Sources

- [Payboy Payroll](https://payboy.sg/solutions/payroll-software/)
- [Payboy Leave](https://payboy.sg/solutions/leave)
- [Payboy Claims](https://payboy.sg/solutions/claims/)
- [Payboy Attendance](https://payboy.sg/solutions/attendance/)
- [Payboy Shift Scheduling](https://payboy.sg/solutions/shift-scheduling/)
- [Talenox Payroll Features](https://help.talenox.com/en/collections/66417-payroll-features)
- [Talenox Employee Profile](https://help.talenox.com/en/articles/672654-employee-profile-details-singapore)

---

## 1. PAYROLL ENGINE

### Salary Calculation

| Feature                                            | Payboy | Talenox               | AITE Status                           |
| -------------------------------------------------- | ------ | --------------------- | ------------------------------------- |
| Gross-to-net calculation                           | Yes    | Yes                   | NEED (have calculators, need wrapper) |
| Full-time payroll                                  | Yes    | Yes                   | NEED                                  |
| Part-time payroll (hourly/daily)                   | Yes    | Yes                   | NEED                                  |
| Freelancer/contractor payroll                      | Yes    | Yes                   | NEED                                  |
| Weekly/bi-weekly/monthly frequency                 | Yes    | Yes                   | NEED                                  |
| Mid-month hire proration                           | Yes    | Yes                   | NEED                                  |
| Mid-month resignation proration                    | Yes    | Yes                   | NEED                                  |
| Back-pay / salary adjustment                       | Yes    | Yes                   | NEED                                  |
| Bonus / 13th month / AWS processing                | Yes    | Yes (separate AW run) | NEED                                  |
| Commission (daily/weekly/monthly/irregular)        | Yes    | Yes                   | NEED                                  |
| Overtime calculation (Part IV EA)                  | Yes    | Yes                   | HAVE (calculator exists)              |
| Allowances (transport, meal, housing, phone, etc.) | Yes    | Yes                   | NEED (model field)                    |
| Deductions (loan repayment, union dues, insurance) | Yes    | Yes                   | NEED (model field)                    |
| No-pay leave deduction                             | Yes    | Yes                   | NEED                                  |
| Per diem allowance                                 | ?      | Yes                   | NEED                                  |
| Employee Stock Purchase Plan (ESPP)                | No     | Yes                   | DEFER                                 |

### Statutory Calculations

| Feature                                           | Payboy | Talenox | AITE Status       |
| ------------------------------------------------- | ------ | ------- | ----------------- |
| CPF (employee + employer, SC/PR tiers, age bands) | Yes    | Yes     | HAVE (calculator) |
| CPF OW ceiling ($8,000)                           | Yes    | Yes     | HAVE              |
| CPF AW ceiling (annual)                           | Yes    | Yes     | HAVE              |
| CPF YTD tracking across runs                      | Yes    | Yes     | NEED              |
| CPF PR Year 1/2/3 graduated rates                 | Yes    | Yes     | HAVE              |
| CPF proration for PR status change                | Yes    | Yes     | NEED              |
| SDL (Skills Development Levy)                     | Yes    | Yes     | HAVE (calculator) |
| Foreign Worker Levy (FWL)                         | Yes    | Yes     | HAVE (calculator) |
| Self-Help Group funds (CDAC/MBMF/SINDA/ECF)       | Yes    | Yes     | NEED              |
| Platform Workers CPF (PCTS scheme)                | No     | Yes     | DEFER             |

### File Generation & Submissions

| Feature                                         | Payboy | Talenox | AITE Status                 |
| ----------------------------------------------- | ------ | ------- | --------------------------- |
| CPF e-Submit file generation                    | Yes    | Yes     | NEED                        |
| CPF APEX online submission                      | No     | Yes     | DEFER                       |
| IR8A auto-generation                            | Yes    | Yes     | NEED                        |
| IR8A AIS direct submission to IRAS              | Yes    | Yes     | DEFER (generate file first) |
| Appendix 8A (benefits in kind)                  | Yes    | Yes     | NEED                        |
| Appendix 8B (stock options)                     | No     | Yes     | DEFER                       |
| IR21 (departing foreign employees)              | Yes    | Yes     | NEED                        |
| IR8S (refund/voluntary contribution)            | No     | Yes     | DEFER                       |
| Bank GIRO file (DBS/UOB/OCBC/Maybank/CIMB/HSBC) | Yes    | Yes     | NEED                        |
| Bank FAST payment file                          | No     | Yes     | DEFER                       |

### Payslips & Reports

| Feature                              | Payboy | Talenox | AITE Status |
| ------------------------------------ | ------ | ------- | ----------- |
| Itemised payslip (EA s88A compliant) | Yes    | Yes     | NEED        |
| Payslip PDF download                 | Yes    | Yes     | NEED        |
| Payslip email delivery               | Yes    | Yes     | NEED        |
| Mobile payslip access                | Yes    | Yes     | NEED        |
| Customisable payslip format          | Yes    | Yes     | NEED        |
| Payroll summary report               | Yes    | Yes     | NEED        |
| YTD report                           | Yes    | Yes     | NEED        |
| Payment reconciliation report        | Yes    | Yes     | NEED        |

### Accounting Integration

| Feature                | Payboy | Talenox | AITE Status |
| ---------------------- | ------ | ------- | ----------- |
| Xero integration       | Yes    | Yes     | DEFER       |
| QuickBooks integration | Yes    | No      | DEFER       |
| Financio integration   | Yes    | No      | DEFER       |

---

## 2. LEAVE MANAGEMENT

| Feature                                   | Payboy | Talenox | AITE Status         |
| ----------------------------------------- | ------ | ------- | ------------------- |
| Annual leave (service-year based)         | Yes    | Yes     | HAVE (calculator)   |
| Sick leave (14 days outpatient)           | Yes    | Yes     | HAVE                |
| Hospitalisation leave (60 days)           | Yes    | Yes     | HAVE                |
| Maternity leave (16 weeks GPML)           | Yes    | Yes     | HAVE (calculator)   |
| Paternity leave (4 weeks GPPL)            | Yes    | Yes     | HAVE                |
| Childcare leave (6 days)                  | Yes    | Yes     | HAVE                |
| Extended childcare leave (2 days)         | Yes    | Yes     | HAVE                |
| Shared parental leave (4 weeks)           | Yes    | Yes     | HAVE                |
| Adoption leave                            | Yes    | Yes     | NEED                |
| NS leave (reservist)                      | Yes    | ?       | NEED                |
| Compassionate leave                       | Yes    | ?       | NEED                |
| Marriage leave                            | Yes    | ?       | NEED                |
| Study/exam leave                          | Yes    | ?       | NEED                |
| Unpaid leave                              | Yes    | Yes     | NEED                |
| Off-in-lieu (TOIL / replacement leave)    | Yes    | Yes     | NEED                |
| Half-day leave                            | Yes    | Yes     | NEED                |
| Hourly leave                              | Yes    | ?       | NEED                |
| Custom leave types                        | Yes    | Yes     | NEED                |
| Leave application (employee self-service) | Yes    | Yes     | NEED                |
| Leave approval workflow (manager)         | Yes    | Yes     | NEED                |
| Multi-level approval                      | Yes    | ?       | NEED                |
| Leave balance tracking                    | Yes    | Yes     | HAVE (model exists) |
| Leave carry-forward rules                 | Yes    | Yes     | NEED                |
| Leave encashment                          | Yes    | ?       | NEED                |
| Leave proration (mid-year joiner)         | Yes    | Yes     | HAVE (calculator)   |
| Leave calendar (team view)                | Yes    | Yes     | NEED                |
| Public holiday integration (SG gazetted)  | Yes    | Yes     | NEED                |
| Leave policy by employee group            | Yes    | Yes     | NEED                |

---

## 3. CLAIMS & EXPENSES

| Feature                                | Payboy | Talenox | AITE Status |
| -------------------------------------- | ------ | ------- | ----------- |
| Digital claim submission               | Yes    | ?       | NEED        |
| Receipt photo upload (mobile)          | Yes    | ?       | NEED        |
| Multiple receipt attachments (up to 5) | Yes    | ?       | NEED        |
| Customisable claim categories          | Yes    | ?       | NEED        |
| Claim limits per role/project          | Yes    | ?       | NEED        |
| Claim approval workflow                | Yes    | ?       | NEED        |
| Approval audit trail                   | Yes    | ?       | NEED        |
| Claims-to-payroll integration          | Yes    | ?       | NEED        |
| Accounting sync (Xero/QuickBooks)      | Yes    | ?       | DEFER       |
| Mobile claim submission                | Yes    | ?       | NEED        |

---

## 4. ATTENDANCE & TIME TRACKING

| Feature                          | Payboy | Talenox | AITE Status |
| -------------------------------- | ------ | ------- | ----------- |
| Mobile clock in/out              | Yes    | No      | NEED        |
| GPS/location-aware check-in      | Yes    | No      | NEED        |
| Photo proof of attendance        | Yes    | No      | NEED        |
| Lateness tracking (colour-coded) | Yes    | No      | NEED        |
| Overtime auto-calculation        | Yes    | No      | NEED        |
| Attendance summary per employee  | Yes    | No      | NEED        |
| Real-time sync with payroll      | Yes    | No      | NEED        |
| Multi-location support           | Yes    | No      | NEED        |
| Timesheet approval               | Yes    | No      | NEED        |

---

## 5. SHIFT SCHEDULING

| Feature                                | Payboy | Talenox | AITE Status |
| -------------------------------------- | ------ | ------- | ----------- |
| Drag-and-drop shift allocation         | Yes    | No      | NEED        |
| Availability-based scheduling          | Yes    | No      | NEED        |
| Leave-integrated availability          | Yes    | No      | NEED        |
| Schedule publishing with notifications | Yes    | No      | NEED        |
| Hours per staff tracking               | Yes    | No      | NEED        |
| Auto-payroll calculation from shifts   | Yes    | No      | NEED        |
| Mobile schedule access                 | Yes    | No      | NEED        |
| Labour law compliance (max hours)      | Yes    | No      | NEED        |

---

## 6. EMPLOYEE MANAGEMENT

| Feature                                | Payboy | Talenox | AITE Status              |
| -------------------------------------- | ------ | ------- | ------------------------ |
| Employee profile (personal details)    | Yes    | Yes     | HAVE (partial)           |
| Date of birth                          | Yes    | Yes     | NEED                     |
| NRIC / FIN                             | Yes    | Yes     | NEED                     |
| Work pass number + type                | Yes    | Yes     | NEED                     |
| Immigration status + effective date    | Yes    | Yes     | NEED                     |
| Next of kin / emergency contact        | Yes    | Yes     | NEED                     |
| Bank account details                   | Yes    | Yes     | NEED                     |
| Job title + department                 | Yes    | Yes     | HAVE                     |
| Salary components (basic + allowances) | Yes    | Yes     | NEED (have single field) |
| Hire date / resign date / job end date | Yes    | Yes     | HAVE (partial)           |
| CPF contribution rate (auto from DOB)  | Yes    | Yes     | HAVE (calculator)        |
| Employee self-service portal           | Yes    | Yes     | HAVE                     |
| Employee directory                     | Yes    | Yes     | HAVE (/employees page)   |
| Org chart                              | Yes    | ?       | NEED                     |
| Employee documents storage             | Yes    | ?       | NEED                     |
| Onboarding checklist                   | Yes    | ?       | HAVE (partial)           |
| Probation tracking                     | Yes    | ?       | HAVE (task exists)       |
| Confirmation workflow                  | Yes    | ?       | NEED                     |
| Exit / offboarding checklist           | Yes    | ?       | NEED                     |
| Final salary calculation               | Yes    | Yes     | HAVE (calculators)       |
| Employment history                     | Yes    | Yes     | NEED                     |

---

## 7. WHAT AITE HAS THAT COMPETITORS DON'T

| Feature                             | Payboy | Talenox | AITE |
| ----------------------------------- | ------ | ------- | ---- |
| AI shadow agent (command surface)   | No     | No      | HAVE |
| 6-domain compliance knowledge base  | No     | No      | HAVE |
| 14-step advisory safety chain       | No     | No      | HAVE |
| Risk-tiered advisory with citations | No     | No      | HAVE |
| Emergency response guides           | No     | No      | HAVE |
| Compliance health check             | No     | No      | HAVE |
| Regulatory change alerts            | No     | No      | HAVE |
| Document template generation        | Basic  | No      | HAVE |
| EATP trust lineage                  | No     | No      | HAVE |
| Inline compliance annotations       | No     | No      | HAVE |
| Voice input for HR queries          | No     | No      | HAVE |

---

## Summary: AITE Gap Count

| Category            | Total Features | HAVE   | NEED   | DEFER |
| ------------------- | -------------- | ------ | ------ | ----- |
| Payroll Engine      | 42             | 8      | 27     | 7     |
| Leave Management    | 27             | 10     | 17     | 0     |
| Claims & Expenses   | 10             | 0      | 9      | 1     |
| Attendance & Time   | 9              | 0      | 9      | 0     |
| Shift Scheduling    | 8              | 0      | 8      | 0     |
| Employee Management | 21             | 8      | 13     | 0     |
| **Total**           | **117**        | **26** | **83** | **8** |

83 features to build. 26 already exist. 8 deferred (ESPP, APEX CPF submission, direct AIS submission, accounting integrations, etc).
