"""Content validation for the regulatory knowledge base.

Validates content quality before loading and checks database integrity
after loading. All database queries use DataFlow workflow nodes.
"""

import logging
from typing import Optional

from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

from hr_advisory.models.enums import AuthorityLevel

logger = logging.getLogger(__name__)

# Fields that MUST be present for a valid provision
REQUIRED_PROVISION_FIELDS = [
    "section",
    "title",
    "formal_text",
    "authority_level",
    "domain_name",
]

# Fields that SHOULD be present (warnings if missing)
RECOMMENDED_PROVISION_FIELDS = [
    "plain_summary",
    "interpretation_notes",
    "effective_date",
]

# Valid authority_level values
VALID_AUTHORITY_LEVELS = {level.value for level in AuthorityLevel}


class KBContentValidator:
    """Validates knowledge base content quality and completeness."""

    def __init__(self):
        self._runtime = LocalRuntime()

    def _execute(self, node_type: str, node_id: str, params: dict) -> dict:
        """Run a single-node workflow and return the node result."""
        wf = WorkflowBuilder()
        wf.add_node(node_type, node_id, params)
        results, _ = self._runtime.execute(wf.build())
        return results[node_id]

    @staticmethod
    def _extract_records(result) -> list[dict]:
        """Extract the record list from a ListNode result.

        DataFlow ListNode returns either a plain list or
        ``{"records": [...], "count": N, ...}``.
        """
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "records" in result:
            return result["records"]
        return []

    # ------------------------------------------------------------------
    # Provision validation
    # ------------------------------------------------------------------

    def validate_provision(self, provision_data: dict) -> list[str]:
        """Validate a single provision's data before loading.

        Returns:
            List of validation error messages. Empty list means valid.
        """
        errors: list[str] = []

        for field in REQUIRED_PROVISION_FIELDS:
            value = provision_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"Required field '{field}' is missing or empty in provision data.")

        # Validate authority_level value
        authority = provision_data.get("authority_level")
        if authority and authority not in VALID_AUTHORITY_LEVELS:
            errors.append(
                f"Invalid authority_level '{authority}'. "
                f"Must be one of: {', '.join(sorted(VALID_AUTHORITY_LEVELS))}"
            )

        return errors

    def _get_provision_warnings(self, provision_data: dict) -> list[str]:
        """Check for missing recommended fields and return warnings."""
        warnings: list[str] = []
        for field in RECOMMENDED_PROVISION_FIELDS:
            value = provision_data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                warnings.append(
                    f"Recommended field '{field}' is missing in provision "
                    f"'{provision_data.get('section', 'unknown')}'. "
                    f"Consider adding it for better advisory quality."
                )
        return warnings

    # ------------------------------------------------------------------
    # Bundle validation
    # ------------------------------------------------------------------

    def validate_bundle(self, bundle: dict) -> dict:
        """Validate an entire content bundle before loading.

        Returns:
            Dict with ``errors`` (list of blocking errors) and
            ``warnings`` (list of non-blocking advisories).
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate act
        act_data = bundle.get("act")
        if not act_data:
            errors.append("Bundle must include an 'act' entry.")
        elif not act_data.get("short_name"):
            errors.append("Act must have a 'short_name'.")
        elif not act_data.get("title"):
            errors.append("Act must have a 'title'.")

        # Validate provisions
        for i, prov in enumerate(bundle.get("provisions", [])):
            prov_errors = self.validate_provision(prov)
            for err in prov_errors:
                errors.append(f"Provision [{i}] ({prov.get('section', 'unknown')}): {err}")

            prov_warnings = self._get_provision_warnings(prov)
            for warn in prov_warnings:
                warnings.append(f"Provision [{i}]: {warn}")

        # Validate domains
        for i, domain in enumerate(bundle.get("domains", [])):
            if not domain.get("name"):
                errors.append(f"Domain [{i}] must have a 'name'.")

        return {"errors": errors, "warnings": warnings}

    # ------------------------------------------------------------------
    # DB integrity checks
    # ------------------------------------------------------------------

    def validate_db_integrity(self) -> dict:
        """Check database integrity post-load.

        Returns a dict with:
        - orphan_rules: count of applicability rules with no matching provision
        - missing_cross_ref_targets: count of cross-refs where target provision is gone
        - provisions_without_domains: count of provisions with null domain_id
        - rate_tables_without_source_url: count of rate tables missing source_url
        """
        result = {
            "orphan_rules": 0,
            "missing_cross_ref_targets": 0,
            "provisions_without_domains": 0,
            "rate_tables_without_source_url": 0,
        }

        # Count provisions without domains
        all_provisions_raw = self._execute(
            "ProvisionListNode", "all_provs", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_provisions = self._extract_records(all_provisions_raw)
        result["provisions_without_domains"] = sum(
            1 for p in all_provisions if not p.get("domain_id")
        )

        # Count rate tables without source_url
        all_rates_raw = self._execute(
            "RateTableListNode", "all_rates", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_rates = self._extract_records(all_rates_raw)
        result["rate_tables_without_source_url"] = sum(
            1
            for r in all_rates
            if not r.get("source_url")
            or (isinstance(r.get("source_url"), str) and not r["source_url"].strip())
        )

        # Check orphan applicability rules
        all_rules_raw = self._execute(
            "ApplicabilityRuleListNode",
            "all_rules",
            {"filter": {}, "enable_cache": False, "limit": 10000},
        )
        all_rules = self._extract_records(all_rules_raw)
        provision_ids = {p["id"] for p in all_provisions}
        result["orphan_rules"] = sum(
            1 for r in all_rules if r.get("provision_id") not in provision_ids
        )

        # Check cross-references with missing targets
        all_xrefs_raw = self._execute(
            "CrossReferenceListNode",
            "all_xrefs",
            {"filter": {}, "enable_cache": False, "limit": 10000},
        )
        all_xrefs = self._extract_records(all_xrefs_raw)
        result["missing_cross_ref_targets"] = sum(
            1 for x in all_xrefs if x.get("target_provision_id") not in provision_ids
        )

        logger.info("DB integrity check: %s", result)
        return result

    # ------------------------------------------------------------------
    # Quality report
    # ------------------------------------------------------------------

    def generate_quality_report(self) -> dict:
        """Generate a quality report on knowledge base coverage.

        Returns a dict with:
        - total_provisions: total count
        - provisions_per_domain: {domain_name: count}
        - provisions_with_examples: count of provisions that have at least one example
        - provisions_without_examples: count of provisions with no examples
        """
        # Get all provisions
        all_provisions_raw = self._execute(
            "ProvisionListNode", "all_provs", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_provisions = self._extract_records(all_provisions_raw)

        total = len(all_provisions)

        # Get all domains for name lookup
        all_domains_raw = self._execute(
            "DomainListNode", "all_domains", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_domains = self._extract_records(all_domains_raw)
        domain_map = {d["id"]: d["name"] for d in all_domains}

        # Count provisions per domain
        provisions_per_domain: dict[str, int] = {}
        for prov in all_provisions:
            domain_id = prov.get("domain_id")
            domain_name = domain_map.get(domain_id, "Unassigned") if domain_id else "Unassigned"
            provisions_per_domain[domain_name] = provisions_per_domain.get(domain_name, 0) + 1

        # Get all examples
        all_examples_raw = self._execute(
            "PracticalExampleListNode",
            "all_examples",
            {"filter": {}, "enable_cache": False, "limit": 10000},
        )
        all_examples = self._extract_records(all_examples_raw)

        provision_ids_with_examples = {e["provision_id"] for e in all_examples}
        with_examples = sum(1 for p in all_provisions if p["id"] in provision_ids_with_examples)
        without_examples = total - with_examples

        report = {
            "total_provisions": total,
            "provisions_per_domain": provisions_per_domain,
            "provisions_with_examples": with_examples,
            "provisions_without_examples": without_examples,
        }

        logger.info("Quality report: %d provisions, %d with examples", total, with_examples)
        return report
