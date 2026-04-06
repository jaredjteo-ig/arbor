"""Nexus platform configuration for the HR Advisory API gateway.

Creates and configures the Nexus instance with:
- auto_discovery=False (required for DataFlow integration)
- CORS with explicit allowed headers (no wildcard)
- Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
- Rate limiting
- FastAPI routers for each endpoint domain
- Session management with company context
"""

import logging

from fastapi import Request, Response
from nexus import Nexus

from hr_advisory.api.routers import (
    admin_router,
    advisory_router,
    alerts_router,
    appraisals_router,
    approval_groups_router,
    attendance_router,
    auth_router,
    calculator_router,
    claims_router,
    clients_router,
    compliance_router,
    document_router,
    employees_router,
    emergency_router,
    help_router,
    integrations_router,
    inventory_router,
    kb_router,
    learning_router,
    leave_router,
    llm_config_router,
    user_llm_router,
    payroll_router,
    policies_router,
    profile_router,
    projects_router,
    qa_router,
    recruitment_router,
    reports_router,
    search_router,
    settings_router,
    shadow_router,
    shifts_router,
)
from hr_advisory.api.session import create_session_store
from hr_advisory.config.settings import Settings, get_settings
from hr_advisory.security.validation import SECURITY_HEADERS

logger = logging.getLogger(__name__)


def create_platform(settings: Settings | None = None) -> Nexus:
    """Create and configure the Nexus platform instance.

    Args:
        settings: Application settings. If None, loaded from environment.

    Returns:
        A fully configured Nexus instance ready to start.
    """
    if settings is None:
        settings = get_settings()

    # Import models so DataFlow has them registered before Nexus starts.
    # This side-effect import is intentional and required.
    import hr_advisory.models  # noqa: F401

    # --- Nexus instance ---
    # auto_discovery=False is CRITICAL for DataFlow integration (prevents blocking).
    # enable_durability=False because the DurableWorkflowServer deduplicator caches
    # GET responses (including /auth/me) by method+path WITHOUT considering the
    # Authorization header — serving User A's data to User B. This is a security
    # issue for any authenticated endpoint. Disable until per-route cache control
    # is available.
    app = Nexus(
        api_port=settings.api_port,
        auto_discovery=False,
        cors_origins=settings.cors_origins_list,
        cors_allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        cors_allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        cors_expose_headers=["Content-Disposition", "X-Request-ID"],
        cors_allow_credentials=True,
        rate_limit=100,
        enable_durability=False,
    )

    # --- Disable trailing-slash 307 redirects ---
    # FastAPI defaults to redirect_slashes=True, which causes 307 redirects
    # when a client requests /path/ but the route is defined as /path (or
    # vice versa). This breaks some API clients. Disable it so that routes
    # match exactly as defined.
    fast_api = app._gateway.app  # Access underlying FastAPI instance
    fast_api.router.redirect_slashes = False
    logger.info("Trailing-slash 307 redirects disabled")

    # --- Security headers middleware ---
    _add_security_headers_middleware(app)

    # --- Session store ---
    session_store = create_session_store(settings)
    app._session_store = session_store  # Attach for handler access
    logger.info(
        "Session store initialised (%s)",
        "redis" if settings.is_production else "in-memory",
    )

    # --- Register routers ---
    _register_routers(app)

    # --- Register handler-based workflows ---
    _register_handlers(app, session_store)

    logger.info("HR Advisory platform configured successfully")
    return app


def _add_security_headers_middleware(app: Nexus) -> None:
    """Add security headers to every HTTP response."""
    fast_api = app._gateway.app  # Access underlying FastAPI instance

    @fast_api.middleware("http")
    async def security_headers_middleware(request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    logger.info("Security headers middleware registered")


def _register_routers(app: Nexus) -> None:
    """Include all FastAPI routers under their respective prefixes.

    Nexus wraps a Starlette app. We access the underlying ASGI app to register
    FastAPI routers via a lightweight FastAPI sub-application mounted on the gateway.
    """
    from fastapi import FastAPI

    # Build a FastAPI sub-app to hold all routers, then mount it on Nexus.
    api = FastAPI(redirect_slashes=False)

    api.include_router(advisory_router, prefix="/advisory", tags=["Advisory"])
    api.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
    api.include_router(calculator_router, prefix="/calculator", tags=["Calculator"])
    api.include_router(clients_router, prefix="/clients", tags=["Clients"])
    api.include_router(compliance_router, prefix="/compliance", tags=["Compliance"])
    api.include_router(document_router, prefix="/document", tags=["Document"])
    api.include_router(employees_router, prefix="/employees", tags=["Employees"])
    api.include_router(emergency_router, prefix="/emergency", tags=["Emergency"])
    api.include_router(leave_router, prefix="/leave", tags=["Leave"])
    api.include_router(llm_config_router, prefix="/companies", tags=["LLM Config"])
    api.include_router(user_llm_router, prefix="/users", tags=["User LLM Config"])
    api.include_router(payroll_router, prefix="/payroll", tags=["Payroll"])
    api.include_router(policies_router, prefix="/policies", tags=["Policies"])
    api.include_router(help_router, prefix="/help", tags=["Help"])
    api.include_router(profile_router, prefix="/profile", tags=["Profile"])
    api.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])
    api.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    api.include_router(search_router, prefix="/search", tags=["Search"])
    api.include_router(learning_router, prefix="/learning", tags=["Learning Pipeline"])
    api.include_router(settings_router, prefix="/settings", tags=["Settings"])
    api.include_router(shadow_router, prefix="/shadow", tags=["Shadow Agent"])
    api.include_router(shifts_router, prefix="/shifts", tags=["Shifts"])
    api.include_router(claims_router, prefix="/claims", tags=["Claims"])
    api.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
    api.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
    api.include_router(appraisals_router, prefix="/appraisals", tags=["Appraisals"])
    api.include_router(approval_groups_router, prefix="/approval-groups", tags=["Approval Groups"])
    api.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
    api.include_router(projects_router, prefix="/projects", tags=["Projects"])
    api.include_router(recruitment_router, prefix="/recruitment", tags=["Recruitment"])
    api.include_router(reports_router, prefix="/reports", tags=["Reports"])
    api.include_router(admin_router)  # Admin router has its own /admin prefix
    api.include_router(qa_router)  # QA router has its own /admin/qa prefix

    # Mount the FastAPI sub-app on the Nexus gateway
    app._gateway.app.mount("", api)

    logger.info("All API routers registered (including MCP integrations)")


def _register_handlers(app: Nexus, session_store) -> None:
    """Register handler-based workflows for multi-channel access.

    These handlers are available via API, CLI, and MCP simultaneously.
    They wrap the router logic so that the same advisory functionality
    is accessible from any channel.

    Security note: These handlers are invoked outside FastAPI's dependency
    injection system, so Depends(get_current_user) is not available.
    CLI and MCP channels rely on their own authentication mechanisms
    (CLI SSO, MCP transport auth). The HTTP API routes (which use
    Depends(get_current_user)) are the primary web-facing interface.
    """

    @app.handler("advisory_query", description="Submit an HR advisory question")
    async def advisory_query_handler(
        query: str,
        company_id: int = 0,
        conversation_id: int = 0,
    ) -> dict:
        """Multi-channel handler for HR advisory queries.

        Applies the full safety chain: sanitisation, screening, domain
        detection, KB lookup, citation validation, and response generation.
        """
        from hr_advisory.api.routers.advisory import (
            _classify_risk_tier,
            _detect_domains,
            _generate_grounded_response,
            _lookup_provisions,
        )
        from hr_advisory.security.validation import sanitise_input
        from hr_advisory.trust.citation_validator import validate_citations
        from hr_advisory.workflows.guardrails import ScreeningResult, screen_query

        clean_query = sanitise_input(query)
        screening = screen_query(clean_query)

        if screening.result == ScreeningResult.BLOCK:
            return {
                "query": clean_query,
                "response": screening.reason,
                "risk_tier": "red",
                "confidence_score": 0.0,
                "blocked": True,
            }

        if screening.result == ScreeningResult.ESCALATE:
            return {
                "query": clean_query,
                "response": screening.reason,
                "risk_tier": "red",
                "confidence_score": 0.0,
                "escalated": True,
            }

        domains = _detect_domains(clean_query)
        provision_ids = _lookup_provisions(domains, query=clean_query)
        citation_result = validate_citations(provision_ids)
        provisions_cited = [
            {
                "provision_id": c.provision_id,
                "title": c.title,
                "authority_level": c.authority_level.value,
            }
            for c in citation_result.validated_citations
        ]

        confidence = 0.85 if citation_result.is_valid else 0.6
        risk_tier = _classify_risk_tier(domains, confidence)
        response_text = _generate_grounded_response(clean_query, domains, provisions_cited)

        return {
            "query": clean_query,
            "response": response_text,
            "provisions_cited": provisions_cited,
            "risk_tier": risk_tier,
            "confidence_score": confidence,
            "company_id": company_id or None,
            "conversation_id": conversation_id or None,
        }

    @app.handler("compliance_check", description="Run a compliance check")
    async def compliance_check_handler(
        company_id: int = 0,
        domains: str = "",
    ) -> dict:
        """Multi-channel handler for compliance checks.

        Evaluates KB provision coverage across requested regulatory domains.
        """
        from hr_advisory.api.routers.compliance import (
            CORE_DOMAINS,
            _classify_status,
            _risk_tier_from_status,
            search_provisions,
        )

        domain_list = (
            [d.strip() for d in domains.split(",") if d.strip()] if domains else list(CORE_DOMAINS)
        )

        domain_counts: dict[str, int] = {}
        findings: list[dict] = []
        for domain in domain_list:
            try:
                provisions = search_provisions(domain, limit=100)
            except Exception:
                provisions = []
            count = len(provisions)
            domain_counts[domain] = count
            findings.append(
                {
                    "domain": domain,
                    "status": "covered" if count > 0 else "missing",
                    "provisions_checked": count,
                }
            )

        status = _classify_status(domain_counts, domain_list)
        risk_tier = _risk_tier_from_status(status)

        return {
            "company_id": company_id or None,
            "domains_checked": domain_list,
            "status": status,
            "risk_tier": risk_tier,
            "findings": findings,
        }

    @app.handler("search_kb", description="Search the knowledge base")
    async def search_kb_handler(query: str, top_k: int = 10) -> dict:
        """Multi-channel handler for knowledge base search.

        Uses the semantic search logic with keyword-based relevance scoring.
        """
        from hr_advisory.api.routers.search import _execute_semantic_search

        return _execute_semantic_search(
            query=query,
            top_k=top_k,
            domain_id=None,
            threshold=0.5,
        )

    logger.info("Multi-channel handlers registered")
