"""Statutory file generation service.

Deterministic generation of Singapore statutory files -- zero LLM involvement.
Handles CPF e-Submit, bank GIRO, IR8A/IR21 tax data, and payslip HTML/PDF.
"""

import csv
import io
import logging
from datetime import date

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CPF e-Submit file
# ---------------------------------------------------------------------------


def generate_cpf_esubmit(
    payroll_run: dict,
    payslips: list[dict],
    employees: list[dict],
) -> str:
    """Generate CPF Board e-Submit CSV file content.

    Format: Header row + detail rows + trailer row
    Header: EMPLOYER_CPF_ACCOUNT, PAYMENT_YEAR_MONTH, EMPLOYEE_COUNT
    Detail: NRIC/FIN, EMPLOYEE_NAME, OW, AW, EMPLOYER_CPF, EMPLOYEE_CPF, TOTAL_CPF
    Trailer: TOTAL_EMPLOYER_CPF, TOTAL_EMPLOYEE_CPF, TOTAL_CPF

    Returns CSV content as a string.
    """
    # Build employee lookup by id
    emp_by_id = {e.get("id"): e for e in employees}

    # Derive payment year-month from payroll run period
    period_start = payroll_run.get("period_start", "")
    try:
        pd = date.fromisoformat(period_start)
        payment_ym = f"{pd.year}{pd.month:02d}"
    except (ValueError, TypeError):
        payment_ym = ""

    # Find employer CPF account from the first employee's company context
    # In practice this would come from company settings; use UEN as fallback
    employer_cpf_account = payroll_run.get("employer_cpf_account", "")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(
        [
            "HEADER",
            employer_cpf_account,
            payment_ym,
            len(payslips),
        ]
    )

    total_employer_cpf = 0.0
    total_employee_cpf = 0.0
    total_cpf = 0.0

    for ps in payslips:
        emp_id = ps.get("employee_id")
        emp = emp_by_id.get(emp_id, {})

        nric_fin = emp.get("nric_fin", "")
        emp_name = _get_employee_display_name(emp)
        ow = ps.get("cpf_ow_used", 0.0)
        aw = ps.get("cpf_aw_used", 0.0)
        employer_cpf = ps.get("employer_cpf", 0.0)
        employee_cpf = ps.get("employee_cpf", 0.0)
        row_total = employer_cpf + employee_cpf

        writer.writerow(
            [
                "DETAIL",
                nric_fin,
                emp_name,
                f"{ow:.2f}",
                f"{aw:.2f}",
                f"{employer_cpf:.2f}",
                f"{employee_cpf:.2f}",
                f"{row_total:.2f}",
            ]
        )

        total_employer_cpf += employer_cpf
        total_employee_cpf += employee_cpf
        total_cpf += row_total

    # Trailer row
    writer.writerow(
        [
            "TRAILER",
            f"{total_employer_cpf:.2f}",
            f"{total_employee_cpf:.2f}",
            f"{total_cpf:.2f}",
        ]
    )

    return output.getvalue()


# ---------------------------------------------------------------------------
# Bank GIRO file
# ---------------------------------------------------------------------------

# DBS fixed-width field widths (simplified)
_DBS_HEADER_TEMPLATE = (
    "H"  # Record type (1)
    "{originator:>20}"  # Originator (20)
    "{creation_date:>8}"  # DDMMYYYY (8)
    "{value_date:>8}"  # DDMMYYYY (8)
    "{company_id:>12}"  # Company ID / UEN (12)
)

_DBS_DETAIL_TEMPLATE = (
    "D"  # Record type (1)
    "{receiving_bank:>4}"  # Receiving bank code (4)
    "{account_no:>20}"  # Account number (20, right-aligned)
    "{amount:>015}"  # Amount in cents (15, zero-padded)
    "{emp_name:<40}"  # Employee name (40, left-aligned)
    "{reference:<20}"  # Payment reference (20)
)

_DBS_TRAILER_TEMPLATE = (
    "T"  # Record type (1)
    "{total:>015}"  # Total amount in cents (15, zero-padded)
    "{count:>06}"  # Record count (6, zero-padded)
)


def generate_bank_giro(
    payroll_run: dict,
    payslips: list[dict],
    employees: list[dict],
    bank_format: str = "generic",
) -> str:
    """Generate bank payment file.

    Supported formats: generic (CSV), dbs, uob, ocbc

    Generic CSV columns: EMPLOYEE_NAME, BANK_CODE, ACCOUNT_NUMBER, AMOUNT, REFERENCE
    DBS format: fixed-width text with header/detail/trailer records.
    UOB/OCBC use the generic CSV format as a fallback (banks accept CSV uploads).

    Returns file content as a string.
    """
    emp_by_id = {e.get("id"): e for e in employees}
    pay_date = payroll_run.get("pay_date", "")
    run_id = payroll_run.get("id", 0)

    if bank_format == "dbs":
        return _generate_dbs_giro(payroll_run, payslips, emp_by_id, pay_date, run_id)

    # Generic CSV (also used for uob, ocbc)
    return _generate_generic_giro(payslips, emp_by_id, pay_date, run_id)


def _generate_generic_giro(
    payslips: list[dict],
    emp_by_id: dict,
    pay_date: str,
    run_id: int,
) -> str:
    """Generate generic CSV bank file."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "EMPLOYEE_NAME",
            "BANK_CODE",
            "ACCOUNT_NUMBER",
            "AMOUNT",
            "REFERENCE",
        ]
    )

    for ps in payslips:
        emp = emp_by_id.get(ps.get("employee_id"), {})
        net_salary = ps.get("net_salary", 0.0)

        if net_salary <= 0:
            continue

        writer.writerow(
            [
                _get_employee_display_name(emp),
                emp.get("bank_code", ""),
                emp.get("bank_account_number", ""),
                f"{net_salary:.2f}",
                f"SALARY-{run_id}-{pay_date}",
            ]
        )

    return output.getvalue()


def _generate_dbs_giro(
    payroll_run: dict,
    payslips: list[dict],
    emp_by_id: dict,
    pay_date: str,
    run_id: int,
) -> str:
    """Generate DBS fixed-width GIRO file."""
    lines: list[str] = []

    # Format date as DDMMYYYY
    try:
        pd = date.fromisoformat(pay_date)
        formatted_date = f"{pd.day:02d}{pd.month:02d}{pd.year}"
    except (ValueError, TypeError):
        formatted_date = "00000000"

    company_id = str(payroll_run.get("company_id", ""))

    # Header
    lines.append("H" + f"{'':>20}" + formatted_date + formatted_date + company_id.rjust(12))

    total_cents = 0
    count = 0

    for ps in payslips:
        emp = emp_by_id.get(ps.get("employee_id"), {})
        net_salary = ps.get("net_salary", 0.0)

        if net_salary <= 0:
            continue

        amount_cents = int(round(net_salary * 100))
        total_cents += amount_cents
        count += 1

        lines.append(
            "D"
            + emp.get("bank_code", "").rjust(4)
            + emp.get("bank_account_number", "").rjust(20)
            + str(amount_cents).zfill(15)
            + _get_employee_display_name(emp).ljust(40)[:40]
            + f"SALARY-{run_id}".ljust(20)[:20]
        )

    # Trailer
    lines.append("T" + str(total_cents).zfill(15) + str(count).zfill(6))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# IR8A tax filing data
# ---------------------------------------------------------------------------


def generate_ir8a_data(
    employee: dict,
    payslips: list[dict],
    items: list[dict],
    tax_year: int,
) -> dict:
    """Generate IR8A filing data for a single employee.

    Aggregates all payslip items for the tax year into IR8A categories:
    - Gross salary/wages
    - Bonus
    - Director fees (N/A for most)
    - Commission
    - Pension/provident fund
    - Transport allowance (taxable portion)
    - Entertainment allowance (taxable portion)
    - Other allowances
    - Employer CPF contributions
    - Total gross income

    Returns dict matching IR8A form fields.
    """
    # Filter payslips to the tax year
    year_payslips = [ps for ps in payslips if ps.get("period_start", "").startswith(str(tax_year))]
    year_payslip_ids = {ps.get("id") for ps in year_payslips}

    # Filter items to only those belonging to the tax year payslips
    year_items = [item for item in items if item.get("payslip_id") in year_payslip_ids]

    # Aggregate by item type
    basic_salary = 0.0
    bonus = 0.0
    commission = 0.0
    overtime_pay = 0.0
    allowances = 0.0
    transport_allowance = 0.0
    entertainment_allowance = 0.0
    other_allowances = 0.0
    employer_cpf = 0.0
    employee_cpf = 0.0

    for item in year_items:
        item_type = item.get("item_type", "")
        amount = abs(item.get("amount", 0.0))
        name_lower = item.get("name", "").lower()

        if item_type == "basic_salary":
            basic_salary += amount
        elif item_type == "bonus":
            bonus += amount
        elif item_type == "commission":
            commission += amount
        elif item_type == "overtime":
            overtime_pay += amount
        elif item_type == "allowance":
            if not item.get("is_taxable", True):
                continue
            # Classify allowances
            if "transport" in name_lower:
                transport_allowance += amount
            elif "entertainment" in name_lower:
                entertainment_allowance += amount
            else:
                other_allowances += amount
            allowances += amount
        elif item_type == "employer_cpf":
            employer_cpf += amount
        elif item_type == "employee_cpf":
            employee_cpf += amount

    gross_salary_wages = basic_salary + overtime_pay
    total_allowances = transport_allowance + entertainment_allowance + other_allowances
    total_gross_income = gross_salary_wages + bonus + commission + total_allowances

    # Employment period within the tax year
    emp_start = employee.get("start_date", "")
    emp_end = employee.get("end_date", "")
    period_from = f"{tax_year}-01-01"
    period_to = f"{tax_year}-12-31"

    if emp_start and emp_start > period_from:
        period_from = emp_start
    if emp_end and emp_end < period_to:
        period_to = emp_end

    return {
        "filing_type": "ir8a",
        "tax_year": tax_year,
        # Employee details
        "employee_name": _get_employee_display_name(employee),
        "nric_fin": employee.get("nric_fin", ""),
        "date_of_birth": employee.get("date_of_birth", ""),
        "nationality": employee.get("nationality", ""),
        "gender": employee.get("gender", ""),
        "designation": employee.get("designation", ""),
        # Employment period
        "period_from": period_from,
        "period_to": period_to,
        # Income breakdown (Section A)
        "gross_salary_wages": round(gross_salary_wages, 2),
        "bonus": round(bonus, 2),
        "director_fees": 0.0,
        "commission": round(commission, 2),
        "overtime_pay": round(overtime_pay, 2),
        "pension_provident_fund": 0.0,
        # Allowances (Section B)
        "transport_allowance": round(transport_allowance, 2),
        "entertainment_allowance": round(entertainment_allowance, 2),
        "other_allowances": round(other_allowances, 2),
        "total_allowances": round(total_allowances, 2),
        # CPF (Section C)
        "employer_cpf": round(employer_cpf, 2),
        "employee_cpf": round(employee_cpf, 2),
        # Totals
        "total_gross_income": round(total_gross_income, 2),
        # Months of employment
        "months_paid": len(year_payslips),
    }


# ---------------------------------------------------------------------------
# IR21 for departing foreign employees
# ---------------------------------------------------------------------------


def generate_ir21_data(
    employee: dict,
    payslips: list[dict],
    items: list[dict],
    cessation_date: str,
) -> dict:
    """Generate IR21 data for departing foreign employee.

    Similar to IR8A but for partial year + includes:
    - Last day of employment
    - Reason for cessation
    - Outstanding salary/bonus
    - Whether monies have been withheld

    Returns dict matching IR21 form fields.
    """
    # Determine the tax year from cessation date
    try:
        cess_date = date.fromisoformat(cessation_date)
        tax_year = cess_date.year
    except (ValueError, TypeError):
        tax_year = date.today().year

    # Generate base IR8A data first (same aggregation logic)
    ir8a = generate_ir8a_data(employee, payslips, items, tax_year)

    # Override period_to with cessation date
    ir8a["period_to"] = cessation_date

    # Calculate outstanding salary from last payslip to cessation
    year_payslips = [ps for ps in payslips if ps.get("period_start", "").startswith(str(tax_year))]
    last_period_end = ""
    if year_payslips:
        year_payslips_sorted = sorted(year_payslips, key=lambda p: p.get("period_end", ""))
        last_period_end = year_payslips_sorted[-1].get("period_end", "")

    # If cessation is after the last paid period, there may be outstanding salary
    outstanding_salary = 0.0
    if last_period_end and cessation_date > last_period_end:
        monthly = employee.get("salary_monthly", 0.0)
        try:
            last_end = date.fromisoformat(last_period_end)
            cess = date.fromisoformat(cessation_date)
            # Approximate outstanding days
            outstanding_days = (cess - last_end).days
            if outstanding_days > 0 and monthly > 0:
                daily_rate = monthly / 30.0
                outstanding_salary = round(daily_rate * outstanding_days, 2)
        except (ValueError, TypeError):
            pass

    return {
        **ir8a,
        "filing_type": "ir21",
        "cessation_date": cessation_date,
        "last_day_of_employment": cessation_date,
        "reason_for_cessation": employee.get("termination_reason", "resignation"),
        "outstanding_salary": outstanding_salary,
        "outstanding_bonus": 0.0,
        "monies_withheld": outstanding_salary > 0,
        "amount_withheld": outstanding_salary if outstanding_salary > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Payslip HTML generation (EA s88A compliant)
# ---------------------------------------------------------------------------


def generate_payslip_html(
    payslip: dict,
    items: list[dict],
    employee: dict,
    company: dict,
) -> str:
    """Generate HTML for a single payslip (EA s88A compliant).

    The HTML can be converted to PDF using a headless browser or weasyprint.

    Must include per EA s88A:
    1. Employer name
    2. Employee name and NRIC (masked)
    3. Date of payment
    4. Basic salary
    5. Period covered
    6. Allowances (itemised)
    7. Additional payments (OT, bonus, etc. with calculation basis)
    8. Deductions (itemised: CPF, SHG, loans)
    9. OT hours, rate, and pay (if applicable)
    10. Net salary
    11. Employer CPF (for reference)
    12. Mode of payment

    Returns HTML string with inline styles (for PDF rendering).
    """
    # Prepare data
    company_name = company.get("name", "Company")
    company_uen = company.get("uen", "")

    emp_name = _get_employee_display_name(employee)
    nric_masked = _mask_nric(employee.get("nric_fin", ""))
    emp_id_internal = employee.get("employee_id_internal", "")
    department = employee.get("department", "")
    designation = employee.get("designation", "")

    period_start = payslip.get("period_start", "")
    period_end = payslip.get("period_end", "")
    pay_date = _format_display_date(payslip.get("pay_date", period_end))

    basic_salary = payslip.get("basic_salary", 0.0)
    gross_salary = payslip.get("gross_salary", 0.0)
    net_salary = payslip.get("net_salary", 0.0)
    employer_cpf = payslip.get("employer_cpf", 0.0)
    employee_cpf = payslip.get("employee_cpf", 0.0)

    # Classify items into earnings and deductions
    earnings: list[dict] = []
    deductions: list[dict] = []
    employer_contributions: list[dict] = []

    for item in items:
        item_type = item.get("item_type", "")
        amount = item.get("amount", 0.0)

        if item_type in ("employer_cpf", "sdl", "fwl"):
            employer_contributions.append(item)
        elif amount < 0:
            deductions.append(item)
        else:
            earnings.append(item)

    # Build earnings rows HTML
    earnings_rows = ""
    for item in earnings:
        earnings_rows += _html_row(
            item.get("name", ""),
            item.get("amount", 0.0),
        )

    # Build deductions rows HTML
    deductions_rows = ""
    for item in deductions:
        deductions_rows += _html_row(
            item.get("name", ""),
            abs(item.get("amount", 0.0)),
        )

    # Build employer contributions rows
    employer_rows = ""
    for item in employer_contributions:
        employer_rows += _html_row(
            item.get("name", ""),
            abs(item.get("amount", 0.0)),
        )

    # Determine payment mode
    bank_name = employee.get("bank_name", "")
    bank_last4 = employee.get("bank_account_last4", "")
    if bank_name and bank_last4:
        payment_mode = f"Bank Transfer ({bank_name} ****{bank_last4})"
    elif bank_name:
        payment_mode = f"Bank Transfer ({bank_name})"
    else:
        payment_mode = "Bank Transfer"

    total_deductions = sum(abs(item.get("amount", 0.0)) for item in deductions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Payslip - {emp_name} - {period_start} to {period_end}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 12px;
    color: #1a1a1a;
    line-height: 1.5;
    padding: 24px;
    max-width: 800px;
    margin: 0 auto;
    background: #fff;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 2px solid #2c3e50;
    padding-bottom: 16px;
    margin-bottom: 20px;
  }}
  .company-name {{
    font-size: 18px;
    font-weight: 700;
    color: #2c3e50;
  }}
  .company-uen {{
    font-size: 11px;
    color: #666;
  }}
  .payslip-title {{
    font-size: 16px;
    font-weight: 700;
    color: #2c3e50;
    text-align: right;
  }}
  .payslip-period {{
    font-size: 11px;
    color: #666;
    text-align: right;
  }}
  .info-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 24px;
    margin-bottom: 20px;
    background: #f8f9fa;
    padding: 12px 16px;
    border-radius: 4px;
  }}
  .info-row {{
    display: flex;
    justify-content: space-between;
  }}
  .info-label {{
    font-weight: 600;
    color: #555;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}
  .info-value {{
    font-weight: 400;
    color: #1a1a1a;
  }}
  .section {{
    margin-bottom: 16px;
  }}
  .section-title {{
    font-size: 13px;
    font-weight: 700;
    color: #2c3e50;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  table td {{
    padding: 4px 8px;
    font-size: 12px;
  }}
  table td:last-child {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }}
  .total-row {{
    border-top: 1px solid #999;
    font-weight: 700;
  }}
  .net-row {{
    border-top: 2px solid #2c3e50;
    font-weight: 700;
    font-size: 14px;
    color: #2c3e50;
  }}
  .footer {{
    margin-top: 24px;
    padding-top: 12px;
    border-top: 1px solid #ddd;
    font-size: 10px;
    color: #888;
    text-align: center;
  }}
  .payment-info {{
    margin-top: 16px;
    background: #f0f7ff;
    padding: 10px 16px;
    border-radius: 4px;
    border-left: 3px solid #2c3e50;
  }}
  .payment-info .label {{
    font-weight: 600;
    font-size: 11px;
    color: #555;
  }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="company-name">{_html_escape(company_name)}</div>
    <div class="company-uen">{('UEN: ' + _html_escape(company_uen)) if company_uen else ''}</div>
  </div>
  <div>
    <div class="payslip-title">Payslip</div>
    <div class="payslip-period">For period {_format_display_date(period_start)} to {_format_display_date(period_end)}</div>
  </div>
</div>

<div class="info-grid">
  <div class="info-row">
    <span class="info-label">Employee Name</span>
    <span class="info-value">{_html_escape(emp_name)}</span>
  </div>
  <div class="info-row">
    <span class="info-label">NRIC/FIN</span>
    <span class="info-value">{_html_escape(nric_masked)}</span>
  </div>
  <div class="info-row">
    <span class="info-label">Employee ID</span>
    <span class="info-value">{_html_escape(emp_id_internal)}</span>
  </div>
  <div class="info-row">
    <span class="info-label">Date of Payment</span>
    <span class="info-value">{_html_escape(pay_date)}</span>
  </div>
  <div class="info-row">
    <span class="info-label">Department</span>
    <span class="info-value">{_html_escape(department)}</span>
  </div>
  <div class="info-row">
    <span class="info-label">Designation</span>
    <span class="info-value">{_html_escape(designation)}</span>
  </div>
</div>

<div class="section">
  <div class="section-title">Earnings</div>
  <table>
    {earnings_rows}
    <tr class="total-row">
      <td>Gross Salary</td>
      <td>${gross_salary:,.2f}</td>
    </tr>
  </table>
</div>

<div class="section">
  <div class="section-title">Deductions</div>
  <table>
    {deductions_rows}
    <tr class="total-row">
      <td>Total Deductions</td>
      <td>${total_deductions:,.2f}</td>
    </tr>
  </table>
</div>

<div class="section">
  <table>
    <tr class="net-row">
      <td>Net Salary</td>
      <td>${net_salary:,.2f}</td>
    </tr>
  </table>
</div>

<div class="section">
  <div class="section-title">Employer Contributions (for reference)</div>
  <table>
    {employer_rows}
  </table>
</div>

<div class="payment-info">
  <span class="label">Mode of Payment:</span> {_html_escape(payment_mode)}
</div>

<div class="footer">
  This is a computer-generated payslip. No signature is required.<br>
  Issued in compliance with Singapore Employment Act s88A.
</div>

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# Appendix 8A — Benefits in Kind (T169)
# ---------------------------------------------------------------------------


def generate_appendix_8a(
    employee: dict,
    payslips: list[dict],
    items: list[dict],
    tax_year: int,
) -> dict:
    """Generate Appendix 8A (Benefits in Kind) data for a single employee.

    Appendix 8A covers taxable non-cash benefits provided by the employer:
    - Section A: Housing/accommodation benefit
    - Section B: Car/transport benefit
    - Section C: Utilities & household expenses
    - Section D: Other benefits (education, club membership, etc.)

    For now, aggregates benefit-type payslip items into the standard Appendix 8A
    structure. Most values will be zero for companies that primarily pay cash
    compensation, but the structure is ready for future benefit tracking.

    Returns dict matching Appendix 8A form fields.
    """
    # Filter payslips to the tax year
    year_payslips = [ps for ps in payslips if ps.get("period_start", "").startswith(str(tax_year))]
    year_payslip_ids = {ps.get("id") for ps in year_payslips}

    # Filter items to only those belonging to the tax year payslips
    year_items = [item for item in items if item.get("payslip_id") in year_payslip_ids]

    # Aggregate benefit items by category
    housing_benefit = 0.0
    car_benefit = 0.0
    utilities_benefit = 0.0
    driver_benefit = 0.0
    club_membership = 0.0
    education_benefit = 0.0
    entertainment_benefit = 0.0
    insurance_benefit = 0.0
    interest_benefit = 0.0
    holiday_passage = 0.0
    other_benefits = 0.0

    for item in year_items:
        item_type = item.get("item_type", "")
        name_lower = item.get("name", "").lower()
        amount = abs(item.get("amount", 0.0))

        # Only process benefit-type items
        if item_type not in ("benefit", "benefit_in_kind", "allowance"):
            continue

        # Skip non-taxable items
        if not item.get("is_taxable", True):
            continue

        # Classify by name keywords into Appendix 8A categories
        if any(kw in name_lower for kw in ("housing", "accommodation", "rent", "lodging")):
            housing_benefit += amount
        elif any(kw in name_lower for kw in ("car", "vehicle", "motor", "parking")):
            car_benefit += amount
        elif any(kw in name_lower for kw in ("utility", "utilities", "household")):
            utilities_benefit += amount
        elif "driver" in name_lower:
            driver_benefit += amount
        elif any(kw in name_lower for kw in ("club", "membership")):
            club_membership += amount
        elif any(kw in name_lower for kw in ("education", "school", "tuition")):
            education_benefit += amount
        elif "entertainment" in name_lower:
            entertainment_benefit += amount
        elif any(kw in name_lower for kw in ("insurance", "medical")):
            insurance_benefit += amount
        elif any(kw in name_lower for kw in ("interest", "loan")):
            interest_benefit += amount
        elif any(kw in name_lower for kw in ("holiday", "passage", "travel")):
            holiday_passage += amount
        else:
            other_benefits += amount

    total_benefits = (
        housing_benefit
        + car_benefit
        + utilities_benefit
        + driver_benefit
        + club_membership
        + education_benefit
        + entertainment_benefit
        + insurance_benefit
        + interest_benefit
        + holiday_passage
        + other_benefits
    )

    # Employment period within the tax year
    emp_start = employee.get("start_date", "")
    emp_end = employee.get("end_date", "")
    period_from = f"{tax_year}-01-01"
    period_to = f"{tax_year}-12-31"

    if emp_start and emp_start > period_from:
        period_from = emp_start
    if emp_end and emp_end < period_to:
        period_to = emp_end

    return {
        "filing_type": "appendix_8a",
        "tax_year": tax_year,
        # Employee details
        "employee_name": _get_employee_display_name(employee),
        "nric_fin": employee.get("nric_fin", ""),
        "date_of_birth": employee.get("date_of_birth", ""),
        "designation": employee.get("designation", ""),
        # Employment period
        "period_from": period_from,
        "period_to": period_to,
        # Section A: Housing / Accommodation
        "housing_benefit": round(housing_benefit, 2),
        "furniture_fittings": 0.0,
        "hotel_accommodation": 0.0,
        # Section B: Motor Vehicle
        "car_benefit": round(car_benefit, 2),
        "driver_benefit": round(driver_benefit, 2),
        # Section C: Utilities & Household
        "utilities_benefit": round(utilities_benefit, 2),
        "domestic_helper": 0.0,
        "gardener": 0.0,
        # Section D: Other Benefits
        "club_membership": round(club_membership, 2),
        "education_benefit": round(education_benefit, 2),
        "entertainment_benefit": round(entertainment_benefit, 2),
        "insurance_benefit": round(insurance_benefit, 2),
        "interest_benefit": round(interest_benefit, 2),
        "holiday_passage": round(holiday_passage, 2),
        "other_benefits": round(other_benefits, 2),
        # Total
        "total_benefits_in_kind": round(total_benefits, 2),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_employee_display_name(employee: dict) -> str:
    """Get employee display name from user data embedded in the employee dict."""
    # The employee dict may have name directly or we need to fall back
    name = employee.get("name", "")
    if not name:
        name = employee.get("employee_name", "")
    if not name:
        # Build from user_name if available
        name = employee.get("user_name", "Employee")
    return name


def _mask_nric(nric: str) -> str:
    """Mask NRIC/FIN showing only first letter and last 4 characters.

    Example: S1234567D -> S****567D
    """
    if not nric or len(nric) < 5:
        return nric
    return nric[0] + "*" * (len(nric) - 5) + nric[-4:]


def _format_display_date(date_str: str) -> str:
    """Format ISO date string to display format (DD MMM YYYY)."""
    if not date_str:
        return ""
    try:
        d = date.fromisoformat(date_str[:10])
        return d.strftime("%d %b %Y")
    except (ValueError, TypeError):
        return date_str


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _html_row(label: str, amount: float) -> str:
    """Generate a table row for the payslip."""
    return (
        f"    <tr>\n"
        f"      <td>{_html_escape(label)}</td>\n"
        f"      <td>${amount:,.2f}</td>\n"
        f"    </tr>\n"
    )
