"""Core content pipeline for populating the regulatory knowledge base.

Orchestrates bulk loading of legislative content using DataFlow workflow nodes.
All database operations go through Kailash WorkflowBuilder + LocalRuntime,
never direct SQL.
"""

import logging
from datetime import datetime
from typing import Optional

from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

logger = logging.getLogger(__name__)


class KBContentPipeline:
    """Orchestrates bulk loading of regulatory content into the knowledge base."""

    def __init__(self, db_instance=None):
        """Initialise the pipeline.

        Args:
            db_instance: Optional DataFlow instance.  Not used directly for
                queries (we use workflow nodes), but kept for forward
                compatibility.
        """
        self._db = db_instance
        self._runtime = LocalRuntime()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute(self, node_type: str, node_id: str, params: dict) -> dict:
        """Run a single-node workflow and return the node result."""
        wf = WorkflowBuilder()
        wf.add_node(node_type, node_id, params)
        results, _ = self._runtime.execute(wf.build())
        return results[node_id]

    @staticmethod
    def _extract_records(result) -> list[dict]:
        """Extract the record list from a ListNode result.

        DataFlow ListNode returns either:
        - A plain list of dicts, OR
        - A dict with {"records": [...], "count": N, "limit": N, ...}

        This helper normalises both forms to a plain list.
        """
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "records" in result:
            return result["records"]
        return []

    def _find_act_by_short_name(self, short_name: str) -> Optional[dict]:
        """Look up an act by short_name.  Returns the record or None."""
        result = self._execute(
            "ActListNode",
            "find_act",
            {"filter": {"short_name": short_name}, "enable_cache": False},
        )
        records = self._extract_records(result)
        if records:
            return records[0]
        return None

    def _find_domain_by_name(self, name: str) -> Optional[dict]:
        """Look up a domain by name.  Returns the record or None."""
        result = self._execute(
            "DomainListNode",
            "find_domain",
            {"filter": {"name": name}, "enable_cache": False},
        )
        records = self._extract_records(result)
        if records:
            return records[0]
        return None

    def _find_provision_by_section(self, section: str) -> Optional[dict]:
        """Look up a provision by section.  Returns the record or None."""
        result = self._execute(
            "ProvisionListNode",
            "find_prov",
            {"filter": {"section": section}, "enable_cache": False},
        )
        records = self._extract_records(result)
        if records:
            return records[0]
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_act(self, act_data: dict) -> dict:
        """Create or update an Act record.

        Idempotent on ``short_name``: if an Act with the same short_name
        already exists, the existing record is returned instead of creating
        a duplicate.

        Returns:
            The created or existing act as a dict (including ``id``).

        Raises:
            ValueError: If ``short_name`` is missing from act_data.
        """
        short_name = act_data.get("short_name")
        if not short_name:
            raise ValueError("act_data must include 'short_name'")

        existing = self._find_act_by_short_name(short_name)
        if existing:
            logger.info(
                "Act '%s' already exists (id=%s), returning existing", short_name, existing["id"]
            )
            return existing

        logger.info("Creating act: %s (%s)", act_data.get("title", ""), short_name)
        return self._execute("ActCreateNode", "create_act", act_data)

    def load_domain(self, domain_data: dict) -> dict:
        """Create or update a Domain record.

        Supports hierarchy via ``parent_domain_name`` -- the parent is
        resolved to ``parent_domain_id`` automatically.

        Idempotent on ``name``.

        Returns:
            The created or existing domain as a dict (including ``id``).

        Raises:
            ValueError: If ``name`` is missing, or if ``parent_domain_name``
                is given but the parent domain does not exist.
        """
        name = domain_data.get("name")
        if not name:
            raise ValueError("domain_data must include 'name'")

        existing = self._find_domain_by_name(name)
        if existing:
            logger.info(
                "Domain '%s' already exists (id=%s), returning existing", name, existing["id"]
            )
            return existing

        create_params = {k: v for k, v in domain_data.items() if k != "parent_domain_name"}

        parent_domain_name = domain_data.get("parent_domain_name")
        if parent_domain_name:
            parent = self._find_domain_by_name(parent_domain_name)
            if not parent:
                raise ValueError(
                    f"Parent domain '{parent_domain_name}' not found. "
                    f"Load it before loading child domain '{name}'."
                )
            create_params["parent_domain_id"] = parent["id"]

        logger.info("Creating domain: %s", name)
        return self._execute("DomainCreateNode", "create_domain", create_params)

    def load_provision(self, provision_data: dict) -> dict:
        """Load a provision with all metadata.

        Resolves:
        - ``act_short_name`` -> ``source_act_id``
        - ``domain_name`` -> ``domain_id``

        Returns:
            The created provision as a dict (including ``id``).

        Raises:
            ValueError: If the referenced act or domain does not exist.
        """
        data = dict(provision_data)

        # Idempotency: check if provision already exists by section
        section = data.get("section")
        if section:
            existing = self._find_provision_by_section(section)
            if existing:
                logger.info(
                    "Provision '%s' already exists (id=%s), returning existing",
                    section,
                    existing.get("id"),
                )
                return existing

        # Resolve act
        act_short_name = data.pop("act_short_name", None)
        if act_short_name:
            act = self._find_act_by_short_name(act_short_name)
            if not act:
                raise ValueError(
                    f"Act with short_name '{act_short_name}' not found. "
                    f"Load the act before loading provisions."
                )
            data["source_act_id"] = act["id"]

        if "source_act_id" not in data:
            raise ValueError(
                "Provision must have either 'act_short_name' or 'source_act_id'. "
                "Neither was provided."
            )

        # Resolve domain
        domain_name = data.pop("domain_name", None)
        if domain_name:
            domain = self._find_domain_by_name(domain_name)
            if not domain:
                raise ValueError(
                    f"Domain '{domain_name}' not found. "
                    f"Load the domain before loading provisions."
                )
            data["domain_id"] = domain["id"]

        # Strip nested collections that are not part of the Provision model
        data.pop("applicability_rules", None)
        data.pop("practical_examples", None)

        # Convert effective_date string to something DataFlow can handle
        if isinstance(data.get("effective_date"), str):
            data["effective_date"] = datetime.fromisoformat(data["effective_date"])

        logger.info("Creating provision: %s - %s", data.get("section"), data.get("title"))
        result = self._execute("ProvisionCreateNode", "create_provision", data)
        if isinstance(result, dict):
            result["_newly_created"] = True
        return result

    def load_applicability_rule(self, provision_id: int, rule_data: dict) -> dict:
        """Add an applicability rule to a provision.

        Args:
            provision_id: The ID of the provision this rule belongs to.
            rule_data: Dict with rule_type, criteria_value, and optionally
                criteria_type and notes.

        Returns:
            The created applicability rule as a dict (including ``id``).
        """
        params = {
            "provision_id": provision_id,
            **rule_data,
        }
        logger.info(
            "Creating applicability rule for provision %s: type=%s",
            provision_id,
            rule_data.get("rule_type", "unknown"),
        )
        return self._execute("ApplicabilityRuleCreateNode", "create_rule", params)

    def load_cross_reference(
        self,
        source_provision_id: int,
        target_provision_id: int,
        relationship_type: str,
        notes: str = "",
    ) -> dict:
        """Create a cross-reference between two provisions.

        Args:
            source_provision_id: ID of the source provision.
            target_provision_id: ID of the target provision.
            relationship_type: One of CrossReferenceType values.
            notes: Optional explanation of the relationship.

        Returns:
            The created cross-reference as a dict (including ``id``).
        """
        params = {
            "source_provision_id": source_provision_id,
            "target_provision_id": target_provision_id,
            "relationship_type": relationship_type,
        }
        if notes:
            params["notes"] = notes

        logger.info(
            "Creating cross-reference: provision %s -> %s (%s)",
            source_provision_id,
            target_provision_id,
            relationship_type,
        )
        return self._execute("CrossReferenceCreateNode", "create_xref", params)

    def load_practical_example(self, provision_id: int, example_data: dict) -> dict:
        """Add a worked example for a provision.

        Args:
            provision_id: The ID of the provision this example illustrates.
            example_data: Dict with scenario, calculation (dict), and outcome.

        Returns:
            The created practical example as a dict (including ``id``).
        """
        params = {
            "provision_id": provision_id,
            **example_data,
        }
        logger.info(
            "Creating practical example for provision %s: %s",
            provision_id,
            example_data.get("scenario", "")[:60],
        )
        return self._execute("PracticalExampleCreateNode", "create_example", params)

    def load_rate_table(self, rate_data: dict) -> dict:
        """Load a rate table entry (CPF rates, levy rates, etc.).

        Date strings in ``effective_date`` and ``expiry_date`` are
        automatically converted to datetime objects.

        Returns:
            The created rate table entry as a dict (including ``id``).
        """
        data = dict(rate_data)

        # Convert date strings
        for date_field in ("effective_date", "expiry_date"):
            if isinstance(data.get(date_field), str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        logger.info(
            "Creating rate table: type=%s effective=%s",
            data.get("table_type"),
            data.get("effective_date"),
        )
        return self._execute("RateTableCreateNode", "create_rate", data)

    # ------------------------------------------------------------------
    # Bulk load
    # ------------------------------------------------------------------

    def bulk_load(self, content_bundle: dict) -> dict:
        """Load an entire content bundle.

        Accepts a structured dict with keys: act, domains, provisions,
        cross_references, rate_tables.

        Provisions may contain nested ``applicability_rules`` and
        ``practical_examples`` which are extracted and loaded separately.

        Cross-references are specified by ``source_section`` and
        ``target_section`` and resolved to provision IDs.

        Returns:
            Summary dict with keys matching the input, each containing
            the loaded records with their database IDs.
        """
        summary: dict = {
            "act": None,
            "domains": [],
            "provisions": [],
            "applicability_rules": [],
            "practical_examples": [],
            "cross_references": [],
            "rate_tables": [],
        }

        # 1. Act
        act_data = content_bundle.get("act")
        if act_data:
            summary["act"] = self.load_act(act_data)
            logger.info(
                "Loaded act: %s (id=%s)", summary["act"]["short_name"], summary["act"]["id"]
            )

        # 2. Domains (order matters for parent-child)
        for domain_data in content_bundle.get("domains", []):
            domain = self.load_domain(domain_data)
            summary["domains"].append(domain)

        # 3. Provisions (with nested rules and examples)
        for prov_data in content_bundle.get("provisions", []):
            prov_copy = dict(prov_data)
            nested_rules = prov_copy.pop("applicability_rules", [])
            nested_examples = prov_copy.pop("practical_examples", [])

            # Default act_short_name to the bundle act if not specified
            if "act_short_name" not in prov_copy and "source_act_id" not in prov_copy:
                if act_data and "short_name" in act_data:
                    prov_copy["act_short_name"] = act_data["short_name"]

            provision = self.load_provision(prov_copy)
            summary["provisions"].append(provision)

            # Only load nested rules/examples if the provision was newly created
            # (existing provisions already have their rules/examples)
            is_new = provision.get("_newly_created", False)
            if is_new:
                # Load nested applicability rules
                for rule_data in nested_rules:
                    rule = self.load_applicability_rule(provision["id"], rule_data)
                    summary["applicability_rules"].append(rule)

                # Load nested practical examples
                for example_data in nested_examples:
                    example = self.load_practical_example(provision["id"], example_data)
                    summary["practical_examples"].append(example)

        # 4. Cross-references (resolve by section)
        for xref_data in content_bundle.get("cross_references", []):
            source_section = xref_data.get("source_section")
            target_section = xref_data.get("target_section")

            source_prov = self._find_provision_by_section(source_section)
            if not source_prov:
                logger.error(
                    "Cross-reference source section '%s' not found, skipping",
                    source_section,
                )
                continue

            target_prov = self._find_provision_by_section(target_section)
            if not target_prov:
                logger.error(
                    "Cross-reference target section '%s' not found, skipping",
                    target_section,
                )
                continue

            xref = self.load_cross_reference(
                source_provision_id=source_prov["id"],
                target_provision_id=target_prov["id"],
                relationship_type=xref_data.get("relationship_type", "related"),
                notes=xref_data.get("notes", ""),
            )
            summary["cross_references"].append(xref)

        # 5. Rate tables
        for rate_data in content_bundle.get("rate_tables", []):
            rate = self.load_rate_table(rate_data)
            summary["rate_tables"].append(rate)

        logger.info(
            "Bulk load complete: %d domains, %d provisions, %d rules, "
            "%d examples, %d cross-refs, %d rate tables",
            len(summary["domains"]),
            len(summary["provisions"]),
            len(summary["applicability_rules"]),
            len(summary["practical_examples"]),
            len(summary["cross_references"]),
            len(summary["rate_tables"]),
        )
        return summary
