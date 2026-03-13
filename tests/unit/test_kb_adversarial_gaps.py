"""Unit tests for adversarial scenario gap provisions (T082).

Validates that all 10 identified gaps have sufficient provision coverage
with correct structure, required fields, valid domains, and no duplicates.
Does NOT run DB operations -- purely validates data structures.
"""

from __future__ import annotations

import pytest

from hr_advisory.kb.content.adversarial_gaps import get_provisions, KNOWN_DOMAINS


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def all_provisions() -> list[dict]:
    """Load all adversarial gap provisions once per module."""
    return get_provisions()


@pytest.fixture(scope="module")
def provision_ids(all_provisions: list[dict]) -> list[str]:
    """Extract all provision IDs (section field)."""
    return [p["section"] for p in all_provisions]


# ── Required fields ──────────────────────────────────────────

REQUIRED_FIELDS = {"section", "title", "formal_text", "domain_name", "authority_level"}
RECOMMENDED_FIELDS = {"plain_summary", "effective_date", "act_short_name"}
VALID_AUTHORITY_LEVELS = {
    "statute",
    "subsidiary",
    "tripartite_guideline",
    "advisory",
    "best_practice",
}


# ── Gap definitions ──────────────────────────────────────────

GAP_DEFINITIONS = {
    "gap_01_compound_ot": {
        "label": "Compound OT Day Types",
        "id_prefixes": ["EA-S36", "EA-S38"],
        "min_provisions": 3,
    },
    "gap_02_extended_childcare": {
        "label": "Extended Childcare Leave (Ages 7-12)",
        "id_prefixes": ["CDCSA-S12B"],
        "min_provisions": 3,
    },
    "gap_03_low_wage_cpf": {
        "label": "Low-Wage CPF Rules",
        "id_prefixes": ["CPFA-3S", "CPFA-AW"],
        "min_provisions": 3,
    },
    "gap_04_platform_workers": {
        "label": "Platform Workers Act",
        "id_prefixes": ["PWA-"],
        "min_provisions": 3,
    },
    "gap_05_constructive_dismissal": {
        "label": "Constructive Dismissal",
        "id_prefixes": ["EA-S14-CD"],
        "min_provisions": 3,
    },
    "gap_06_pdpa_breach": {
        "label": "PDPA Breach Notification",
        "id_prefixes": ["PDPA-S26D"],
        "min_provisions": 3,
    },
    "gap_07_salary_deduction": {
        "label": "Salary Deduction Aggregation",
        "id_prefixes": ["EA-S27"],
        "min_provisions": 3,
    },
    "gap_08_part_time": {
        "label": "Part-Time Employee Regulations",
        "id_prefixes": ["EA-PT-"],
        "min_provisions": 3,
    },
    "gap_09_mental_health": {
        "label": "Mental Health Workplace Obligations",
        "id_prefixes": ["WSHA-S12-MH", "TA-MH"],
        "min_provisions": 3,
    },
    "gap_10_ai_discrimination": {
        "label": "AI and Algorithmic Discrimination",
        "id_prefixes": ["TAFEP-AI", "FCF-AI"],
        "min_provisions": 3,
    },
}


# ── Test Class: Structure Validation ─────────────────────────


class TestProvisionStructure:
    """Validate that every provision has all required fields populated."""

    def test_all_provisions_have_required_fields(self, all_provisions: list[dict]) -> None:
        """Every provision must have section, title, formal_text, domain_name, authority_level."""
        for prov in all_provisions:
            missing = REQUIRED_FIELDS - set(prov.keys())
            assert (
                not missing
            ), f"Provision '{prov.get('section', 'UNKNOWN')}' is missing required fields: {missing}"

    def test_all_provisions_have_recommended_fields(self, all_provisions: list[dict]) -> None:
        """Every provision should have plain_summary, effective_date, act_short_name."""
        for prov in all_provisions:
            missing = RECOMMENDED_FIELDS - set(prov.keys())
            assert (
                not missing
            ), f"Provision '{prov.get('section', 'UNKNOWN')}' is missing recommended fields: {missing}"

    def test_required_fields_not_empty(self, all_provisions: list[dict]) -> None:
        """Required fields must not be empty strings or None."""
        for prov in all_provisions:
            for field in REQUIRED_FIELDS:
                value = prov.get(field)
                assert value is not None and value != "", (
                    f"Provision '{prov.get('section', 'UNKNOWN')}' has empty/None value for "
                    f"required field '{field}'"
                )

    def test_formal_text_is_substantive(self, all_provisions: list[dict]) -> None:
        """formal_text must be at least 50 characters (not a stub)."""
        for prov in all_provisions:
            formal_text = prov.get("formal_text", "")
            assert len(formal_text) >= 50, (
                f"Provision '{prov['section']}' has formal_text of only {len(formal_text)} chars. "
                f"Minimum is 50 characters to be substantive."
            )

    def test_plain_summary_is_substantive(self, all_provisions: list[dict]) -> None:
        """plain_summary must be at least 30 characters (not a stub)."""
        for prov in all_provisions:
            plain_summary = prov.get("plain_summary", "")
            assert len(plain_summary) >= 30, (
                f"Provision '{prov['section']}' has plain_summary of only {len(plain_summary)} chars. "
                f"Minimum is 30 characters to be substantive."
            )


# ── Test Class: Domain Validation ────────────────────────────


class TestDomainValidation:
    """Validate that all domain values match known domains."""

    def test_all_domains_are_known(self, all_provisions: list[dict]) -> None:
        """Every provision's domain_name must be in the KNOWN_DOMAINS set."""
        for prov in all_provisions:
            domain = prov.get("domain_name")
            assert domain in KNOWN_DOMAINS, (
                f"Provision '{prov['section']}' has unknown domain '{domain}'. "
                f"Known domains: {sorted(KNOWN_DOMAINS)}"
            )

    def test_known_domains_includes_existing(self) -> None:
        """KNOWN_DOMAINS should include the standard domains from existing bundles."""
        expected_core = {
            "Working Hours & Overtime",
            "Leave Entitlements",
            "Salary & Compensation",
            "Termination & Dismissal",
            "Family Leave",
            "Workplace Safety & Health",
            "Data Protection",
            "CPF Contribution Rates",
            "Fair Employment Practices",
        }
        for domain in expected_core:
            assert domain in KNOWN_DOMAINS, f"Core domain '{domain}' missing from KNOWN_DOMAINS"


# ── Test Class: Authority Level Validation ───────────────────


class TestAuthorityLevelValidation:
    """Validate authority_level values match the enum."""

    def test_all_authority_levels_valid(self, all_provisions: list[dict]) -> None:
        """Every provision's authority_level must be a valid enum value."""
        for prov in all_provisions:
            level = prov.get("authority_level")
            assert level in VALID_AUTHORITY_LEVELS, (
                f"Provision '{prov['section']}' has invalid authority_level '{level}'. "
                f"Valid levels: {sorted(VALID_AUTHORITY_LEVELS)}"
            )


# ── Test Class: Uniqueness ───────────────────────────────────


class TestProvisionUniqueness:
    """Validate no duplicate provision IDs exist."""

    def test_no_duplicate_provision_ids(self, provision_ids: list[str]) -> None:
        """All provision section IDs must be unique."""
        seen = set()
        duplicates = []
        for pid in provision_ids:
            if pid in seen:
                duplicates.append(pid)
            seen.add(pid)
        assert not duplicates, f"Duplicate provision IDs found: {duplicates}"

    def test_provision_ids_follow_naming_convention(self, provision_ids: list[str]) -> None:
        """Provision IDs should follow the ACT-SECTION pattern."""
        for pid in provision_ids:
            assert "-" in pid, (
                f"Provision ID '{pid}' does not follow the ACT-SECTION naming convention "
                f"(must contain at least one hyphen)"
            )


# ── Test Class: Gap Coverage ─────────────────────────────────


class TestGapCoverage:
    """Validate that each of the 10 gaps has sufficient provisions."""

    def test_total_provision_count(self, all_provisions: list[dict]) -> None:
        """There must be at least 30 total provisions (3 per gap minimum)."""
        assert len(all_provisions) >= 30, (
            f"Expected at least 30 provisions (3 per gap x 10 gaps), " f"got {len(all_provisions)}"
        )

    @pytest.mark.parametrize(
        "gap_key,gap_def",
        GAP_DEFINITIONS.items(),
        ids=[v["label"] for v in GAP_DEFINITIONS.values()],
    )
    def test_gap_has_minimum_provisions(
        self, gap_key: str, gap_def: dict, all_provisions: list[dict]
    ) -> None:
        """Each gap must have at least min_provisions provisions matching its ID prefixes."""
        matching = [
            p
            for p in all_provisions
            if any(p["section"].startswith(prefix) for prefix in gap_def["id_prefixes"])
        ]
        assert len(matching) >= gap_def["min_provisions"], (
            f"Gap '{gap_def['label']}' needs at least {gap_def['min_provisions']} provisions "
            f"with prefixes {gap_def['id_prefixes']}, but found only {len(matching)}: "
            f"{[m['section'] for m in matching]}"
        )

    def test_all_10_gaps_covered(self, all_provisions: list[dict]) -> None:
        """All 10 gaps must have at least one provision."""
        uncovered = []
        for gap_key, gap_def in GAP_DEFINITIONS.items():
            matching = [
                p
                for p in all_provisions
                if any(p["section"].startswith(prefix) for prefix in gap_def["id_prefixes"])
            ]
            if not matching:
                uncovered.append(gap_def["label"])
        assert not uncovered, f"The following gaps have no provisions: {uncovered}"


# ── Test Class: Bundle Format ────────────────────────────────


class TestBundleFormat:
    """Validate the bundle is compatible with KBContentPipeline.bulk_load()."""

    def test_get_provisions_returns_list(self) -> None:
        """get_provisions() must return a list."""
        provisions = get_provisions()
        assert isinstance(
            provisions, list
        ), f"get_provisions() returned {type(provisions).__name__}, expected list"

    def test_each_provision_is_dict(self, all_provisions: list[dict]) -> None:
        """Every item in the provisions list must be a dict."""
        for i, prov in enumerate(all_provisions):
            assert isinstance(
                prov, dict
            ), f"Provision at index {i} is {type(prov).__name__}, expected dict"

    def test_effective_dates_are_strings(self, all_provisions: list[dict]) -> None:
        """effective_date values must be ISO date strings (YYYY-MM-DD)."""
        import re

        iso_date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for prov in all_provisions:
            ed = prov.get("effective_date")
            if ed is not None:
                assert isinstance(ed, str) and iso_date_re.match(ed), (
                    f"Provision '{prov['section']}' has invalid effective_date '{ed}'. "
                    f"Expected ISO format YYYY-MM-DD string."
                )

    def test_act_short_names_are_known(self, all_provisions: list[dict]) -> None:
        """act_short_name values must reference known acts."""
        known_acts = {"EA", "CDCSA", "CPFA", "EFMA", "TGFEP", "PWA", "PDPA", "WSHA"}
        for prov in all_provisions:
            act = prov.get("act_short_name")
            if act is not None:
                assert act in known_acts, (
                    f"Provision '{prov['section']}' references unknown act '{act}'. "
                    f"Known acts: {sorted(known_acts)}"
                )


# ── Test Class: Citation Validator Integration ───────────────


class TestCitationValidatorFallbacks:
    """Validate that key provision IDs are included in citation validator fallbacks."""

    def test_fallback_provisions_include_gap_entries(self) -> None:
        """Key provision IDs from each gap should be in _FALLBACK_PROVISIONS."""
        from hr_advisory.trust.citation_validator import _FALLBACK_PROVISIONS

        # At minimum, one key provision per gap must be in the fallback
        expected_keys = [
            "EA-S36-RD-PH",  # Gap 1: Compound OT
            "CDCSA-S12B-ECL",  # Gap 2: Extended Childcare
            "CPFA-3S-LW",  # Gap 3: Low-Wage CPF
            "PWA-CPF",  # Gap 4: Platform Workers
            "EA-S14-CD-DEF",  # Gap 5: Constructive Dismissal
            "PDPA-S26D-NOTIFY",  # Gap 6: PDPA Breach
            "EA-S27-AGG",  # Gap 7: Salary Deduction
            "EA-PT-LEAVE",  # Gap 8: Part-Time
            "WSHA-S12-MH-DOC",  # Gap 9: Mental Health
            "TAFEP-AI-SCREEN",  # Gap 10: AI Discrimination
        ]
        missing = [k for k in expected_keys if k not in _FALLBACK_PROVISIONS]
        assert (
            not missing
        ), f"The following gap provision IDs are missing from _FALLBACK_PROVISIONS: {missing}"


# ── Test Class: Loader Function ──────────────────────────────


class TestLoaderFunction:
    """Validate the loader function interface."""

    def test_load_gaps_function_exists(self) -> None:
        """load_gaps() must be importable from the loader module."""
        from hr_advisory.kb.load_adversarial_gaps import load_gaps

        assert callable(load_gaps), "load_gaps must be callable"

    def test_load_gaps_accepts_pipeline_argument(self) -> None:
        """load_gaps() must accept a pipeline argument (for dependency injection)."""
        import inspect
        from hr_advisory.kb.load_adversarial_gaps import load_gaps

        sig = inspect.signature(load_gaps)
        params = list(sig.parameters.keys())
        assert len(params) >= 1, (
            f"load_gaps() must accept at least one parameter (pipeline), "
            f"but has parameters: {params}"
        )
