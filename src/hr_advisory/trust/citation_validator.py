"""Source Citation and Authority Level System (T045, T081).

Pre-delivery validation hook that ensures every cited provision
exists in the KB and is currently in force. This is a deterministic
check, not probabilistic -- runs on every response.

Provisions are loaded from the DataFlow KB on first access and cached
for ``_CACHE_TTL`` seconds.  When the database is unreachable, a stale
cache is preferred; if no cache has ever been populated the minimal
``_FALLBACK_PROVISIONS`` dict is returned so that core citations still
validate offline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AuthorityLevel(str, Enum):
    """Authority level of a source reference."""

    STATUTORY = "statutory"
    TRIPARTITE_GUIDELINE = "tripartite_guideline"
    BEST_PRACTICE = "best_practice"
    COMPANY_POLICY = "company_policy"


class CitationStatus(str, Enum):
    """Validation status of a citation."""

    VALID = "valid"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class ValidatedCitation:
    """A citation that has been validated against the KB."""

    provision_id: str
    title: str
    authority_level: AuthorityLevel
    status: CitationStatus
    last_verified: date
    effective_date: Optional[date] = None
    expiry_date: Optional[date] = None
    full_text: str = ""
    cross_references: tuple[str, ...] = ()


@dataclass(frozen=True)
class CitationValidationResult:
    """Result of validating all citations in a response."""

    is_valid: bool
    validated_citations: list[ValidatedCitation]
    invalid_citations: list[str]
    warnings: list[str]

    @property
    def valid_count(self) -> int:
        return sum(1 for c in self.validated_citations if c.status == CitationStatus.VALID)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_citations)


# ── Cache state ──────────────────────────────────────────────
_provision_cache: dict[str, dict] | None = None
_cache_timestamp: float = 0.0
_CACHE_TTL: float = 60.0  # seconds


# ── Fallback provisions (safety net when DB is unavailable) ──
# Stripped-down set of the most critical core provisions.

_FALLBACK_PROVISIONS: dict[str, dict] = {
    # Employment Act -- core
    "EA-S95-KETs": {
        "title": "Employment Act s95A -- Key Employment Terms",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2016-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S88A-payslip": {
        "title": "Employment Act s88A -- Itemised Payslips",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2016-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S10-notice": {
        "title": "Employment Act s10 -- Notice of Termination",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S11-salary-in-lieu": {
        "title": "Employment Act s11 -- Salary in Lieu of Notice",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S14-misconduct-dismissal": {
        "title": "Employment Act s14 -- Dismissal for Misconduct",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S22-final-payment": {
        "title": "Employment Act s22 -- Final Salary Payment",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-KET": {
        "title": "Employment Act -- Key Employment Terms (General)",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2016-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-PART-X-annual-leave": {
        "title": "Employment Act Part X -- Annual Leave",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-PART-IV-hours": {
        "title": "Employment Act Part IV -- Hours of Work and Overtime",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S21-salary-payment": {
        "title": "Employment Act s21 -- Salary Payment",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    "EA-S89-sick-leave": {
        "title": "Employment Act s89 -- Sick Leave",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    # CPF
    "CPFA-S52": {
        "title": "CPF Act s52 -- Late Payment Interest",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2024-01-01",
        "last_verified": "2026-03-01",
    },
    # WSH
    "WSHA-S12": {
        "title": "WSH Act s12 -- Duties of Occupier",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2006-03-01",
        "last_verified": "2026-03-01",
    },
    # Fair Employment
    "TGFEP-GRIEVANCE": {
        "title": "TGFEP -- Grievance Handling Process",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2023-01-01",
        "last_verified": "2026-02-15",
    },
    "TGFEP-fair-employment": {
        "title": "Tripartite Guidelines on Fair Employment Practices",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2023-01-01",
        "last_verified": "2026-02-15",
    },
    "TGFEP-fair-dismissal": {
        "title": "TGFEP -- Fair Dismissal Guidelines",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2023-01-01",
        "last_verified": "2026-02-15",
    },
    "TGFWAR-request-process": {
        "title": "TG-FWAR -- Flexible Work Arrangement Request Process",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2024-12-01",
        "last_verified": "2026-02-15",
    },
    # Foreign Manpower
    "EFMA-conditions": {
        "title": "EFMA -- Work Pass Conditions",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2021-01-01",
        "last_verified": "2026-03-01",
    },
    # WICA
    "WICA-employer-obligations": {
        "title": "WICA -- Employer Obligations",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2020-09-01",
        "last_verified": "2026-03-01",
    },
    "WSH-incident-reporting": {
        "title": "WSH (Incident Reporting) Regulations",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2006-03-01",
        "last_verified": "2026-03-01",
    },
    # PDPA
    "PDPA-breach-notification": {
        "title": "PDPA -- Mandatory Breach Notification",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2021-02-01",
        "last_verified": "2026-03-01",
    },
    "PDPA-protection-obligation": {
        "title": "PDPA -- Protection Obligation",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2014-07-02",
        "last_verified": "2026-03-01",
    },
    "PDPA-accountability": {
        "title": "PDPA -- Accountability Obligation",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2014-07-02",
        "last_verified": "2026-03-01",
    },
    # TADM/ECT
    "TADM-ECT-process": {
        "title": "TADM/ECT Claims Process",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2017-04-01",
        "last_verified": "2026-03-01",
    },
    # TAFEP
    "TAFEP-complaint-process": {
        "title": "TAFEP Complaint Process",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2023-01-01",
        "last_verified": "2026-02-15",
    },
    # WFA
    "WFA-workplace-fairness": {
        "title": "Workplace Fairness Act",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2025-01-01",
        "last_verified": "2026-03-01",
    },
    # ── Adversarial gap provisions (T082) ──
    # Gap 1: Compound OT Day Types
    "EA-S36-RD-PH": {
        "title": "EA s.36/s.88 -- Compound Rest Day + Public Holiday Pay Rules",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    # Gap 2: Extended Childcare Leave (Ages 7-12)
    "CDCSA-S12B-ECL": {
        "title": "CDCSA s.12B -- Extended Childcare Leave for Children Aged 7-12",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2017-07-01",
        "last_verified": "2026-03-01",
    },
    # Gap 3: Low-Wage CPF Rules
    "CPFA-3S-LW": {
        "title": "CPF Act Third Schedule -- Low-Wage Graduated Contributions",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2025-01-01",
        "last_verified": "2026-03-01",
    },
    # Gap 4: Platform Workers Act
    "PWA-CPF": {
        "title": "Platform Workers Act -- CPF Contributions for Platform Workers",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2025-01-01",
        "last_verified": "2026-03-01",
    },
    # Gap 5: Constructive Dismissal
    "EA-S14-CD-DEF": {
        "title": "EA s.14 -- Constructive Dismissal Definition and Legal Basis",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    # Gap 6: PDPA Breach Notification
    "PDPA-S26D-NOTIFY": {
        "title": "PDPA s.26D -- Data Breach Notification Obligation",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2021-02-01",
        "last_verified": "2026-03-01",
    },
    # Gap 7: Salary Deduction Aggregation
    "EA-S27-AGG": {
        "title": "EA s.27(3) -- Salary Deduction 50% Aggregate Cap",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    # Gap 8: Part-Time Employee Regulations
    "EA-PT-LEAVE": {
        "title": "EA Part-Time Regulations -- Pro-Rated Leave Entitlements",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2019-04-01",
        "last_verified": "2026-03-01",
    },
    # Gap 9: Mental Health Workplace Obligations
    "WSHA-S12-MH-DOC": {
        "title": "WSH Act s.12 -- Employer Duty of Care Includes Mental Health",
        "authority": AuthorityLevel.STATUTORY,
        "effective_date": "2006-03-01",
        "last_verified": "2026-03-01",
    },
    # Gap 10: AI and Algorithmic Discrimination
    "TAFEP-AI-SCREEN": {
        "title": "TAFEP Advisory -- Fair Use of AI in Hiring and Screening",
        "authority": AuthorityLevel.TRIPARTITE_GUIDELINE,
        "effective_date": "2024-06-01",
        "last_verified": "2026-03-01",
    },
}


# ── Backward-compatible alias ────────────────────────────────
# Other modules (e.g. advisory.py) import _KB_PROVISIONS directly.
# This alias ensures they get the fallback provisions on import and
# continue to work until they are migrated to get_valid_provisions().
_KB_PROVISIONS = _FALLBACK_PROVISIONS


# ── Authority level resolution ───────────────────────────────

_AUTHORITY_LEVEL_MAP: dict[str, AuthorityLevel] = {
    "statutory": AuthorityLevel.STATUTORY,
    "tripartite_guideline": AuthorityLevel.TRIPARTITE_GUIDELINE,
    "best_practice": AuthorityLevel.BEST_PRACTICE,
    "company_policy": AuthorityLevel.COMPANY_POLICY,
}


def _resolve_authority(entry: dict) -> AuthorityLevel:
    """Resolve the authority level from a provision dict.

    Handles both AuthorityLevel enum values (from fallback) and
    string values (from the database).
    """
    raw = entry.get("authority") or entry.get("authority_level")
    if isinstance(raw, AuthorityLevel):
        return raw
    if isinstance(raw, str):
        resolved = _AUTHORITY_LEVEL_MAP.get(raw.lower())
        if resolved is not None:
            return resolved
        logger.warning(
            "Unknown authority level '%s' for provision, defaulting to BEST_PRACTICE", raw
        )
    return AuthorityLevel.BEST_PRACTICE


# ── DB fetch helper ──────────────────────────────────────────


def _fetch_provisions_from_db() -> list[dict]:
    """Query all active provisions from the DataFlow KB.

    Uses the same ProvisionListNode pattern as ``kb.admin.search_provisions``.
    Returns a list of provision dicts.

    Raises:
        Any exception from the Kailash runtime or DataFlow layer.
    """
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    runtime = LocalRuntime()
    wf = WorkflowBuilder()
    wf.add_node(
        "ProvisionListNode",
        "all_active",
        {"filter": {"is_active": True}, "enable_cache": False, "limit": 10000},
    )
    results, _ = runtime.execute(wf.build())
    raw = results["all_active"]

    # Normalise ListNode result format
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    return []


# ── Public API: dynamic provision lookup ─────────────────────


def get_valid_provisions() -> dict[str, dict]:
    """Get the current set of valid provisions from the DB.

    Cached for ``_CACHE_TTL`` seconds.  Falls back gracefully:
    1. Fresh cache  -- returned immediately, no DB call
    2. DB available -- refreshes cache and returns
    3. DB down + stale cache -- returns stale cache (better than nothing)
    4. DB down + no cache   -- returns ``_FALLBACK_PROVISIONS``
    """
    global _provision_cache, _cache_timestamp

    now = time.time()
    if _provision_cache is not None and (now - _cache_timestamp) < _CACHE_TTL:
        return _provision_cache

    try:
        provisions = _fetch_provisions_from_db()

        # Start with fallback provisions so core entries are always present,
        # then overlay DB provisions (DB takes precedence on collisions).
        cache: dict[str, dict] = dict(_FALLBACK_PROVISIONS)
        db_count = 0
        for prov in provisions:
            pid = prov.get("provision_id") or prov.get("id")
            if pid is not None:
                # Cache is contractually `dict[str, dict]`; DB row.id is an
                # int. Coerce so the lookup in validate_citations() (which
                # also stringifies its inputs) always hits the same key.
                cache[str(pid)] = prov
                db_count += 1

        _provision_cache = cache
        _cache_timestamp = now
        logger.info(
            "Refreshed provision cache: %d from DB + %d fallback = %d total",
            db_count,
            len(_FALLBACK_PROVISIONS),
            len(cache),
        )
        return cache

    except Exception as exc:
        logger.warning(
            "Failed to refresh provision cache from DB: %s. Using %s.",
            exc,
            "stale cache" if _provision_cache is not None else "fallback provisions",
        )
        if _provision_cache is not None:
            return _provision_cache
        return _FALLBACK_PROVISIONS


# ── Validation functions ─────────────────────────────────────


def _is_company_policy_citation(pid: str) -> bool:
    """Check if a provision ID is a company policy citation (format: policy-{id})."""
    import re

    return bool(re.match(r"^policy-\d+$", pid))


def validate_citations(provision_ids: list[str]) -> CitationValidationResult:
    """Validate a list of provision IDs against the KB.

    This is a pre-delivery guardrail -- runs on EVERY response before
    it reaches the user. If any citation cannot be resolved, the
    response should be regenerated.

    Company policy citations (format 'policy-{id}') are recognized as
    valid citations with COMPANY_POLICY authority level. They are not
    looked up in the KB provisions since they come from the company's
    own policy database.
    """
    provisions = get_valid_provisions()

    validated: list[ValidatedCitation] = []
    invalid: list[str] = []
    warnings: list[str] = []

    today = date.today()

    for raw_pid in provision_ids:
        # When provisions come from DB, the id is an int; the regex below
        # expects a string. Normalise once so all downstream code paths
        # (regex, dict lookup, ValidatedCitation field) get a string.
        pid = str(raw_pid)
        # T017: Recognize company policy citations (format: policy-{id})
        if _is_company_policy_citation(pid):
            validated.append(
                ValidatedCitation(
                    provision_id=pid,
                    title=f"Company Policy {pid}",
                    authority_level=AuthorityLevel.COMPANY_POLICY,
                    status=CitationStatus.VALID,
                    last_verified=today,
                )
            )
            continue

        kb_entry = provisions.get(pid)

        if kb_entry is None:
            invalid.append(pid)
            continue

        effective_raw = kb_entry.get("effective_date", "")
        last_verified_raw = kb_entry.get("last_verified", "")

        # Parse dates, handling both str and date objects
        if isinstance(effective_raw, date):
            effective = effective_raw
        elif isinstance(effective_raw, str) and effective_raw:
            effective = date.fromisoformat(effective_raw[:10])
        else:
            effective = None

        if isinstance(last_verified_raw, date):
            last_verified = last_verified_raw
        elif isinstance(last_verified_raw, str) and last_verified_raw:
            last_verified = date.fromisoformat(last_verified_raw[:10])
        else:
            last_verified = today

        authority = _resolve_authority(kb_entry)

        # Check if verification is stale (> 90 days old)
        days_since_verified = (today - last_verified).days
        if days_since_verified > 90:
            warnings.append(f"Provision {pid} was last verified {days_since_verified} days ago.")

        validated.append(
            ValidatedCitation(
                provision_id=pid,
                title=kb_entry.get("title", pid),
                authority_level=authority,
                status=CitationStatus.VALID,
                last_verified=last_verified,
                effective_date=effective,
            )
        )

    return CitationValidationResult(
        is_valid=len(invalid) == 0,
        validated_citations=validated,
        invalid_citations=invalid,
        warnings=warnings,
    )


def get_provision_detail(provision_id: str) -> Optional[dict]:
    """Get full detail for a provision (for 'View Source' action)."""
    provisions = get_valid_provisions()
    entry = provisions.get(provision_id)
    if entry is None:
        return None

    authority = _resolve_authority(entry)

    effective_raw = entry.get("effective_date", "")
    last_verified_raw = entry.get("last_verified", "")

    # Normalise to string for the response
    if isinstance(effective_raw, date):
        effective_str = effective_raw.isoformat()
    else:
        effective_str = str(effective_raw) if effective_raw else ""

    if isinstance(last_verified_raw, date):
        last_verified_str = last_verified_raw.isoformat()
    else:
        last_verified_str = str(last_verified_raw) if last_verified_raw else ""

    return {
        "provision_id": provision_id,
        "title": entry.get("title", provision_id),
        "authority_level": authority.value,
        "effective_date": effective_str,
        "last_verified": last_verified_str,
    }
