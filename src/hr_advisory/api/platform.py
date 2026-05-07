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
    banking_router,
    attendance_router,
    auth_router,
    calculator_router,
    claims_router,
    company_router,
    compliance_router,
    document_router,
    employees_router,
    emergency_router,
    feature_flags_router,
    help_router,
    integrations_router,
    integrations_calendar_router,
    inventory_router,
    kb_router,
    onboarding_router,
    learning_router,
    leave_router,
    llm_config_router,
    user_llm_router,
    payroll_router,
    policies_router,
    profile_router,
    projects_router,
    push_router,
    qa_router,
    recruitment_router,
    reports_router,
    search_router,
    settings_router,
    shadow_router,
    exit_interviews_router,
    engagement_surveys_router,
    goals_router,
    recognition_router,
    shifts_router,
    strategy_router,
    training_router,
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

    # --- Health check endpoint ---
    _register_health_check(app)

    logger.info("HR Advisory platform configured successfully")
    return app


def _register_health_check(app: Nexus) -> None:
    """Register a public /health endpoint for load balancers and monitoring.

    Returns {"status": "ok"} with no authentication required.
    """
    fast_api = app._gateway.app

    @fast_api.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {"status": "ok"}

    logger.info("Health check endpoint registered at /health")


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
    api.include_router(banking_router, prefix="/banking", tags=["Banking"])
    api.include_router(calculator_router, prefix="/calculator", tags=["Calculator"])
    api.include_router(company_router, prefix="/company", tags=["Company"])
    api.include_router(compliance_router, prefix="/compliance", tags=["Compliance"])
    api.include_router(document_router, prefix="/document", tags=["Document"])
    api.include_router(employees_router, prefix="/employees", tags=["Employees"])
    api.include_router(emergency_router, prefix="/emergency", tags=["Emergency"])
    api.include_router(feature_flags_router, prefix="/companies", tags=["Feature Flags"])
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
    api.include_router(strategy_router, prefix="/strategy", tags=["Strategy"])
    api.include_router(training_router, prefix="/training", tags=["Training"])
    api.include_router(
        recognition_router, prefix="/recognition", tags=["Recognition"]
    )
    api.include_router(goals_router, prefix="/goals", tags=["Goals"])
    api.include_router(
        exit_interviews_router,
        prefix="/exit-interviews",
        tags=["Exit Interview"],
    )
    api.include_router(
        engagement_surveys_router,
        prefix="/engagement-surveys",
        tags=["Engagement Surveys"],
    )
    api.include_router(claims_router, prefix="/claims", tags=["Claims"])
    api.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
    # Round-13 H — disconnect-route shadowing fix.
    # The dedicated Google Calendar router (T-R055) MUST be registered BEFORE
    # the generic ``integrations`` router. FastAPI matches routes in
    # registration order, and the generic router defines a catch-all
    # ``POST /{provider}/disconnect`` that would otherwise shadow the dedicated
    # ``POST /integrations/google-calendar/disconnect`` — the dedicated handler
    # actually revokes tokens at Google and deletes the GoogleCalendarConnection
    # row, while the generic handler returns a fake-success response without
    # touching either. Re-ordering here is the structural fix; the generic
    # handler also carries a defence-in-depth 404 guard for ``google-calendar``.
    api.include_router(
        integrations_calendar_router,
        prefix="/integrations/google-calendar",
        tags=["Integrations - Google Calendar"],
    )
    api.include_router(integrations_router, prefix="/integrations", tags=["Integrations"])
    api.include_router(appraisals_router, prefix="/appraisals", tags=["Appraisals"])
    api.include_router(approval_groups_router, prefix="/approval-groups", tags=["Approval Groups"])
    api.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
    api.include_router(onboarding_router, prefix="/onboarding", tags=["Onboarding"])
    api.include_router(projects_router, prefix="/projects", tags=["Projects"])
    api.include_router(push_router, prefix="/push", tags=["Web Push"])
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

    Security note (round-13 CRIT-S1 — RESOLVED):
    These handlers are invoked outside FastAPI's dependency injection
    system, so ``Depends(get_current_user)`` is not available. We
    therefore CANNOT trust any tenant identifier the caller hands us.
    Earlier revisions accepted ``company_id: int = 0`` as a body parameter
    and passed it straight to ``AdvisoryEngine`` / ``search_provisions``,
    which let an unauthenticated CLI/MCP caller dump arbitrary companies'
    data. The parameters have been removed; these handlers now run in a
    tenant-LESS mode that exposes only the public KB. When a future
    CLI/MCP authentication mechanism is wired up, add a ``current_user``
    parameter that the channel pre-populates from a verified token, and
    derive ``company_id`` from there — never from caller-supplied input.
    The HTTP API routes (which use ``Depends(get_current_user)``) remain
    the primary web-facing interface and continue to enforce tenant
    isolation correctly.
    """

    @app.handler("advisory_query", description="Submit an HR advisory question")
    async def advisory_query_handler(query: str) -> dict:
        """Multi-channel handler for HR advisory queries (tenant-less).

        Runs the autonomous AdvisoryEngine (LLM function-calling) using
        ONLY the public KB — no company context. CLI and MCP channels
        cannot establish a trustworthy tenant identifier today, so we
        deliberately give up company-specific policy lookups rather than
        accept an unauthenticated tenant id. See module docstring above.
        """
        import asyncio

        from hr_advisory.agents.advisory_engine import AdvisoryEngine
        from hr_advisory.security.validation import sanitise_input
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

        engine = AdvisoryEngine()
        loop = asyncio.get_event_loop()
        engine_result = await loop.run_in_executor(
            None,
            lambda: engine.run(
                query=clean_query,
                conversation_history=[],
                company_id=None,  # tenant-less by design — see handler docstring
            ),
        )

        return {
            "query": clean_query,
            "response": engine_result.get("response_text", ""),
            "provisions_cited": engine_result.get("citations", []),
            "risk_tier": engine_result.get("risk_tier", "amber"),
            "confidence_score": engine_result.get("confidence", 0.7),
            "domains": engine_result.get("domains", []),
            "degraded": engine_result.get("degraded", False),
        }

    @app.handler("compliance_check", description="Run a compliance check")
    async def compliance_check_handler(domains: str = "") -> dict:
        """Multi-channel handler for compliance checks (tenant-less).

        Evaluates KB provision coverage across requested regulatory
        domains using only the public KB — no company context. See
        the module docstring above for why ``company_id`` is no longer
        accepted.
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
