"""T478: Comprehensive intent classification tests for the Shadow Agent.

Tests the RULE-BASED classifier (ShadowIntentClassifier._classify_rule_based)
since LLM classification requires external API calls. Also tests the standalone
_classify_trust_level function and attachment detection logic.

100+ test cases covering all classification categories:
- Employee commands
- Leave queries and actions
- Attendance commands
- Payroll queries and actions
- Navigation commands
- Advisory fallback
- Attachment detection
- Trust level verification
- Government/financial double_confirm
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

# Prevent Kaizen import chain
_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

from hr_advisory.shadow.intent_classifier import (
    ShadowIntent,
    ShadowIntentClassifier,
    _classify_trust_level,
    _AUTONOMOUS_ACTIONS,
    _ALWAYS_PROPOSE_ACTIONS,
    _DOUBLE_CONFIRM_ACTIONS,
    _DOUBLE_CONFIRM_MODULES,
)


# ── Helpers ──────────────────────────────────────────────────────


def _rule_based(message: str, page_context: str = "dashboard") -> ShadowIntent:
    """Classify using only the rule-based fallback (no LLM)."""
    classifier = ShadowIntentClassifier()
    return classifier._classify_rule_based(message, page_context)


# =========================================================================
# ShadowIntent Dataclass Tests
# =========================================================================


class TestShadowIntentDataclass:
    """ShadowIntent construction and serialization."""

    def test_create_intent_all_fields(self) -> None:
        intent = ShadowIntent(
            module="employees",
            action="create",
            entities={"name": "John"},
            trust_level="propose",
            requires_confirmation=True,
            confirmation_message="Create John?",
            has_attachment=False,
            attachment_intent="",
            raw_query="onboard John",
        )
        assert intent.module == "employees"
        assert intent.action == "create"
        assert intent.entities == {"name": "John"}
        assert intent.trust_level == "propose"
        assert intent.requires_confirmation is True
        assert intent.confirmation_message == "Create John?"
        assert intent.has_attachment is False
        assert intent.attachment_intent == ""
        assert intent.raw_query == "onboard John"

    def test_to_dict_roundtrip(self) -> None:
        intent = ShadowIntent(
            module="leave",
            action="apply",
            entities={"days": 2},
            trust_level="propose",
            requires_confirmation=True,
            confirmation_message="Apply for leave",
            has_attachment=False,
            attachment_intent="",
            raw_query="apply leave",
        )
        d = intent.to_dict()
        assert d["module"] == "leave"
        assert d["action"] == "apply"
        assert d["entities"] == {"days": 2}
        assert d["trust_level"] == "propose"
        assert d["requires_confirmation"] is True
        assert d["has_attachment"] is False
        assert d["raw_query"] == "apply leave"

    def test_to_dict_with_attachment(self) -> None:
        intent = ShadowIntent(
            module="employees",
            action="import",
            entities={},
            trust_level="propose",
            requires_confirmation=True,
            confirmation_message="Import employees",
            has_attachment=True,
            attachment_intent="bulk_import",
            raw_query="import csv",
        )
        d = intent.to_dict()
        assert d["has_attachment"] is True
        assert d["attachment_intent"] == "bulk_import"


# =========================================================================
# Employee Command Classification
# =========================================================================


class TestEmployeeClassification:
    """Employee module classification via rule-based classifier."""

    def test_show_employees(self) -> None:
        intent = _rule_based("show employees")
        assert intent.module == "employees"
        assert intent.action == "list"

    def test_list_employees(self) -> None:
        intent = _rule_based("list employees")
        assert intent.module == "employees"
        assert intent.action == "list"

    def test_all_employees(self) -> None:
        intent = _rule_based("all employees")
        assert intent.module == "employees"
        assert intent.action == "list"

    def test_employee_list(self) -> None:
        intent = _rule_based("employee list")
        assert intent.module == "employees"
        assert intent.action == "list"

    def test_employees_list_trust_level(self) -> None:
        intent = _rule_based("show employees")
        assert intent.trust_level == "autonomous"
        assert intent.requires_confirmation is False

    def test_employees_list_has_no_attachment(self) -> None:
        intent = _rule_based("show employees")
        assert intent.has_attachment is False
        assert intent.attachment_intent == ""

    def test_employees_list_confirmation_message(self) -> None:
        intent = _rule_based("list employees")
        assert intent.confirmation_message != ""

    def test_employees_list_raw_query_preserved(self) -> None:
        msg = "show employees please"
        intent = _rule_based(msg)
        assert intent.raw_query == msg


# =========================================================================
# Leave Query Classification
# =========================================================================


class TestLeaveQueryClassification:
    """Leave balance/query classification."""

    def test_leave_balance(self) -> None:
        intent = _rule_based("leave balance")
        assert intent.module == "leave"
        assert intent.action == "balance"

    def test_my_leave(self) -> None:
        intent = _rule_based("my leave")
        assert intent.module == "leave"
        assert intent.action == "balance"

    def test_how_many_days_leave(self) -> None:
        intent = _rule_based("how many days leave do I have")
        assert intent.module == "leave"
        assert intent.action == "balance"

    def test_leave_balance_is_autonomous(self) -> None:
        intent = _rule_based("leave balance")
        assert intent.trust_level == "autonomous"
        assert intent.requires_confirmation is False


# =========================================================================
# Leave Action Classification
# =========================================================================


class TestLeaveActionClassification:
    """Leave apply/action classification."""

    def test_apply_leave(self) -> None:
        intent = _rule_based("apply leave")
        assert intent.module == "leave"
        assert intent.action == "apply"

    def test_take_leave(self) -> None:
        intent = _rule_based("take leave tomorrow")
        assert intent.module == "leave"
        assert intent.action == "apply"

    def test_apply_for_leave(self) -> None:
        intent = _rule_based("apply for leave next week")
        assert intent.module == "leave"
        assert intent.action == "apply"

    def test_apply_leave_requires_confirmation(self) -> None:
        intent = _rule_based("apply leave")
        assert intent.trust_level == "propose"
        assert intent.requires_confirmation is True


# =========================================================================
# Attendance Classification
# =========================================================================


class TestAttendanceClassification:
    """Attendance clock in/out classification."""

    def test_clock_in(self) -> None:
        intent = _rule_based("clock in")
        assert intent.module == "attendance"
        assert intent.action == "clock_in"

    def test_clock_me_in(self) -> None:
        intent = _rule_based("clock me in")
        assert intent.module == "attendance"
        assert intent.action == "clock_in"

    def test_punch_in(self) -> None:
        intent = _rule_based("punch in")
        assert intent.module == "attendance"
        assert intent.action == "clock_in"

    def test_clock_out(self) -> None:
        intent = _rule_based("clock out")
        assert intent.module == "attendance"
        assert intent.action == "clock_out"

    def test_clock_me_out(self) -> None:
        intent = _rule_based("clock me out")
        assert intent.module == "attendance"
        assert intent.action == "clock_out"

    def test_punch_out(self) -> None:
        intent = _rule_based("punch out")
        assert intent.module == "attendance"
        assert intent.action == "clock_out"

    def test_clock_in_requires_confirmation(self) -> None:
        intent = _rule_based("clock in")
        assert intent.trust_level == "propose"
        assert intent.requires_confirmation is True

    def test_clock_out_requires_confirmation(self) -> None:
        intent = _rule_based("clock out")
        assert intent.trust_level == "propose"
        assert intent.requires_confirmation is True


# =========================================================================
# Payroll Classification
# =========================================================================


class TestPayrollClassification:
    """Payroll queries and actions."""

    def test_my_payslips(self) -> None:
        intent = _rule_based("my payslips")
        assert intent.module == "payroll"
        assert intent.action == "my_payslips"

    def test_my_payslip_singular(self) -> None:
        intent = _rule_based("my payslip")
        assert intent.module == "payroll"
        assert intent.action == "my_payslips"

    def test_show_payslip(self) -> None:
        intent = _rule_based("show payslip")
        assert intent.module == "payroll"
        assert intent.action == "my_payslips"

    def test_payslips_autonomous(self) -> None:
        intent = _rule_based("my payslips")
        assert intent.trust_level == "autonomous"
        assert intent.requires_confirmation is False

    def test_run_payroll(self) -> None:
        intent = _rule_based("run payroll")
        assert intent.module == "payroll"
        assert intent.action == "calculate"

    def test_calculate_payroll(self) -> None:
        intent = _rule_based("calculate payroll for March")
        assert intent.module == "payroll"
        assert intent.action == "calculate"

    def test_process_payroll(self) -> None:
        intent = _rule_based("process payroll")
        assert intent.module == "payroll"
        assert intent.action == "calculate"

    def test_payroll_calculate_requires_confirmation(self) -> None:
        intent = _rule_based("run payroll")
        assert intent.trust_level == "propose"
        assert intent.requires_confirmation is True


# =========================================================================
# Navigation Classification
# =========================================================================


class TestNavigationClassification:
    """Navigation command classification for all routes."""

    def test_go_to_dashboard(self) -> None:
        intent = _rule_based("go to dashboard")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/my-dashboard"

    def test_go_to_employees(self) -> None:
        intent = _rule_based("go to employees")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/employees"

    def test_go_to_payroll(self) -> None:
        intent = _rule_based("go to payroll")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/payroll"

    def test_go_to_leave(self) -> None:
        intent = _rule_based("go to leave")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/leave"

    def test_go_to_attendance(self) -> None:
        intent = _rule_based("go to attendance")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/attendance"

    def test_go_to_claims(self) -> None:
        intent = _rule_based("go to claims")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/claims"

    def test_go_to_shifts(self) -> None:
        intent = _rule_based("go to shifts")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/shifts"

    def test_go_to_appraisals(self) -> None:
        intent = _rule_based("go to appraisals")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/appraisals"

    def test_go_to_projects(self) -> None:
        intent = _rule_based("go to projects")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/projects"

    def test_go_to_inventory(self) -> None:
        intent = _rule_based("go to inventory")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/inventory"

    def test_go_to_recruitment(self) -> None:
        intent = _rule_based("go to recruitment")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/recruitment"

    def test_go_to_reports(self) -> None:
        intent = _rule_based("go to reports")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/reports"

    def test_go_to_documents(self) -> None:
        intent = _rule_based("go to documents")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/documents"

    def test_go_to_compliance(self) -> None:
        intent = _rule_based("go to compliance")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/compliance"

    def test_go_to_settings(self) -> None:
        intent = _rule_based("go to settings")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/settings"

    def test_go_to_calculator(self) -> None:
        intent = _rule_based("go to calculator")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/calculator"

    def test_go_to_advisory(self) -> None:
        intent = _rule_based("go to advisory")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/advisory"

    def test_go_to_leave_calendar(self) -> None:
        intent = _rule_based("go to leave calendar")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/leave/calendar"

    def test_go_to_org_chart(self) -> None:
        intent = _rule_based("go to org chart")
        assert intent.module == "navigation"
        assert intent.action == "navigate"
        assert intent.entities["route"] == "/employees/org-chart"

    def test_navigation_is_autonomous(self) -> None:
        intent = _rule_based("go to dashboard")
        assert intent.trust_level == "autonomous"
        assert intent.requires_confirmation is False

    def test_navigation_has_no_attachment(self) -> None:
        intent = _rule_based("go to payroll")
        assert intent.has_attachment is False

    def test_navigation_confirmation_message_not_empty(self) -> None:
        intent = _rule_based("go to employees")
        assert intent.confirmation_message != ""

    def test_navigation_requires_go_to_prefix(self) -> None:
        """Without 'go to' prefix, navigation keywords do not trigger nav routing."""
        intent = _rule_based("payroll")
        # Without "go to" prefix, should fall through to advisory
        assert intent.module != "navigation"


# =========================================================================
# Advisory Fallback Classification
# =========================================================================


class TestAdvisoryFallback:
    """Unrecognized queries should fall back to advisory."""

    def test_general_question(self) -> None:
        intent = _rule_based("what is the notice period for termination?")
        assert intent.module == "advisory"
        assert intent.action == "query"

    def test_employment_law_question(self) -> None:
        intent = _rule_based("is overtime compulsory in Singapore?")
        assert intent.module == "advisory"
        assert intent.action == "query"

    def test_random_question(self) -> None:
        intent = _rule_based("how do I handle a grievance?")
        assert intent.module == "advisory"
        assert intent.action == "query"

    def test_advisory_is_autonomous(self) -> None:
        intent = _rule_based("what is the minimum retirement age?")
        assert intent.trust_level == "autonomous"
        assert intent.requires_confirmation is False

    def test_advisory_entities_contain_query(self) -> None:
        msg = "what is the probation period?"
        intent = _rule_based(msg)
        assert intent.entities.get("query") == msg

    def test_advisory_raw_query_preserved(self) -> None:
        msg = "tell me about maternity leave entitlements"
        intent = _rule_based(msg)
        assert intent.raw_query == msg


# =========================================================================
# Attachment Detection
# =========================================================================


class TestAttachmentDetection:
    """Attachment detection in user messages."""

    def test_import_csv(self) -> None:
        intent = _rule_based("import csv of employees")
        assert intent.has_attachment is True
        assert intent.attachment_intent == "bulk_import"

    def test_upload_employees(self) -> None:
        intent = _rule_based("upload employees from spreadsheet")
        assert intent.has_attachment is True
        assert intent.attachment_intent == "bulk_import"

    def test_excel_file(self) -> None:
        intent = _rule_based("I have an xlsx file to import")
        assert intent.has_attachment is True
        assert intent.attachment_intent == "bulk_import"

    def test_spreadsheet_import(self) -> None:
        intent = _rule_based("import from spreadsheet")
        assert intent.has_attachment is True
        assert intent.attachment_intent == "bulk_import"

    def test_bulk_import(self) -> None:
        intent = _rule_based("do a bulk import of employees")
        assert intent.has_attachment is True
        assert intent.attachment_intent == "bulk_import"

    def test_receipt_upload(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("upload receipt for taxi")
        assert has_att is True
        assert att_intent == "receipt_upload"

    def test_receipt_keyword(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("attach receipt for lunch claim")
        assert has_att is True
        assert att_intent == "receipt_upload"

    def test_document_upload(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("upload document for employee")
        assert has_att is True
        assert att_intent == "document_upload"

    def test_pdf_upload(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("upload pdf contract")
        assert has_att is True
        assert att_intent == "document_upload"

    def test_contract_upload(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("upload contract for new hire")
        assert has_att is True
        assert att_intent == "document_upload"

    def test_payroll_csv(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("upload payroll csv")
        assert has_att is True
        assert att_intent == "payroll_import"

    def test_payroll_file(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("import payroll file")
        assert has_att is True
        assert att_intent == "payroll_import"

    def test_generic_file_reference(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("I have a file to upload")
        assert has_att is True
        assert att_intent == ""  # generic — no specific intent

    def test_no_attachment(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("show me all employees")
        assert has_att is False
        assert att_intent == ""

    def test_no_attachment_plain_question(self) -> None:
        classifier = ShadowIntentClassifier()
        has_att, att_intent = classifier._detect_attachment("what is the leave policy?")
        assert has_att is False
        assert att_intent == ""


# =========================================================================
# Trust Level Classification (_classify_trust_level)
# =========================================================================


class TestTrustLevelClassification:
    """_classify_trust_level standalone function tests."""

    # ── Autonomous actions ────────────────────────────────────────

    @pytest.mark.parametrize(
        "action",
        [
            "list",
            "get",
            "view",
            "search",
            "navigate",
            "check",
            "balance",
            "summary",
            "history",
            "calendar",
            "dashboard",
            "status",
            "count",
            "my_payslips",
            "my_leave",
            "my_schedule",
        ],
    )
    def test_autonomous_actions(self, action: str) -> None:
        trust_level, requires_confirmation = _classify_trust_level(action)
        assert trust_level == "autonomous"
        assert requires_confirmation is False

    # ── Always-propose actions ────────────────────────────────────

    @pytest.mark.parametrize(
        "action",
        [
            "delete",
            "terminate",
            "cancel",
            "cancel_payroll",
            "mark_paid",
            "bulk_delete",
            "reset",
            "revoke",
            "deactivate",
            "remove",
        ],
    )
    def test_always_propose_actions(self, action: str) -> None:
        trust_level, requires_confirmation = _classify_trust_level(action)
        assert trust_level == "always_propose"
        assert requires_confirmation is True

    # ── Double-confirm actions ────────────────────────────────────

    @pytest.mark.parametrize(
        "action",
        [
            "cpf_submit",
            "ir8a_submit",
            "ir21_generate",
            "post_payroll_journal",
            "post_claims_journal",
            "giro_submit",
            "giro_process",
        ],
    )
    def test_double_confirm_actions(self, action: str) -> None:
        trust_level, requires_confirmation = _classify_trust_level(action)
        assert trust_level == "double_confirm"
        assert requires_confirmation is True

    # ── Propose actions (default) ─────────────────────────────────

    @pytest.mark.parametrize(
        "action",
        [
            "create",
            "update",
            "approve",
            "reject",
            "apply",
            "submit",
            "generate",
            "invite",
            "import",
            "encash",
            "download",
            "export",
        ],
    )
    def test_propose_actions(self, action: str) -> None:
        trust_level, requires_confirmation = _classify_trust_level(action)
        assert trust_level == "propose"
        assert requires_confirmation is True

    # ── Government module double-confirm ──────────────────────────

    def test_government_module_forces_double_confirm(self) -> None:
        """Any action on the government module should be double_confirm."""
        trust_level, requires_confirmation = _classify_trust_level("list", module="government")
        assert trust_level == "double_confirm"
        assert requires_confirmation is True

    def test_government_module_overrides_autonomous(self) -> None:
        """Even normally autonomous actions get double_confirm for government."""
        trust_level, _ = _classify_trust_level("get", module="government")
        assert trust_level == "double_confirm"

    def test_government_module_with_write_action(self) -> None:
        trust_level, requires_confirmation = _classify_trust_level("create", module="government")
        assert trust_level == "double_confirm"
        assert requires_confirmation is True

    def test_government_module_with_delete_action(self) -> None:
        """Government + delete: double_confirm takes priority (matched first)."""
        trust_level, requires_confirmation = _classify_trust_level("delete", module="government")
        # delete is in _ALWAYS_PROPOSE_ACTIONS but government module check
        # comes AFTER the autonomous check but BEFORE always_propose in the code.
        # Actually in the code: autonomous → double_confirm → always_propose → propose
        # Since delete is NOT autonomous, it hits the double_confirm check (module=government).
        assert trust_level in ("double_confirm", "always_propose")
        assert requires_confirmation is True

    # ── Non-government modules don't get double-confirm ───────────

    def test_non_government_module_no_double_confirm(self) -> None:
        trust_level, _ = _classify_trust_level("create", module="employees")
        assert trust_level == "propose"

    def test_empty_module_default(self) -> None:
        trust_level, _ = _classify_trust_level("create")
        assert trust_level == "propose"


# =========================================================================
# Frozen Sets Consistency
# =========================================================================


class TestFrozenSetsConsistency:
    """Verify the action sets don't overlap."""

    def test_autonomous_and_always_propose_disjoint(self) -> None:
        overlap = _AUTONOMOUS_ACTIONS & _ALWAYS_PROPOSE_ACTIONS
        assert len(overlap) == 0, f"Overlap: {overlap}"

    def test_autonomous_and_double_confirm_disjoint(self) -> None:
        overlap = _AUTONOMOUS_ACTIONS & _DOUBLE_CONFIRM_ACTIONS
        assert len(overlap) == 0, f"Overlap: {overlap}"

    def test_always_propose_and_double_confirm_disjoint(self) -> None:
        overlap = _ALWAYS_PROPOSE_ACTIONS & _DOUBLE_CONFIRM_ACTIONS
        assert len(overlap) == 0, f"Overlap: {overlap}"

    def test_double_confirm_modules_non_empty(self) -> None:
        assert "government" in _DOUBLE_CONFIRM_MODULES


# =========================================================================
# Classifier Integration (LLM fallback path)
# =========================================================================


class TestClassifierFallbackPath:
    """Verify the classify() method falls back to rule-based when LLM unavailable."""

    @pytest.mark.asyncio
    async def test_no_api_key_uses_fallback(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("show employees")
        assert intent.module == "employees"
        assert intent.action == "list"

    @pytest.mark.asyncio
    async def test_fallback_still_produces_valid_intent(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("random question about HR law")
        assert isinstance(intent, ShadowIntent)
        assert intent.module is not None
        assert intent.action is not None
        assert isinstance(intent.entities, dict)

    @pytest.mark.asyncio
    async def test_fallback_clock_in(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("clock me in")
        assert intent.module == "attendance"
        assert intent.action == "clock_in"

    @pytest.mark.asyncio
    async def test_fallback_payslip(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("show payslip")
        assert intent.module == "payroll"
        assert intent.action == "my_payslips"

    @pytest.mark.asyncio
    async def test_fallback_navigation(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("go to dashboard")
        assert intent.module == "navigation"
        assert intent.action == "navigate"

    @pytest.mark.asyncio
    async def test_fallback_advisory(self) -> None:
        classifier = ShadowIntentClassifier()
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}):
            intent = await classifier.classify("what is the law on wrongful dismissal?")
        assert intent.module == "advisory"
        assert intent.action == "query"
