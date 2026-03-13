"""Compliance Health Check — pure deterministic function.

Evaluates a company's compliance posture against Singapore employment
regulations and returns findings with severity, recommendations,
and an overall compliance score.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ComplianceFinding:
    domain: str
    issue: str
    severity: str  # "critical" | "high" | "medium" | "low"
    recommendation: str
    provision_id: str
    deadline: str


@dataclass(frozen=True)
class ComplianceCheckInput:
    company_size: int
    has_foreign_workers: bool
    sector: str
    has_ket_issued: bool
    has_written_contracts: bool
    has_payslip_system: bool
    has_leave_records: bool
    has_ot_records: bool
    has_safety_policy: bool
    has_grievance_process: bool
    has_cpf_registered: bool = True
    has_fwa_policy: bool = False


@dataclass(frozen=True)
class InspectionItem:
    category: str
    item: str
    status: str  # "pass" | "fail" | "unknown"
    provision: str


@dataclass(frozen=True)
class ComplianceCheckResult:
    score: int
    risk_tier: str
    findings: list[ComplianceFinding]
    action_items: list[str]
    domains_checked: list[str]
    explanation: str
    inspection_readiness: list[InspectionItem] = field(default_factory=list)


_SEVERITY_DEDUCTIONS = {
    "critical": 20,
    "high": 10,
    "medium": 5,
    "low": 2,
}


def check_compliance(inp: ComplianceCheckInput) -> ComplianceCheckResult:
    """Run a compliance health check and return findings with score."""
    findings: list[ComplianceFinding] = []
    action_items: list[str] = []

    # KET compliance (EA s95A)
    if not inp.has_ket_issued:
        findings.append(
            ComplianceFinding(
                domain="Employment Act",
                issue="Key Employment Terms (KET) not issued to employees",
                severity="critical",
                recommendation="Issue KET to all employees within 14 days of employment start. Fine up to $5,000 per offence.",
                provision_id="EA-S95-KETs",
                deadline="Immediate",
            )
        )
        action_items.append("Issue KET documents to all current employees")

    # Written contracts
    if not inp.has_written_contracts:
        findings.append(
            ComplianceFinding(
                domain="Employment Act",
                issue="No written employment contracts in place",
                severity="high",
                recommendation="Provide written contracts to all employees. While not strictly required for all, it is best practice and required for employees earning ≤$4,500.",
                provision_id="EA-KET",
                deadline="Within 30 days",
            )
        )
        action_items.append("Prepare and issue written employment contracts")

    # Payslip compliance (EA s88A)
    if not inp.has_payslip_system:
        findings.append(
            ComplianceFinding(
                domain="Employment Act",
                issue="No itemised payslip system in place",
                severity="critical",
                recommendation="Implement itemised payslips for every salary payment. Fine up to $5,000 per offence (EA s88A).",
                provision_id="EA-S88A-payslip",
                deadline="Immediate",
            )
        )
        action_items.append("Set up itemised payslip system")

    # Leave records (EA Part XII)
    if not inp.has_leave_records:
        findings.append(
            ComplianceFinding(
                domain="Employment Act",
                issue="No leave records maintained",
                severity="high",
                recommendation="Maintain accurate leave records for all employees. Required for MOM inspections.",
                provision_id="EA-PART-X-annual-leave",
                deadline="Within 14 days",
            )
        )
        action_items.append("Set up leave tracking system")

    # OT records (EA Part IV)
    if not inp.has_ot_records:
        findings.append(
            ComplianceFinding(
                domain="Employment Act",
                issue="No overtime records maintained",
                severity="high",
                recommendation="Maintain OT records for all Part IV eligible employees (workmen and non-workmen earning ≤$2,600).",
                provision_id="EA-PART-IV-hours",
                deadline="Within 14 days",
            )
        )
        action_items.append("Set up overtime tracking for Part IV employees")

    # Safety policy (WSH Act)
    if not inp.has_safety_policy and (inp.has_foreign_workers or inp.company_size >= 10):
        findings.append(
            ComplianceFinding(
                domain="Workplace Safety & Health",
                issue="No workplace safety and health policy in place",
                severity="high",
                recommendation="Develop and implement a WSH policy. Required for companies with 10+ employees or foreign workers.",
                provision_id="WSHA-S12",
                deadline="Within 30 days",
            )
        )
        action_items.append("Develop workplace safety and health policy")

    # Grievance process (TGFEP)
    if not inp.has_grievance_process:
        findings.append(
            ComplianceFinding(
                domain="Fair Employment",
                issue="No formal grievance handling process",
                severity="medium",
                recommendation="Establish a grievance handling process as recommended by TGFEP. Protects against wrongful dismissal claims.",
                provision_id="TGFEP-GRIEVANCE",
                deadline="Within 60 days",
            )
        )
        action_items.append("Establish employee grievance handling process")

    # CPF registration
    if not inp.has_cpf_registered:
        findings.append(
            ComplianceFinding(
                domain="CPF",
                issue="Company not registered with CPF Board",
                severity="critical",
                recommendation="Register with CPF Board immediately. Late payment incurs 18% p.a. interest (CPF Act s52).",
                provision_id="CPFA-S52",
                deadline="Immediate",
            )
        )
        action_items.append("Register with CPF Board")

    # FWA policy (TG-FWAR effective Dec 2024)
    if not inp.has_fwa_policy:
        findings.append(
            ComplianceFinding(
                domain="Fair Employment",
                issue="No Flexible Work Arrangement (FWA) policy",
                severity="medium",
                recommendation="Implement FWA policy per TG-FWAR guidelines (effective 1 Dec 2024). Employers must respond to FWA requests within 2 months.",
                provision_id="TGFWAR-request-process",
                deadline="Within 60 days",
            )
        )
        action_items.append("Draft and implement FWA policy")

    # Foreign worker compliance
    if inp.has_foreign_workers:
        findings.append(
            ComplianceFinding(
                domain="Foreign Manpower",
                issue="Foreign workers employed — ensure all passes are valid and conditions are met",
                severity="low",
                recommendation="Regularly verify work pass validity, quota compliance, and levy payments. Non-compliance can result in pass revocation.",
                provision_id="EFMA-conditions",
                deadline="Ongoing",
            )
        )

    # Calculate score
    score = 100
    for f in findings:
        score -= _SEVERITY_DEDUCTIONS.get(f.severity, 0)
    score = max(0, score)

    if score >= 80:
        risk_tier = "green"
    elif score >= 50:
        risk_tier = "amber"
    else:
        risk_tier = "red"

    domains_checked = [
        "Employment Act",
        "CPF",
        "Workplace Safety & Health",
        "Fair Employment",
    ]
    if inp.has_foreign_workers:
        domains_checked.append("Foreign Manpower")

    critical_count = sum(1 for f in findings if f.severity == "critical")
    high_count = sum(1 for f in findings if f.severity == "high")

    explanation = (
        f"Compliance score: {score}/100 ({risk_tier.upper()}). "
        f"Found {len(findings)} issue{'s' if len(findings) != 1 else ''}: "
        f"{critical_count} critical, {high_count} high priority. "
        f"Checked {len(domains_checked)} regulatory domains."
    )

    # MOM inspection readiness
    inspection = _build_inspection_checklist(inp)

    return ComplianceCheckResult(
        score=score,
        risk_tier=risk_tier,
        findings=findings,
        action_items=action_items,
        domains_checked=domains_checked,
        explanation=explanation,
        inspection_readiness=inspection,
    )


def _build_inspection_checklist(inp: ComplianceCheckInput) -> list[InspectionItem]:
    """Build MOM inspection readiness checklist."""
    return [
        InspectionItem(
            category="Employment Records",
            item="Key Employment Terms issued to all employees",
            status="pass" if inp.has_ket_issued else "fail",
            provision="EA s95A",
        ),
        InspectionItem(
            category="Employment Records",
            item="Written employment contracts available",
            status="pass" if inp.has_written_contracts else "fail",
            provision="EA",
        ),
        InspectionItem(
            category="Salary Records",
            item="Itemised payslips issued every payment",
            status="pass" if inp.has_payslip_system else "fail",
            provision="EA s88A",
        ),
        InspectionItem(
            category="Salary Records",
            item="CPF contributions up to date",
            status="pass" if inp.has_cpf_registered else "fail",
            provision="CPF Act",
        ),
        InspectionItem(
            category="Leave & Hours",
            item="Leave records maintained",
            status="pass" if inp.has_leave_records else "fail",
            provision="EA Part XII",
        ),
        InspectionItem(
            category="Leave & Hours",
            item="Overtime records maintained",
            status="pass" if inp.has_ot_records else "fail",
            provision="EA Part IV",
        ),
        InspectionItem(
            category="Safety",
            item="Workplace safety and health policy",
            status=(
                "pass"
                if inp.has_safety_policy
                else ("fail" if inp.company_size >= 10 else "unknown")
            ),
            provision="WSH Act",
        ),
        InspectionItem(
            category="Fair Employment",
            item="Grievance handling process in place",
            status="pass" if inp.has_grievance_process else "unknown",
            provision="TGFEP",
        ),
        InspectionItem(
            category="Fair Employment",
            item="FWA policy implemented",
            status="pass" if inp.has_fwa_policy else "unknown",
            provision="TG-FWAR",
        ),
    ]
