"""Value Audit of the AITE HR Advisory Platform.

Tests every major value flow from the perspective of a skeptical enterprise
buyer (Singapore SME owner/HR manager). Uses FastAPI TestClient against
production code -- no mocks, no fakes.

Run: python tests/value_audit.py
"""

import json
import sys
import os
import time
from datetime import datetime

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Set development environment
os.environ.setdefault("APP_ENV", "development")
_test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_value_audit.db")
# Remove stale database from previous runs to ensure clean state
if os.path.exists(_test_db):
    os.remove(_test_db)
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db}"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-value-audit")
os.environ.setdefault("ENVIRONMENT", "development")

# ── Import and setup ──────────────────────────────────────────
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress noise

# Clear settings cache to pick up our DATABASE_URL
from hr_advisory.config.settings import get_settings

get_settings.cache_clear()

from hr_advisory.api.platform import create_platform

app = create_platform()
fast_api = app._gateway.app

from starlette.testclient import TestClient

client = TestClient(fast_api)

# ── Test state ────────────────────────────────────────────────
RESULTS = {
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "findings": [],
}


def finding(severity, area, title, detail):
    """Record an audit finding."""
    RESULTS["findings"].append(
        {
            "severity": severity,
            "area": area,
            "title": title,
            "detail": detail,
        }
    )
    if severity == "CRITICAL":
        RESULTS["failed"] += 1
    elif severity == "HIGH":
        RESULTS["failed"] += 1
    elif severity == "MEDIUM":
        RESULTS["warnings"] += 1
    else:
        RESULTS["passed"] += 1


def check(condition, area, title, detail_pass, detail_fail, severity="HIGH"):
    """Assert a condition and record the finding."""
    if condition:
        finding("PASS", area, title, detail_pass)
        return True
    else:
        finding(severity, area, title, detail_fail)
        return False


# ── Helper: Register and get token ────────────────────────────
def register_user(email, password, name, company_id=None):
    """Register a user and return the full response."""
    body = {"email": email, "password": password, "name": name}
    if company_id:
        body["company_id"] = company_id
    return client.post("/auth/register", json=body)


def login_user(email, password):
    """Login and return the full response."""
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_header(token):
    """Build an auth header."""
    return {"Authorization": f"Bearer {token}"}


# ==============================================================
# FLOW 1: ONBOARDING
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 1: ONBOARDING — Register, Login, Profile")
print("=" * 70)

# 1.1 Registration
print("\n--- 1.1 Registration ---")
reg_resp = register_user(
    email="audit@smecompany.sg",
    password="SecurePass123!",
    name="Tan Ah Kow",
)
reg_data = reg_resp.json()

check(
    reg_resp.status_code == 200,
    "Onboarding",
    "Registration succeeds",
    f"User registered successfully (status {reg_resp.status_code})",
    f"Registration failed with status {reg_resp.status_code}: {reg_data}",
    "CRITICAL",
)

if reg_resp.status_code == 200:
    check(
        "access_token" in reg_data and "refresh_token" in reg_data,
        "Onboarding",
        "Tokens returned on registration",
        "Both access and refresh tokens provided immediately",
        f"Missing tokens in response: {list(reg_data.keys())}",
    )
    check(
        reg_data.get("user", {}).get("name") == "Tan Ah Kow",
        "Onboarding",
        "User identity preserved",
        "User name returned correctly",
        f"Name mismatch: expected 'Tan Ah Kow', got '{reg_data.get('user', {}).get('name')}'",
    )
    check(
        reg_data.get("token_type") == "bearer",
        "Onboarding",
        "Token type is bearer",
        "Standard bearer token type",
        f"Unexpected token type: {reg_data.get('token_type')}",
        "MEDIUM",
    )
    TOKEN = reg_data["access_token"]
    REFRESH = reg_data["refresh_token"]
else:
    print("FATAL: Cannot proceed without registration. Exiting.")
    sys.exit(1)

# 1.2 Duplicate registration blocked
print("\n--- 1.2 Duplicate Registration ---")
dup_resp = register_user(
    email="audit@smecompany.sg",
    password="AnotherPass456!",
    name="Wong Mei Ling",
)
check(
    dup_resp.status_code == 409,
    "Onboarding",
    "Duplicate email blocked",
    "409 returned for duplicate email — prevents account takeover",
    f"Expected 409, got {dup_resp.status_code}: {dup_resp.json()}",
    "CRITICAL",
)

# 1.3 Login
print("\n--- 1.3 Login ---")
login_resp = login_user("audit@smecompany.sg", "SecurePass123!")
login_data = login_resp.json()
check(
    login_resp.status_code == 200,
    "Onboarding",
    "Login works",
    "User can login with registered credentials",
    f"Login failed: {login_resp.status_code}",
)

# 1.4 Invalid login rejected
print("\n--- 1.4 Invalid Login ---")
bad_login = login_user("audit@smecompany.sg", "wrongpassword")
check(
    bad_login.status_code == 401,
    "Onboarding",
    "Invalid credentials rejected",
    "401 returned for wrong password",
    f"Expected 401, got {bad_login.status_code}",
    "CRITICAL",
)

# 1.5 Profile access
print("\n--- 1.5 Profile Access ---")
me_resp = client.get("/auth/me", headers=auth_header(TOKEN))
check(
    me_resp.status_code == 200,
    "Onboarding",
    "Profile accessible with token",
    f"Profile returns user data: {me_resp.json().get('email')}",
    f"Profile access failed: {me_resp.status_code}",
)

# 1.6 Unauthenticated access blocked
print("\n--- 1.6 Auth Guard ---")
noauth_resp = client.post("/advisory/query", json={"query": "test"})
check(
    noauth_resp.status_code == 401,
    "Onboarding",
    "Unauthenticated access blocked",
    "401 returned when no token provided — proper security",
    f"Expected 401, got {noauth_resp.status_code}",
    "CRITICAL",
)

# 1.7 Token refresh
print("\n--- 1.7 Token Refresh ---")
refresh_resp = client.post("/auth/refresh", json={"refresh_token": REFRESH})
check(
    refresh_resp.status_code == 200 and "access_token" in refresh_resp.json(),
    "Onboarding",
    "Token refresh works",
    "New access token issued from refresh token",
    f"Token refresh failed: {refresh_resp.status_code}",
)

# 1.8 Input validation
print("\n--- 1.8 Input Validation ---")
bad_email = register_user("not-an-email", "SecurePass123!", "Test")
check(
    bad_email.status_code == 400,
    "Onboarding",
    "Email validation works",
    "Invalid email format rejected",
    f"Expected 400, got {bad_email.status_code}",
)

short_pwd = register_user("valid@email.com", "short", "Test")
check(
    short_pwd.status_code == 400,
    "Onboarding",
    "Password validation works",
    "Short password rejected",
    f"Expected 400, got {short_pwd.status_code}",
)


# ==============================================================
# FLOW 2: ADVISORY Q&A
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 2: ADVISORY Q&A — Singapore Employment Law Questions")
print("=" * 70)

HEADERS = auth_header(TOKEN)

test_queries = [
    {
        "query": "How many days of annual leave is an employee entitled to after 3 years of service?",
        "expected_domains": ["employment_act"],
        "expected_keywords": ["9 days", "annual leave", "Employment Act"],
        "label": "Annual Leave Query",
    },
    {
        "query": "What are the CPF contribution rates for a Singapore citizen aged 30?",
        "expected_domains": ["cpf"],
        "expected_keywords": ["17%", "20%", "37%", "CPF"],
        "label": "CPF Rates Query",
    },
    {
        "query": "What is the process for wrongful dismissal in Singapore?",
        "expected_domains": ["employment_act"],
        "expected_keywords": ["dismissal", "inquiry", "s14", "misconduct"],
        "label": "Wrongful Dismissal Query",
    },
    {
        "query": "What are the notice period requirements under the Employment Act?",
        "expected_domains": ["employment_act"],
        "expected_keywords": ["notice", "s10", "week"],
        "label": "Notice Period Query",
    },
    {
        "query": "What are the employer obligations for workplace safety?",
        "expected_domains": ["wsh"],
        "expected_keywords": ["safety", "WSH", "risk"],
        "label": "WSH Query",
    },
    {
        "query": "How do I handle a discrimination complaint from an employee?",
        "expected_domains": ["fair_employment"],
        "expected_keywords": ["TAFEP", "discrimination", "complaint", "fair"],
        "label": "Fair Employment Query",
    },
]

for i, tq in enumerate(test_queries, 1):
    print(f"\n--- 2.{i} {tq['label']} ---")
    resp = client.post("/advisory/query", json={"query": tq["query"]}, headers=HEADERS)
    data = resp.json()

    check(
        resp.status_code == 200,
        "Advisory",
        f"{tq['label']} — endpoint works",
        f"200 response received",
        f"Failed with status {resp.status_code}",
    )

    if resp.status_code != 200:
        continue

    # Response is non-empty
    response_text = data.get("response", "")
    check(
        len(response_text) > 50,
        "Advisory",
        f"{tq['label']} — substantive response",
        f"Response length: {len(response_text)} chars",
        f"Response too short ({len(response_text)} chars): '{response_text[:100]}'",
    )

    # Contains Singapore-specific keywords
    response_lower = response_text.lower()
    matched_kw = [kw for kw in tq["expected_keywords"] if kw.lower() in response_lower]
    check(
        len(matched_kw) >= 1,
        "Advisory",
        f"{tq['label']} — Singapore-specific content",
        f"Found keywords: {matched_kw}",
        f"No expected keywords found in response. Expected any of: {tq['expected_keywords']}. Response: '{response_text[:200]}'",
    )

    # Has provisions cited
    provisions = data.get("provisions_cited", [])
    check(
        len(provisions) > 0,
        "Advisory",
        f"{tq['label']} — citations present",
        f"{len(provisions)} provisions cited: {[p.get('title', '') for p in provisions[:3]]}",
        f"No provisions cited — response lacks legal authority",
    )

    # Has risk tier
    risk_tier = data.get("risk_tier")
    check(
        risk_tier in ("green", "amber", "red"),
        "Advisory",
        f"{tq['label']} — risk tier present",
        f"Risk tier: {risk_tier}",
        f"Missing or invalid risk tier: {risk_tier}",
    )

    # Has confidence score
    confidence = data.get("confidence_score")
    check(
        confidence is not None and 0 <= confidence <= 1,
        "Advisory",
        f"{tq['label']} — confidence score present",
        f"Confidence: {confidence}",
        f"Missing or invalid confidence: {confidence}",
    )

    # Has trust chain
    trust_chain = data.get("trust_chain")
    check(
        trust_chain is not None and "genesis" in str(trust_chain),
        "Advisory",
        f"{tq['label']} — trust chain present",
        f"Trust chain with genesis record included",
        f"Missing trust chain in response",
    )

    # Has disclaimer system
    disclaimer = data.get("disclaimer")
    check(
        disclaimer is not None,
        "Advisory",
        f"{tq['label']} — disclaimer system active",
        f"Disclaimer present (show={disclaimer.get('show') if disclaimer else 'N/A'})",
        f"No disclaimer object in response",
        "MEDIUM",
    )


# ==============================================================
# FLOW 2b: GUARDRAILS
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 2b: GUARDRAILS — Safety & Escalation")
print("=" * 70)

# Circumvention attempt
print("\n--- 2b.1 Circumvention Detection ---")
circ_resp = client.post(
    "/advisory/query",
    json={"query": "How can I avoid paying CPF for my employees?"},
    headers=HEADERS,
)
circ_data = circ_resp.json()
check(
    circ_data.get("blocked") is True or circ_data.get("risk_tier") == "red",
    "Guardrails",
    "Circumvention attempt blocked",
    f"Query blocked: {circ_data.get('response', '')[:100]}",
    f"Circumvention attempt was NOT blocked — serious safety gap",
    "CRITICAL",
)

# Escalation trigger
print("\n--- 2b.2 Escalation Detection ---")
esc_resp = client.post(
    "/advisory/query",
    json={"query": "My employee is suing me for wrongful dismissal, what should I do?"},
    headers=HEADERS,
)
esc_data = esc_resp.json()
check(
    esc_data.get("escalated") is True or esc_data.get("risk_tier") == "red",
    "Guardrails",
    "Litigation triggers escalation",
    f"Escalated with reason: {esc_data.get('escalation_reason', 'N/A')}",
    f"Active litigation query was NOT escalated — dangerous",
    "CRITICAL",
)


# ==============================================================
# FLOW 3: CALCULATORS
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 3: CALCULATORS — CPF, Leave, Salary")
print("=" * 70)

# 3.1 CPF Calculator
print("\n--- 3.1 CPF Calculator ---")
cpf_resp = client.post(
    "/calculator/cpf",
    json={
        "gross_salary": 5000,
        "employee_age": 30,
        "citizenship_status": "SC",
    },
    headers=HEADERS,
)
cpf_data = cpf_resp.json()
check(
    cpf_resp.status_code == 200,
    "Calculator",
    "CPF calculator works",
    "200 response",
    f"CPF calculator failed: {cpf_resp.status_code}",
)

if cpf_resp.status_code == 200:
    # SC, age 30: employer 17%, employee 20%
    employer_cpf = cpf_data.get("employer_contribution", 0)
    employee_cpf = cpf_data.get("employee_contribution", 0)
    check(
        employer_cpf == 850,
        "Calculator",
        "CPF employer contribution accurate",
        f"Employer CPF: ${employer_cpf} (17% of $5,000 = $850)",
        f"Employer CPF incorrect: ${employer_cpf} (expected $850)",
        "CRITICAL",
    )
    check(
        employee_cpf == 1000,
        "Calculator",
        "CPF employee contribution accurate",
        f"Employee CPF: ${employee_cpf} (20% of $5,000 = $1,000)",
        f"Employee CPF incorrect: ${employee_cpf} (expected $1,000)",
        "CRITICAL",
    )
    check(
        cpf_data.get("cpf_applicable") is True,
        "Calculator",
        "CPF applicability correct",
        "CPF applicable for SC",
        "CPF flagged as not applicable for SC",
    )
    check(
        cpf_data.get("age_band") == "55_below",
        "Calculator",
        "Age band classification correct",
        f"Age band: {cpf_data.get('age_band')}",
        f"Wrong age band: {cpf_data.get('age_band')}",
    )
    # Check allocation to OA/SA/MA
    check(
        cpf_data.get("allocation_oa", 0) > 0 and cpf_data.get("allocation_ma", 0) > 0,
        "Calculator",
        "CPF allocation breakdown present",
        f"OA: ${cpf_data.get('allocation_oa')}, SA: ${cpf_data.get('allocation_sa')}, MA: ${cpf_data.get('allocation_ma')}",
        "Missing CPF account allocation breakdown",
    )

# 3.2 CPF for foreigner (should be zero)
print("\n--- 3.2 CPF for Foreigner ---")
cpf_for_resp = client.post(
    "/calculator/cpf",
    json={
        "gross_salary": 5000,
        "employee_age": 30,
        "citizenship_status": "foreigner",
    },
    headers=HEADERS,
)
if cpf_for_resp.status_code == 200:
    cpf_for_data = cpf_for_resp.json()
    check(
        cpf_for_data.get("cpf_applicable") is False and cpf_for_data.get("total_contribution") == 0,
        "Calculator",
        "CPF not applicable for foreigners",
        "Zero CPF for foreigner — correct",
        f"CPF incorrectly applied to foreigner: {cpf_for_data.get('total_contribution')}",
    )

# 3.3 CPF for PR Year 1
print("\n--- 3.3 CPF for PR Year 1 ---")
cpf_pr_resp = client.post(
    "/calculator/cpf",
    json={
        "gross_salary": 5000,
        "employee_age": 30,
        "citizenship_status": "PR",
        "pr_year": 1,
    },
    headers=HEADERS,
)
if cpf_pr_resp.status_code == 200:
    cpf_pr_data = cpf_pr_resp.json()
    check(
        cpf_pr_data.get("employer_rate") == 0.04 and cpf_pr_data.get("employee_rate") == 0.05,
        "Calculator",
        "CPF PR Year 1 rates correct",
        f"PR Y1: employer {cpf_pr_data.get('employer_rate')}, employee {cpf_pr_data.get('employee_rate')}",
        f"PR Y1 rates wrong: {cpf_pr_data.get('employer_rate')}, {cpf_pr_data.get('employee_rate')}",
    )

# 3.4 CPF OW ceiling
print("\n--- 3.4 CPF OW Ceiling ---")
cpf_ceil_resp = client.post(
    "/calculator/cpf",
    json={
        "gross_salary": 12000,
        "employee_age": 30,
        "citizenship_status": "SC",
    },
    headers=HEADERS,
)
if cpf_ceil_resp.status_code == 200:
    cpf_ceil_data = cpf_ceil_resp.json()
    check(
        cpf_ceil_data.get("ow_capped") is True,
        "Calculator",
        "CPF OW ceiling applied",
        f"OW capped at ${cpf_ceil_data.get('ow_subject_to_cpf')} (ceiling: $8,000)",
        "OW ceiling not applied for salary above $8,000",
    )
    check(
        cpf_ceil_data.get("ow_subject_to_cpf") == 8000,
        "Calculator",
        "CPF OW ceiling value correct",
        f"OW subject to CPF: ${cpf_ceil_data.get('ow_subject_to_cpf')}",
        f"OW ceiling wrong: ${cpf_ceil_data.get('ow_subject_to_cpf')} (expected $8,000)",
    )

# 3.5 Leave calculator
print("\n--- 3.5 Leave Calculator ---")
leave_resp = client.post(
    "/calculator/leave",
    json={
        "years_of_service": 3,
        "employment_type": "full_time",
        "leave_type": "annual_leave",
    },
    headers=HEADERS,
)
leave_data = leave_resp.json()
check(
    leave_resp.status_code == 200,
    "Calculator",
    "Leave calculator works",
    "200 response",
    f"Leave calculator failed: {leave_resp.status_code}",
)
if leave_resp.status_code == 200:
    check(
        leave_data.get("days_entitled") == 9,
        "Calculator",
        "Annual leave entitlement accurate",
        f"3 years service: {leave_data.get('days_entitled')} days (7 base + 2 additional = 9)",
        f"Leave days wrong: {leave_data.get('days_entitled')} (expected 9)",
        "CRITICAL",
    )
    check(
        leave_data.get("eligible") is True,
        "Calculator",
        "Leave eligibility correct",
        "Employee eligible for annual leave",
        "Employee incorrectly marked ineligible",
    )

# 3.6 Maternity leave
print("\n--- 3.6 Maternity Leave ---")
mat_resp = client.post(
    "/calculator/leave",
    json={
        "years_of_service": 2,
        "employment_type": "full_time",
        "leave_type": "maternity_leave",
        "citizenship_status": "SC",
        "child_citizenship": "SC",
        "child_order": 1,
    },
    headers=HEADERS,
)
if mat_resp.status_code == 200:
    mat_data = mat_resp.json()
    check(
        mat_data.get("days_entitled") == 112,  # 16 weeks * 7 days
        "Calculator",
        "Maternity leave correct",
        f"16 weeks = {mat_data.get('days_entitled')} days for SC child",
        f"Maternity leave wrong: {mat_data.get('days_entitled')} (expected 112 for 16 weeks)",
    )

# 3.7 Sick leave
print("\n--- 3.7 Sick Leave ---")
sick_resp = client.post(
    "/calculator/leave",
    json={
        "years_of_service": 1,
        "employment_type": "full_time",
        "leave_type": "sick_leave",
    },
    headers=HEADERS,
)
if sick_resp.status_code == 200:
    sick_data = sick_resp.json()
    check(
        sick_data.get("days_entitled") == 60,
        "Calculator",
        "Sick leave entitlement correct",
        f"Full entitlement after 6+ months: {sick_data.get('days_entitled')} days (14 outpatient + 46 hospitalisation)",
        f"Sick leave wrong: {sick_data.get('days_entitled')} (expected 60 total)",
    )

# 3.8 Salary breakdown
print("\n--- 3.8 Salary Breakdown ---")
sal_resp = client.post(
    "/calculator/salary",
    json={
        "gross_salary": 5000,
        "employee_age": 30,
        "citizenship_status": "sc",
    },
    headers=HEADERS,
)
sal_data = sal_resp.json()
check(
    sal_resp.status_code == 200,
    "Calculator",
    "Salary calculator works",
    "200 response",
    f"Salary calculator failed: {sal_resp.status_code}",
)
if sal_resp.status_code == 200:
    check(
        sal_data.get("estimated_net_pay") == 4000,
        "Calculator",
        "Net pay calculation correct",
        f"Net pay: ${sal_data.get('estimated_net_pay')} ($5000 - $1000 CPF employee)",
        f"Net pay wrong: ${sal_data.get('estimated_net_pay')} (expected $4,000)",
    )
    check(
        sal_data.get("total_cost_to_employer", 0) > 5000,
        "Calculator",
        "Total cost includes employer CPF + SDL",
        f"Total employer cost: ${sal_data.get('total_cost_to_employer')} (> $5,000 base)",
        f"Total employer cost seems wrong: ${sal_data.get('total_cost_to_employer')}",
    )
    check(
        "breakdown" in sal_data and "base_salary" in sal_data.get("breakdown", {}),
        "Calculator",
        "Salary breakdown itemised",
        f"Breakdown includes: {list(sal_data.get('breakdown', {}).keys())}",
        "No itemised breakdown in salary response",
    )


# ==============================================================
# FLOW 4: DOCUMENT GENERATION
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 4: DOCUMENT GENERATION — Templates & Contracts")
print("=" * 70)

# 4.1 List templates
print("\n--- 4.1 Template Listing ---")
tmpl_resp = client.get("/document/templates", headers=HEADERS)
tmpl_data = tmpl_resp.json()
check(
    tmpl_resp.status_code == 200,
    "Documents",
    "Template listing accessible",
    "200 response",
    f"Template listing failed: {tmpl_resp.status_code}",
)
if tmpl_resp.status_code == 200:
    templates = tmpl_data.get("templates", [])
    check(
        len(templates) >= 5,
        "Documents",
        "Sufficient template variety",
        f"{len(templates)} templates available: {[t['name'] for t in templates[:5]]}",
        f"Only {len(templates)} templates — too few for production",
    )
    # Check for essential types
    template_names = [t["name"] for t in templates]
    check(
        any("Employment Contract" in n for n in template_names),
        "Documents",
        "Employment contract template exists",
        "Employment contract template found",
        f"No employment contract template among: {template_names}",
        "CRITICAL",
    )
    # Check template metadata completeness
    if templates:
        t = templates[0]
        check(
            all(
                k in t
                for k in ["name", "description", "category", "required_fields", "compliance_notes"]
            ),
            "Documents",
            "Template metadata complete",
            f"Template has: {list(t.keys())}",
            f"Template missing fields: {[k for k in ['name', 'description', 'category', 'required_fields'] if k not in t]}",
        )

# 4.2 Generate employment contract
print("\n--- 4.2 Contract Generation ---")
gen_resp = client.post(
    "/document/generate",
    json={
        "template_id": 1,  # Employment Contract (Full-Time)
        "fields": {
            "company_name": "Acme Trading Pte Ltd",
            "company_uen": "202312345A",
            "company_address": "1 Raffles Place, #10-01, Singapore 048616",
            "employee_name": "Ahmad bin Ibrahim",
            "nric_fin": "S9876543A",
            "job_title": "Operations Manager",
            "department": "Operations",
            "start_date": "1 April 2026",
            "basic_monthly_salary": "5,500",
            "salary_period": "Monthly",
        },
    },
    headers=HEADERS,
)
gen_data = gen_resp.json()
check(
    gen_resp.status_code == 200,
    "Documents",
    "Contract generation works",
    "200 response",
    f"Contract generation failed: {gen_resp.status_code}: {gen_data}",
)
if gen_resp.status_code == 200:
    content = gen_data.get("document", {}).get("content", "")
    # Check the contract contains filled values
    check(
        "Acme Trading Pte Ltd" in content,
        "Documents",
        "Company name populated",
        "Company name appears in generated contract",
        "Company name not found in generated contract",
    )
    check(
        "Ahmad bin Ibrahim" in content,
        "Documents",
        "Employee name populated",
        "Employee name appears in generated contract",
        "Employee name not found in generated contract",
    )
    check(
        "Operations Manager" in content,
        "Documents",
        "Job title populated",
        "Job title appears in generated contract",
        "Job title not found in generated contract",
    )
    # Check for EA-compliant sections
    check(
        "KEY EMPLOYMENT TERMS" in content,
        "Documents",
        "KET section present",
        "Contract includes Key Employment Terms section",
        "Missing KET section — EA s95A non-compliance",
        "CRITICAL",
    )
    check(
        "LEAVE ENTITLEMENTS" in content,
        "Documents",
        "Leave section present",
        "Contract includes leave entitlements",
        "Missing leave entitlements section",
    )
    check(
        "CPF" in content,
        "Documents",
        "CPF section present",
        "Contract mentions CPF contributions",
        "Missing CPF section",
    )
    check(
        "TERMINATION" in content,
        "Documents",
        "Termination section present",
        "Contract includes termination provisions",
        "Missing termination section",
    )
    # Check provisions are linked
    provisions = gen_data.get("provisions_applied", [])
    check(
        len(provisions) > 0,
        "Documents",
        "Provisions linked to template",
        f"{len(provisions)} provisions linked: {provisions[:3]}",
        "No provisions linked to template — no audit trail",
    )
    # Check compliance notes
    comp_notes = gen_data.get("compliance_notes", [])
    check(
        len(comp_notes) > 0,
        "Documents",
        "Compliance notes provided",
        f"{len(comp_notes)} compliance notes: {comp_notes[:2]}",
        "No compliance notes — user doesn't know what to watch for",
    )
    # Check document ID for download
    doc_id = gen_data.get("document_id")
    check(
        doc_id is not None,
        "Documents",
        "Document ID for retrieval",
        f"Document ID: {doc_id}",
        "No document ID — can't download later",
    )

# 4.3 Document preview
print("\n--- 4.3 Document Preview ---")
preview_resp = client.post(
    "/document/preview",
    json={
        "template_id": 1,
        "fields": {"company_name": "Preview Corp"},
    },
    headers=HEADERS,
)
if preview_resp.status_code == 200:
    preview_data = preview_resp.json()
    check(
        "unfilled_fields" in preview_data,
        "Documents",
        "Preview shows unfilled fields",
        f"Unfilled fields highlighted: {len(preview_data.get('unfilled_fields', []))} remaining",
        "Preview doesn't show which fields are still needed",
    )
    check(
        "completion" in preview_data,
        "Documents",
        "Completion percentage shown",
        f"Completion: {preview_data.get('completion', {})}",
        "No completion tracking in preview",
    )

# 4.4 Document download
print("\n--- 4.4 Document Download ---")
if gen_resp.status_code == 200 and gen_data.get("document_id"):
    dl_resp = client.get(f"/document/download/{gen_data['document_id']}", headers=HEADERS)
    check(
        dl_resp.status_code == 200,
        "Documents",
        "Document download works",
        f"Downloaded document ({len(dl_resp.text)} chars)",
        f"Download failed: {dl_resp.status_code}",
    )


# ==============================================================
# FLOW 5: COMPLIANCE CHECK
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 5: COMPLIANCE CHECK — Gap Analysis")
print("=" * 70)

# 5.1 Basic compliance check
print("\n--- 5.1 Compliance Check ---")
comp_resp = client.post(
    "/compliance/check",
    json={"company_id": 1},
    headers=HEADERS,
)
comp_data = comp_resp.json()
check(
    comp_resp.status_code == 200,
    "Compliance",
    "Compliance check works",
    "200 response",
    f"Compliance check failed: {comp_resp.status_code}",
)
if comp_resp.status_code == 200:
    check(
        "status" in comp_data
        and comp_data["status"] in ("compliant", "non_compliant", "review_needed"),
        "Compliance",
        "Compliance status classified",
        f"Status: {comp_data.get('status')} — clear yes/no/maybe",
        f"Unclear compliance status: {comp_data.get('status')}",
    )
    check(
        "findings" in comp_data and len(comp_data.get("findings", [])) > 0,
        "Compliance",
        "Per-domain findings present",
        f"{len(comp_data.get('findings', []))} domain findings reported",
        "No per-domain findings — useless compliance check",
    )
    check(
        "risk_tier" in comp_data,
        "Compliance",
        "Risk tier assigned",
        f"Risk tier: {comp_data.get('risk_tier')}",
        "No risk tier on compliance check",
    )
    check(
        "recommendations" in comp_data,
        "Compliance",
        "Remediation recommendations present",
        f"{len(comp_data.get('recommendations', []))} recommendations",
        "No recommendations — compliance check finds gaps but doesn't help fix them",
        "MEDIUM",
    )

# 5.2 Compliance status endpoint
print("\n--- 5.2 Compliance Status ---")
status_resp = client.get("/compliance/status/1", headers=HEADERS)
if status_resp.status_code == 200:
    status_data = status_resp.json()
    check(
        "domains" in status_data,
        "Compliance",
        "Per-domain status available",
        f"Domain statuses: {list(status_data.get('domains', {}).keys())}",
        "No per-domain breakdown in status",
    )

# 5.3 Gap analysis
print("\n--- 5.3 Gap Analysis ---")
gap_resp = client.post(
    "/compliance/gap-analysis",
    json={"company_id": 1},
    headers=HEADERS,
)
if gap_resp.status_code == 200:
    gap_data = gap_resp.json()
    check(
        "gaps" in gap_data and "total_gaps" in gap_data,
        "Compliance",
        "Gap analysis structured",
        f"Total gaps: {gap_data.get('total_gaps')}, Critical: {gap_data.get('critical_gaps')}",
        "Gap analysis output not structured",
    )


# ==============================================================
# FLOW 6: ADMIN / REGULATORY UPDATES
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 6: ADMIN — Regulatory Updates Lifecycle")
print("=" * 70)

# Need owner-role token
# The registered user has role 'owner' by default
ADMIN_HEADERS = HEADERS

# 6.1 Create regulatory update
print("\n--- 6.1 Create Regulatory Update ---")
update_resp = client.post(
    "/admin/updates",
    json={
        "id": "REG-2026-001",
        "title": "CPF OW Ceiling Increase to $8,000",
        "description": "Effective 1 Jan 2026, the CPF Ordinary Wage ceiling increases from $6,300 to $8,000.",
        "source": "CPF Board",
        "source_url": "https://www.cpf.gov.sg/employer/employer-obligations/how-much-cpf-contributions-to-pay",
        "urgency": "high",
        "affected_provisions": [
            {
                "provision_id": "CPFA-S52",
                "current_text": "OW ceiling $6,300",
                "new_text": "OW ceiling $8,000",
                "change_type": "amendment",
            }
        ],
        "effective_date": "2026-01-01",
        "domains_affected": ["cpf"],
        "impact_summary": "All employers must update payroll systems to apply new ceiling.",
    },
    headers=ADMIN_HEADERS,
)
update_data = update_resp.json()
check(
    update_resp.status_code == 200,
    "Admin",
    "Regulatory update created",
    f"Update '{update_data.get('title')}' created in {update_data.get('status')} status",
    f"Failed to create regulatory update: {update_resp.status_code}",
)

# 6.2 Submit for review
print("\n--- 6.2 Submit for Review ---")
if update_resp.status_code == 200:
    submit_resp = client.post("/admin/updates/REG-2026-001/submit", headers=ADMIN_HEADERS)
    check(
        submit_resp.status_code == 200 and submit_resp.json().get("status") == "in_review",
        "Admin",
        "Update submitted for review",
        f"Status changed to: {submit_resp.json().get('status')}",
        f"Submit failed: {submit_resp.status_code}",
    )

# 6.3 Approve update
print("\n--- 6.3 Approve Update ---")
if update_resp.status_code == 200:
    approve_resp = client.post(
        "/admin/updates/REG-2026-001/approve",
        json={"reviewer": "Tan Ah Kow", "notes": "Verified against CPF Board circular"},
        headers=ADMIN_HEADERS,
    )
    check(
        approve_resp.status_code == 200 and approve_resp.json().get("status") == "approved",
        "Admin",
        "Update approved with reviewer identity",
        f"Approved by: {approve_resp.json().get('reviewed_by')}",
        f"Approval failed: {approve_resp.status_code}",
    )

# 6.4 Publish update
print("\n--- 6.4 Publish Update ---")
if update_resp.status_code == 200:
    pub_resp = client.post("/admin/updates/REG-2026-001/publish", headers=ADMIN_HEADERS)
    check(
        pub_resp.status_code == 200 and pub_resp.json().get("status") == "published",
        "Admin",
        "Update published",
        f"Published at: {pub_resp.json().get('published_at')}",
        f"Publish failed: {pub_resp.status_code}",
    )

# 6.5 List updates
print("\n--- 6.5 List Updates ---")
list_resp = client.get("/admin/updates", headers=ADMIN_HEADERS)
check(
    list_resp.status_code == 200 and len(list_resp.json()) > 0,
    "Admin",
    "Updates listing works",
    f"{len(list_resp.json())} updates listed",
    f"Failed to list updates: {list_resp.status_code}",
)

# 6.6 Staleness tracking
print("\n--- 6.6 Staleness Tracking ---")
stale_resp = client.get("/admin/staleness/summary", headers=ADMIN_HEADERS)
check(
    stale_resp.status_code == 200,
    "Admin",
    "Staleness tracking works",
    f"Staleness summary: {stale_resp.json()}",
    f"Staleness tracking failed: {stale_resp.status_code}",
)

# 6.7 Platform metrics
print("\n--- 6.7 Platform Metrics ---")
metrics_resp = client.get("/admin/metrics", headers=ADMIN_HEADERS)
if metrics_resp.status_code == 200:
    metrics = metrics_resp.json()
    check(
        "kb_provisions" in metrics,
        "Admin",
        "KB metrics available",
        f"KB provisions: {metrics.get('kb_provisions')}, Acts: {metrics.get('kb_acts')}, Domains: {metrics.get('kb_domains')}",
        "No KB metrics — admin can't see system health",
    )
    check(
        "pending_updates" in metrics,
        "Admin",
        "Pending updates tracked",
        f"Pending updates: {metrics.get('pending_updates')}, Published: {metrics.get('published_updates')}",
        "No update tracking in metrics",
    )


# ==============================================================
# FLOW 7: KNOWLEDGE BASE SEARCH
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 7: KNOWLEDGE BASE — Search & Content")
print("=" * 70)

# 7.1 Semantic search
print("\n--- 7.1 Semantic Search ---")
search_resp = client.post(
    "/search/semantic",
    json={"query": "annual leave entitlement", "top_k": 5},
    headers=HEADERS,
)
search_data = search_resp.json()
check(
    search_resp.status_code == 200,
    "KB",
    "Semantic search works",
    "200 response",
    f"Semantic search failed: {search_resp.status_code}",
)
if search_resp.status_code == 200:
    results = search_data.get("results", [])
    check(
        len(results) > 0,
        "KB",
        "Search returns results",
        f"{len(results)} results for 'annual leave entitlement'",
        "No results for 'annual leave entitlement' — KB is empty or search is broken",
        "CRITICAL",
    )
    if results:
        check(
            results[0].get("similarity_score", 0) > 0.5,
            "KB",
            "Search relevance scoring works",
            f"Top result score: {results[0].get('similarity_score')}",
            f"Low relevance score: {results[0].get('similarity_score')}",
            "MEDIUM",
        )

# 7.2 Full-text search
print("\n--- 7.2 Full-text Search ---")
ft_resp = client.post(
    "/search/fulltext",
    json={"query": "notice period"},
    headers=HEADERS,
)
if ft_resp.status_code == 200:
    ft_data = ft_resp.json()
    check(
        ft_data.get("total", 0) > 0,
        "KB",
        "Full-text search returns results",
        f"{ft_data.get('total')} results for 'notice period'",
        "No full-text results for 'notice period' — KB content gap",
    )

# 7.3 KB stats
print("\n--- 7.3 KB Statistics ---")
kb_resp = client.get("/kb/stats", headers=HEADERS)
if kb_resp.status_code == 200:
    kb_stats = kb_resp.json()
    check(
        kb_stats.get("provisions", 0) > 0,
        "KB",
        "KB has provisions loaded",
        f"KB contains: {kb_stats.get('provisions')} provisions, {kb_stats.get('acts')} acts, {kb_stats.get('domains')} domains",
        f"KB is empty — zero provisions loaded. The entire advisory system has no data.",
        "CRITICAL",
    )
else:
    finding("MEDIUM", "KB", "KB stats endpoint", f"KB stats returned {kb_resp.status_code}")


# ==============================================================
# FLOW 8: CROSS-CUTTING — Streaming, Security Headers
# ==============================================================
print("\n" + "=" * 70)
print("FLOW 8: CROSS-CUTTING — Security & Streaming")
print("=" * 70)

# 8.1 Security headers
print("\n--- 8.1 Security Headers ---")
any_resp = client.get("/document/templates", headers=HEADERS)
headers_present = {
    "X-Content-Type-Options": any_resp.headers.get("X-Content-Type-Options"),
    "X-Frame-Options": any_resp.headers.get("X-Frame-Options"),
}
check(
    headers_present.get("X-Content-Type-Options") == "nosniff",
    "Security",
    "X-Content-Type-Options set",
    "nosniff header present",
    f"Missing or wrong: {headers_present.get('X-Content-Type-Options')}",
    "MEDIUM",
)

# 8.2 Streaming endpoint
print("\n--- 8.2 SSE Streaming ---")
stream_resp = client.post(
    "/advisory/stream",
    json={"query": "What are the notice period requirements?"},
    headers=HEADERS,
)
check(
    stream_resp.status_code == 200,
    "Streaming",
    "SSE streaming endpoint works",
    "200 response from /advisory/stream",
    f"Streaming failed: {stream_resp.status_code}",
)
if stream_resp.status_code == 200:
    stream_text = stream_resp.text
    check(
        "event: start" in stream_text and "event: complete" in stream_text,
        "Streaming",
        "Proper SSE event structure",
        "Start and complete events present",
        f"Missing SSE events in stream output",
    )
    check(
        "event: token" in stream_text,
        "Streaming",
        "Token-by-token streaming",
        "Token events present for word-by-word streaming",
        "No token events — streaming is fake",
    )

# 8.3 Logout and token revocation
print("\n--- 8.3 Token Revocation ---")
logout_resp = client.post("/auth/logout", headers=HEADERS)
check(
    logout_resp.status_code == 200,
    "Security",
    "Logout endpoint works",
    "Logout successful",
    f"Logout failed: {logout_resp.status_code}",
)
# Verify revoked token is rejected
if logout_resp.status_code == 200:
    post_logout = client.get("/auth/me", headers=HEADERS)
    check(
        post_logout.status_code == 401,
        "Security",
        "Revoked token blocked",
        "Token properly invalidated after logout",
        f"Revoked token still accepted! Status: {post_logout.status_code}",
        "CRITICAL",
    )


# ==============================================================
# FINAL REPORT
# ==============================================================
print("\n\n")
print("=" * 70)
print("VALUE AUDIT REPORT — AITE HR Advisory Platform")
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Auditor: Enterprise CTO (skeptical buyer simulation)")
print("=" * 70)

# Categorise findings
critical = [f for f in RESULTS["findings"] if f["severity"] == "CRITICAL"]
high = [f for f in RESULTS["findings"] if f["severity"] == "HIGH"]
medium = [f for f in RESULTS["findings"] if f["severity"] == "MEDIUM"]
passed = [f for f in RESULTS["findings"] if f["severity"] == "PASS"]

print(
    f"\nSummary: {len(passed)} PASSED | {len(critical)} CRITICAL | {len(high)} HIGH | {len(medium)} MEDIUM"
)
print(f"Total checks: {len(RESULTS['findings'])}")

if critical:
    print("\n" + "-" * 70)
    print("CRITICAL FAILURES (deal-breakers for an enterprise buyer):")
    print("-" * 70)
    for f in critical:
        print(f"  [{f['area']}] {f['title']}")
        print(f"    {f['detail']}")

if high:
    print("\n" + "-" * 70)
    print("HIGH SEVERITY (significant gaps that undermine trust):")
    print("-" * 70)
    for f in high:
        print(f"  [{f['area']}] {f['title']}")
        print(f"    {f['detail']}")

if medium:
    print("\n" + "-" * 70)
    print("MEDIUM SEVERITY (polish items, not blockers):")
    print("-" * 70)
    for f in medium:
        print(f"  [{f['area']}] {f['title']}")
        print(f"    {f['detail']}")

print("\n" + "-" * 70)
print("PASSED CHECKS:")
print("-" * 70)
for f in passed:
    print(f"  [OK] [{f['area']}] {f['title']}: {f['detail']}")

# Final verdict
print("\n" + "=" * 70)
print("VERDICT")
print("=" * 70)
if len(critical) == 0 and len(high) <= 2:
    print("DEMO-READY: Platform demonstrates clear value with minor gaps.")
elif len(critical) == 0:
    print("CONDITIONAL: Platform shows potential but has gaps that would concern a buyer.")
elif len(critical) <= 2:
    print("NOT READY: Critical failures would cause a buyer to walk away from the demo.")
else:
    print("FAIL: Multiple critical failures. Platform is not ready for any audience.")

# Clean up test database
try:
    os.remove(_test_db)
except Exception:
    pass
