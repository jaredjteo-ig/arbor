"""aite-government MCP server — Singapore government API integrations.

Registers all government-related tools for the shadow agent:
- CPF monthly contribution submission (G01)
- IRAS AIS tax filings — IR8A, Appendix 8A, IR8S, IR21 (G02-G04)
- MOM OED occupational data submission (G05)
- MyInfo employee onboarding (G06)
- CorpPass authorization management (G07)
- ACRA UEN verification and business profiles (G10)

Each tool is wired with:
- CorpPass authentication (via auth/corppass.py)
- Idempotency ledger (prevents double-submission)
- Saga orchestrator (multi-step workflows)
- Circuit breakers (resilience against API failures)
- Tenant isolation (via base MCP server)
- Full audit logging
"""

from __future__ import annotations

import logging
from typing import Optional

from hr_advisory.mcp_servers.base import AiteMCPServer, TenantContext
from hr_advisory.mcp_servers.idempotency import (
    DuplicateSubmissionError,
    get_submission_ledger,
)
from hr_advisory.mcp_servers.saga import (
    SAGA_TEMPLATES,
    get_saga_orchestrator,
)

# Adapters
from hr_advisory.mcp_servers.adapters import cpf_apex, iras_ais, mom_oed, myinfo, acra

# Auth
from hr_advisory.mcp_servers.auth import corppass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Create the server instance
# ---------------------------------------------------------------------------

server = AiteMCPServer(
    name="aite-government",
    description=(
        "Singapore government API integrations: CPF submissions, "
        "IRAS tax filings, MOM occupational data, MyInfo onboarding, "
        "and ACRA company verification."
    ),
    version="1.0.0",
)


# ============================================================================
# G07: CorpPass Authorization Management
# ============================================================================


@server.tool(
    "gov_corppass_initiate",
    description=(
        "Start the CorpPass authorization process. Returns a URL the admin "
        "must visit to authenticate their company via Singpass for business. "
        "Required before any government submission (CPF, IRAS, MOM)."
    ),
)
async def gov_corppass_initiate(ctx: TenantContext, callback_url: str) -> dict:
    """Initiate CorpPass OAuth 2.1 authorization flow."""
    result = corppass.initiate_auth(
        tenant_id=ctx.company_id,
        callback_url=callback_url,
    )
    return {
        "status": "authorization_required",
        "authorization_url": result["authorization_url"],
        "instructions": (
            "Open the authorization URL to log in via CorpPass (Singpass for business). "
            "After authenticating, you will be redirected back to complete the connection."
        ),
        "expires_in": result["expires_in"],
    }


@server.tool(
    "gov_corppass_callback",
    description="Complete CorpPass authorization after admin authenticates. Called automatically by the redirect handler.",
)
async def gov_corppass_callback(ctx: TenantContext, auth_code: str, state: str) -> dict:
    """Handle CorpPass OAuth callback with authorization code."""
    return await corppass.handle_callback(auth_code=auth_code, state=state)


@server.tool(
    "gov_corppass_status",
    description="Check if the company has an active CorpPass connection for government submissions.",
)
async def gov_corppass_status(ctx: TenantContext) -> dict:
    """Check CorpPass connection status."""
    connected = corppass.is_connected(ctx.company_id)
    return {
        "connected": connected,
        "tenant_id": ctx.company_id,
        "message": (
            "CorpPass is connected. Government submissions are available."
            if connected
            else "CorpPass is not connected. Use gov_corppass_initiate to connect."
        ),
    }


@server.tool(
    "gov_corppass_disconnect",
    description="Disconnect CorpPass authorization. Revokes tokens and removes the connection.",
)
async def gov_corppass_disconnect(ctx: TenantContext) -> dict:
    """Revoke CorpPass tokens and disconnect."""
    return await corppass.revoke_token(ctx.company_id)


# ============================================================================
# G01: CPF Monthly Contributions
# ============================================================================


@server.tool(
    "gov_cpf_validate",
    description=(
        "Validate that payroll data is ready for CPF submission. "
        "Checks payroll status, employee NRIC/FIN, CPF amounts, and "
        "whether a submission already exists for the period."
    ),
)
async def gov_cpf_validate(
    ctx: TenantContext,
    period: str,
    payroll_run: dict,
    payslips: list,
    employees: list,
) -> dict:
    """Validate CPF data readiness."""
    return await cpf_apex.validate_cpf_data(
        tenant_id=ctx.company_id,
        period=period,
        payroll_run=payroll_run,
        payslips=payslips,
        employees=employees,
    )


@server.tool(
    "gov_cpf_generate",
    description=(
        "Generate CPF submission payload from payroll data. "
        "Creates the data package but does NOT submit. "
        "Returns a preview for human confirmation."
    ),
)
async def gov_cpf_generate(
    ctx: TenantContext,
    period: str,
    payroll_run: dict,
    payslips: list,
    employees: list,
) -> dict:
    """Generate CPF submission payload for preview."""
    return await cpf_apex.generate_submission(
        tenant_id=ctx.company_id,
        period=period,
        payroll_run=payroll_run,
        payslips=payslips,
        employees=employees,
    )


@server.tool(
    "gov_cpf_submit",
    description=(
        "Submit CPF contributions to CPF Board via APEX. "
        "REQUIRES HUMAN CONFIRMATION. This is an irreversible government filing. "
        "The payload must come from gov_cpf_generate."
    ),
    requires_confirmation=True,
)
async def gov_cpf_submit(
    ctx: TenantContext,
    period: str,
    payload: dict,
) -> dict:
    """Submit CPF contributions (requires confirmation)."""
    try:
        return await cpf_apex.submit(
            tenant_id=ctx.company_id,
            period=period,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {
            "status": "blocked",
            "reason": "duplicate_submission",
            "message": str(e),
            "existing_submission": {
                "id": e.existing.id,
                "status": e.existing.status.value,
                "external_ref": e.existing.external_reference_id,
            },
        }


@server.tool(
    "gov_cpf_status",
    description="Check the status of a CPF submission. Returns whether CPF Board has acknowledged the filing.",
)
async def gov_cpf_status(ctx: TenantContext, submission_id: str) -> dict:
    """Check CPF submission acknowledgement status."""
    return await cpf_apex.check_status(
        tenant_id=ctx.company_id,
        submission_id=submission_id,
    )


@server.tool(
    "gov_cpf_csv_fallback",
    description=(
        "Generate a CPF e-Submit CSV file for manual upload to the CPF portal. "
        "Use when APEX API submission is not available (e.g., before OSP registration)."
    ),
)
async def gov_cpf_csv_fallback(
    ctx: TenantContext,
    payroll_run: dict,
    payslips: list,
    employees: list,
) -> dict:
    """Generate CPF e-Submit CSV file as fallback."""
    return await cpf_apex.generate_csv_fallback(
        payroll_run=payroll_run,
        payslips=payslips,
        employees=employees,
    )


# ============================================================================
# G02: IRAS IR8A — Annual Employment Income
# ============================================================================


@server.tool(
    "gov_iras_ir8a_generate",
    description=(
        "Generate IR8A annual employment income data for all employees. "
        "Aggregates payroll data for the basis year into IRAS format. "
        "Returns payload for preview before submission."
    ),
)
async def gov_iras_ir8a_generate(
    ctx: TenantContext,
    year_of_assessment: int,
    company: dict,
    employees: list,
    payslips: list,
    items: list,
) -> dict:
    """Generate IR8A payload for preview."""
    return await iras_ais.generate_ir8a_payload(
        tenant_id=ctx.company_id,
        year_of_assessment=year_of_assessment,
        company=company,
        employees=employees,
        all_payslips=payslips,
        all_items=items,
    )


@server.tool(
    "gov_iras_ir8a_submit",
    description=(
        "Submit IR8A employment income records to IRAS via AIS-API 2.0. "
        "REQUIRES HUMAN CONFIRMATION. Irreversible annual tax filing."
    ),
    requires_confirmation=True,
)
async def gov_iras_ir8a_submit(
    ctx: TenantContext,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit IR8A to IRAS (requires confirmation)."""
    try:
        return await iras_ais.submit_ir8a(
            tenant_id=ctx.company_id,
            year_of_assessment=year_of_assessment,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {
            "status": "blocked",
            "reason": "duplicate_submission",
            "message": str(e),
        }


# ============================================================================
# G02 (cont): IRAS Appendix 8A — Benefits in Kind
# ============================================================================


@server.tool(
    "gov_iras_appendix8a_generate",
    description=(
        "Generate Appendix 8A data for benefits in kind reporting. "
        "Includes housing, car, and other non-monetary benefits."
    ),
)
async def gov_iras_appendix8a_generate(
    ctx: TenantContext,
    year_of_assessment: int,
    company: dict,
    employees: list,
    benefits_data: list,
) -> dict:
    """Generate Appendix 8A payload for preview."""
    return await iras_ais.generate_appendix_8a_payload(
        tenant_id=ctx.company_id,
        year_of_assessment=year_of_assessment,
        company=company,
        employees=employees,
        benefits_data=benefits_data,
    )


@server.tool(
    "gov_iras_appendix8a_submit",
    description="Submit Appendix 8A benefits in kind to IRAS. REQUIRES HUMAN CONFIRMATION.",
    requires_confirmation=True,
)
async def gov_iras_appendix8a_submit(
    ctx: TenantContext,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit Appendix 8A to IRAS (requires confirmation)."""
    try:
        return await iras_ais.submit_appendix_8a(
            tenant_id=ctx.company_id,
            year_of_assessment=year_of_assessment,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {"status": "blocked", "reason": "duplicate_submission", "message": str(e)}


# ============================================================================
# G04: IRAS IR8S — Excess/Voluntary CPF Contributions
# ============================================================================


@server.tool(
    "gov_iras_ir8s_generate",
    description=(
        "Generate IR8S data for excess or voluntary CPF contribution refunds. "
        "Filed when employees receive CPF refunds or employer makes voluntary contributions."
    ),
)
async def gov_iras_ir8s_generate(
    ctx: TenantContext,
    year_of_assessment: int,
    company: dict,
    employees: list,
    ir8s_data: list,
) -> dict:
    """Generate IR8S payload for preview."""
    return await iras_ais.generate_ir8s_payload(
        tenant_id=ctx.company_id,
        year_of_assessment=year_of_assessment,
        company=company,
        employees=employees,
        ir8s_data=ir8s_data,
    )


@server.tool(
    "gov_iras_ir8s_submit",
    description="Submit IR8S records to IRAS. REQUIRES HUMAN CONFIRMATION.",
    requires_confirmation=True,
)
async def gov_iras_ir8s_submit(
    ctx: TenantContext,
    year_of_assessment: int,
    payload: dict,
) -> dict:
    """Submit IR8S to IRAS (requires confirmation)."""
    try:
        return await iras_ais.submit_ir8s(
            tenant_id=ctx.company_id,
            year_of_assessment=year_of_assessment,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {"status": "blocked", "reason": "duplicate_submission", "message": str(e)}


# ============================================================================
# G03: IRAS IR21 — Departing Foreign Employees
# ============================================================================


@server.tool(
    "gov_iras_ir21_generate",
    description=(
        "Generate IR21 data for a departing foreign employee. "
        "Must be filed at least 1 month before the employee's last day. "
        "Includes income from employment start to cessation."
    ),
)
async def gov_iras_ir21_generate(
    ctx: TenantContext,
    employee: dict,
    payslips: list,
    items: list,
    cessation_date: str,
    company: dict,
) -> dict:
    """Generate IR21 payload for a departing foreign employee."""
    return await iras_ais.generate_ir21_payload(
        tenant_id=ctx.company_id,
        employee=employee,
        payslips=payslips,
        items=items,
        cessation_date=cessation_date,
        company=company,
    )


@server.tool(
    "gov_iras_ir21_submit",
    description=(
        "Submit IR21 for a departing foreign employee to IRAS. "
        "REQUIRES HUMAN CONFIRMATION. Employer must withhold all monies "
        "until IRAS issues tax clearance."
    ),
    requires_confirmation=True,
)
async def gov_iras_ir21_submit(
    ctx: TenantContext,
    employee_id: str,
    payload: dict,
) -> dict:
    """Submit IR21 to IRAS (requires confirmation)."""
    try:
        return await iras_ais.submit_ir21(
            tenant_id=ctx.company_id,
            employee_id=employee_id,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {"status": "blocked", "reason": "duplicate_submission", "message": str(e)}


# ============================================================================
# IRAS Filing Status (shared across all form types)
# ============================================================================


@server.tool(
    "gov_iras_filing_status",
    description="Check the acknowledgement status of any IRAS AIS filing (IR8A, Appendix 8A, IR8S, IR21).",
)
async def gov_iras_filing_status(ctx: TenantContext, submission_id: str) -> dict:
    """Check IRAS filing acknowledgement status."""
    return await iras_ais.check_filing_status(
        tenant_id=ctx.company_id,
        submission_id=submission_id,
    )


# ============================================================================
# G05: MOM OED — Occupational Employment Data
# ============================================================================


@server.tool(
    "gov_mom_oed_generate",
    description=(
        "Generate Occupational Employment Data (OED) from employee records. "
        "Auto-maps designations to SSOC codes and aggregates by nationality, "
        "employment type, and salary range."
    ),
)
async def gov_mom_oed_generate(
    ctx: TenantContext,
    company: dict,
    employees: list,
    reference_date: Optional[str] = None,
) -> dict:
    """Generate OED payload for preview."""
    return await mom_oed.generate_oed_data(
        tenant_id=ctx.company_id,
        company=company,
        employees=employees,
        reference_date=reference_date,
    )


@server.tool(
    "gov_mom_oed_submit",
    description=(
        "Submit Occupational Employment Data to MOM. "
        "REQUIRES HUMAN CONFIRMATION. Mandatory under the Statistics Act."
    ),
    requires_confirmation=True,
)
async def gov_mom_oed_submit(
    ctx: TenantContext,
    period: str,
    payload: dict,
) -> dict:
    """Submit OED to MOM (requires confirmation)."""
    try:
        return await mom_oed.submit_oed(
            tenant_id=ctx.company_id,
            period=period,
            payload=payload,
        )
    except DuplicateSubmissionError as e:
        return {"status": "blocked", "reason": "duplicate_submission", "message": str(e)}


@server.tool(
    "gov_mom_oed_status",
    description="Check the status of a MOM OED submission.",
)
async def gov_mom_oed_status(ctx: TenantContext, submission_id: str) -> dict:
    """Check MOM OED submission status."""
    return await mom_oed.check_status(
        tenant_id=ctx.company_id,
        submission_id=submission_id,
    )


# ============================================================================
# G06: MyInfo Employee Onboarding
# ============================================================================


@server.tool(
    "gov_myinfo_initiate",
    description=(
        "Start MyInfo consent flow for a new employee. "
        "Returns a Singpass authorization URL. The employee visits this URL, "
        "consents to sharing their data, and is redirected back. "
        "Auto-fills name, NRIC, DOB, address, race, and nationality."
    ),
)
async def gov_myinfo_initiate(
    ctx: TenantContext,
    callback_url: str,
    requested_attributes: Optional[list] = None,
) -> dict:
    """Initiate MyInfo consent flow via Singpass."""
    return await myinfo.initiate_consent(
        callback_url=callback_url,
        requested_attributes=requested_attributes,
    )


@server.tool(
    "gov_myinfo_callback",
    description="Complete MyInfo data retrieval after employee consents via Singpass.",
)
async def gov_myinfo_callback(
    ctx: TenantContext,
    auth_code: str,
    state: str = "",
) -> dict:
    """Handle MyInfo callback and retrieve person data."""
    if not state:
        return {
            "status": "error",
            "message": "State parameter is required for MyInfo CSRF protection",
        }
    # Exchange code for token
    token_data = await myinfo.handle_callback(auth_code=auth_code, state=state)

    # Fetch person data
    person_data = await myinfo.fetch_person_data(
        access_token=token_data["access_token"],
    )

    return {
        "status": "success",
        "mapped_fields": person_data["mapped_fields"],
        "verified": person_data["verified"],
        "instructions": (
            "Review the auto-populated fields and confirm to create the employee record. "
            "All fields are government-verified via MyInfo."
        ),
    }


@server.tool(
    "gov_myinfo_business",
    description=(
        "Retrieve company profile data from MyInfo Business. "
        "Auto-fills UEN, company name, SSIC codes, and directors "
        "during company onboarding."
    ),
)
async def gov_myinfo_business(ctx: TenantContext, access_token: str) -> dict:
    """Fetch company data from MyInfo Business."""
    return await myinfo.fetch_business_data(access_token=access_token)


# ============================================================================
# G10: ACRA — Company Verification
# ============================================================================


@server.tool(
    "gov_acra_verify_uen",
    description=(
        "Verify a Singapore UEN against the ACRA registry. "
        "Uses the free data.gov.sg dataset. Returns entity name, type, and status."
    ),
)
async def gov_acra_verify_uen(ctx: TenantContext, uen: str) -> dict:
    """Verify UEN against ACRA registry (free)."""
    return await acra.verify_uen(uen)


@server.tool(
    "gov_acra_business_profile",
    description=(
        "Get full business profile from ACRA. "
        "Includes directors, shareholders, capital, and SSIC codes. "
        "Costs S$5.50 per query (cached for 30 days)."
    ),
)
async def gov_acra_business_profile(ctx: TenantContext, uen: str) -> dict:
    """Fetch full ACRA business profile (paid, cached)."""
    return await acra.get_business_profile(
        tenant_id=ctx.company_id,
        uen=uen,
    )


@server.tool(
    "gov_acra_cost_summary",
    description="Get cost summary for ACRA API queries. Shows total queries and costs per tenant.",
)
async def gov_acra_cost_summary(ctx: TenantContext) -> dict:
    """Get ACRA query cost summary."""
    return acra.get_cost_summary(tenant_id=ctx.company_id)


# ============================================================================
# Saga-based multi-step workflows
# ============================================================================


@server.tool(
    "gov_submission_saga_start",
    description=(
        "Start a multi-step government submission workflow. "
        "Creates a saga that tracks progress through validate, generate, "
        "confirm, submit, and verify steps."
    ),
)
async def gov_submission_saga_start(
    ctx: TenantContext,
    saga_type: str,
    context: Optional[dict] = None,
) -> dict:
    """Start a submission saga (e.g., submit_cpf, file_ir8a)."""
    template = SAGA_TEMPLATES.get(saga_type)
    if template is None:
        available = list(SAGA_TEMPLATES.keys())
        return {
            "status": "error",
            "message": f"Unknown saga type: {saga_type}",
            "available_types": available,
        }

    orchestrator = get_saga_orchestrator()
    saga = orchestrator.start_saga(
        tenant_id=ctx.company_id,
        saga_type=saga_type,
        step_names=template,
        context=context,
    )

    return {
        "status": "started",
        "saga_id": saga.id,
        "saga_type": saga_type,
        "steps": [s.name for s in saga.steps],
        "total_steps": saga.total_steps,
    }


@server.tool(
    "gov_submission_saga_status",
    description="Check the status of a government submission saga. Shows current step, completed steps, and any errors.",
)
async def gov_submission_saga_status(ctx: TenantContext, saga_id: str) -> dict:
    """Check saga status."""
    orchestrator = get_saga_orchestrator()
    saga = orchestrator.get_saga(saga_id)
    if saga is None:
        return {"status": "error", "message": f"Unknown saga: {saga_id}"}
    if saga.tenant_id != ctx.company_id:
        return {"status": "error", "message": "Saga does not belong to this tenant"}
    return saga.to_dict()


# ============================================================================
# Submission ledger queries
# ============================================================================


@server.tool(
    "gov_submissions_list",
    description=(
        "List all government submissions for this company. "
        "Shows CPF, IRAS, and MOM submissions with their current status."
    ),
)
async def gov_submissions_list(
    ctx: TenantContext,
    submission_type: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """List submission records from the idempotency ledger."""
    from hr_advisory.mcp_servers.idempotency import SubmissionStatus, SubmissionType

    ledger = get_submission_ledger()

    # Parse optional filters
    stype = None
    if submission_type:
        try:
            stype = SubmissionType(submission_type)
        except ValueError:
            return {"status": "error", "message": f"Invalid submission type: {submission_type}"}

    sstatus = None
    if status:
        try:
            sstatus = SubmissionStatus(status)
        except ValueError:
            return {"status": "error", "message": f"Invalid status: {status}"}

    records = ledger.list_submissions(
        tenant_id=ctx.company_id,
        submission_type=stype,
        status=sstatus,
    )

    return {
        "submissions": [
            {
                "id": r.id,
                "type": r.submission_type.value,
                "period": r.period,
                "status": r.status.value,
                "external_reference": r.external_reference_id,
                "employee_count": r.employee_count,
                "amount": r.amount,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "error": r.error_detail,
            }
            for r in records
        ],
        "total": len(records),
    }


# ============================================================================
# Resources (read-only data)
# ============================================================================


@server.resource(
    "gov://connectors",
    name="Government Connectors",
    description="List of available government API connectors and their status.",
)
def gov_connectors_resource() -> dict:
    """List all government connectors."""
    return {
        "connectors": [
            {
                "id": "G01",
                "name": "CPF APEX Submission",
                "api": "CPF Board via APEX",
                "status": "active",
                "requires_corppass": True,
            },
            {
                "id": "G02",
                "name": "IRAS AIS IR8A",
                "api": "IRAS AIS-API 2.0 via APEX",
                "status": "active",
                "requires_corppass": True,
            },
            {
                "id": "G03",
                "name": "IRAS AIS IR21",
                "api": "IRAS AIS-API 2.0 via APEX",
                "status": "active",
                "requires_corppass": True,
            },
            {
                "id": "G04",
                "name": "IRAS AIS IR8S",
                "api": "IRAS AIS-API 2.0 via APEX",
                "status": "active",
                "requires_corppass": True,
            },
            {
                "id": "G05",
                "name": "MOM OED",
                "api": "MOM via APEX",
                "status": "active",
                "requires_corppass": True,
            },
            {
                "id": "G06",
                "name": "MyInfo Onboarding",
                "api": "MyInfo v5 (FAPI 2.0)",
                "status": "active",
                "requires_corppass": False,
            },
            {
                "id": "G10",
                "name": "ACRA UEN Verification",
                "api": "data.gov.sg + ACRA API",
                "status": "active",
                "requires_corppass": True,
            },
        ],
    }


# ---------------------------------------------------------------------------
# Server health
# ---------------------------------------------------------------------------


@server.resource(
    "gov://health",
    name="Government Server Health",
    description="Health status of the aite-government MCP server.",
)
def gov_health_resource() -> dict:
    """Government server health."""
    from hr_advisory.mcp_servers.resilience import CIRCUITS

    circuit_statuses = {}
    for name in ("cpf_board", "iras", "mom", "myinfo", "data_gov_sg", "acra"):
        circuit = CIRCUITS.get(name)
        if circuit:
            circuit_statuses[name] = {
                "state": circuit.state.value,
                "error_rate": round(circuit.error_rate, 3),
                "total_calls": circuit._total_calls,
            }

    return {
        **server.get_health(),
        "circuits": circuit_statuses,
        "corppass_configured": bool(corppass.APEX_CLIENT_ID),
        "myinfo_configured": bool(myinfo.MYINFO_CLIENT_ID),
    }


# ============================================================================
# G11: SkillsFuture SSG — Course Search and Grant Calculation
# ============================================================================


@server.tool(
    "gov_skillsfuture_search_courses",
    description=(
        "Search the SkillsFuture course catalog (SSG Developer Portal). "
        "Returns matching courses with fee, duration, provider, and funding eligibility. "
        "Supports filters by training provider, course type, and area of training."
    ),
)
async def gov_skillsfuture_search_courses(
    ctx: TenantContext,
    query: str,
    filters: Optional[dict] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Search SkillsFuture course catalog."""
    from hr_advisory.mcp_servers.adapters.skillsfuture import SkillsFutureAdapter

    adapter = SkillsFutureAdapter()
    return await adapter.search_courses(
        query=query,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@server.tool(
    "gov_skillsfuture_calculate_grant",
    description=(
        "Calculate estimated SkillsFuture training grant eligibility for an employee. "
        "Takes employee nationality and age plus course fee, returns estimated "
        "government subsidy (standard or Mid-Career Enhanced Subsidy for 40+), "
        "out-of-pocket cost, and SkillsFuture Credit eligibility."
    ),
)
async def gov_skillsfuture_calculate_grant(
    ctx: TenantContext,
    employee_data: dict,
    course_fee: float,
    course_id: Optional[str] = None,
) -> dict:
    """Calculate SkillsFuture training grant estimate."""
    from hr_advisory.mcp_servers.adapters.skillsfuture import SkillsFutureAdapter

    adapter = SkillsFutureAdapter()
    return adapter.calculate_grant(
        employee_data=employee_data,
        course_fee=course_fee,
        course_id=course_id,
    )


@server.tool(
    "gov_skillsfuture_course_details",
    description=(
        "Get detailed information about a specific SkillsFuture course. "
        "Returns full course description, content outline, entry requirements, "
        "certification, schedules, provider UEN, and nett fee after subsidy."
    ),
)
async def gov_skillsfuture_course_details(
    ctx: TenantContext,
    course_id: str,
) -> dict:
    """Get detailed course information from SSG."""
    from hr_advisory.mcp_servers.adapters.skillsfuture import SkillsFutureAdapter

    adapter = SkillsFutureAdapter()
    return await adapter.get_course_details(course_id=course_id)
