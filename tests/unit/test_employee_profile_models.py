"""Unit tests for M39: Employee Profile Models & APIs.

Tests model field declarations, enum values, indexes, and new model definitions
for employee profile extensions (T298-T307).

Tier 1 (Unit): Fast (<1s), isolated, no external dependencies.

Strategy: Parse the source file directly using AST to verify field declarations,
default values, and __dataflow__ metadata WITHOUT importing the models module
(which requires a live database connection). This approach is completely isolated
and does not interfere with other test modules.
"""

import ast
import os
import textwrap
from pathlib import Path
from typing import Any

import pytest

# Path to the source file under test
_MODEL_FILE = (
    Path(__file__).resolve().parents[2] / "src" / "hr_advisory" / "models" / "company_user.py"
)
_INIT_FILE = Path(__file__).resolve().parents[2] / "src" / "hr_advisory" / "models" / "__init__.py"


# ---------------------------------------------------------------------------
# AST-based model parser
# ---------------------------------------------------------------------------


def _parse_models(filepath: Path) -> dict[str, dict]:
    """Parse a Python file and extract all @db.model-decorated class definitions.

    Returns a dict mapping class name -> {
        "fields": {field_name: {"annotation": str, "default": Any | _MISSING}},
        "dataflow": dict (the __dataflow__ dict literal),
        "docstring": str,
    }
    """
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))

    models = {}
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check if decorated with @db.model
        is_model = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Attribute) and dec.attr == "model":
                is_model = True
            elif isinstance(dec, ast.Name) and dec.id == "model":
                is_model = True
        if not is_model:
            continue

        fields = {}
        dataflow_meta = {}
        docstring = ast.get_docstring(node) or ""

        for item in node.body:
            # Skip the docstring node
            if isinstance(item, ast.Expr) and isinstance(item.value, (ast.Constant, ast.Str)):
                continue

            # Annotated assignment: field_name: type = default
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                annotation = ast.unparse(item.annotation) if item.annotation else ""
                default = _MISSING
                if item.value is not None:
                    try:
                        default = ast.literal_eval(item.value)
                    except (ValueError, TypeError):
                        # Can't literal_eval (e.g. enum references) -- store as string
                        default = ast.unparse(item.value)
                fields[field_name] = {"annotation": annotation, "default": default}

            # __dataflow__ assignment
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__dataflow__":
                        try:
                            dataflow_meta = ast.literal_eval(item.value)
                        except (ValueError, TypeError):
                            dataflow_meta = {}

        models[node.name] = {
            "fields": fields,
            "dataflow": dataflow_meta,
            "docstring": docstring,
        }

    return models


class _MissingSentinel:
    """Sentinel for fields with no default value (i.e. required fields)."""

    def __repr__(self):
        return "<MISSING>"

    def __eq__(self, other):
        return isinstance(other, _MissingSentinel)


_MISSING = _MissingSentinel()


# ---------------------------------------------------------------------------
# Fixture: parse models once per session
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def models():
    """Parse all @db.model classes from company_user.py."""
    assert _MODEL_FILE.exists(), f"Model file not found: {_MODEL_FILE}"
    return _parse_models(_MODEL_FILE)


@pytest.fixture(scope="module")
def init_source():
    """Read the __init__.py source for import/export verification."""
    assert _INIT_FILE.exists(), f"Init file not found: {_INIT_FILE}"
    return _INIT_FILE.read_text()


# ---------------------------------------------------------------------------
# T298: Employee Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeFieldExtensions:
    """Verify that all new fields are declared on the Employee model."""

    # --- Personal fields ---

    def test_religion_field_exists(self, models):
        assert "religion" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["religion"]["default"] == ""

    def test_phone_field_exists(self, models):
        assert "phone" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["phone"]["default"] == ""

    def test_alias_field_exists(self, models):
        assert "alias" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["alias"]["default"] == ""

    def test_photo_url_field_exists(self, models):
        assert "photo_url" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["photo_url"]["default"] == ""

    def test_nationality_field_still_present(self, models):
        """nationality already exists on Employee -- verify it was not removed."""
        assert "nationality" in models["Employee"]["fields"]

    # --- Employment fields ---

    def test_salary_type_default_monthly(self, models):
        assert models["Employee"]["fields"]["salary_type"]["default"] == "monthly"

    def test_hourly_rate_default_zero(self, models):
        assert models["Employee"]["fields"]["hourly_rate"]["default"] == 0.0

    def test_daily_rate_default_zero(self, models):
        assert models["Employee"]["fields"]["daily_rate"]["default"] == 0.0

    def test_payment_method_default_giro(self, models):
        assert models["Employee"]["fields"]["payment_method"]["default"] == "giro"

    def test_payment_frequency_default_monthly(self, models):
        assert models["Employee"]["fields"]["payment_frequency"]["default"] == "monthly"

    def test_overtime_eligible_default_true(self, models):
        assert models["Employee"]["fields"]["overtime_eligible"]["default"] is True

    def test_working_hours_type_default_fixed(self, models):
        assert models["Employee"]["fields"]["working_hours_type"]["default"] == "fixed"

    # --- Bank fields ---

    def test_branch_code_exists(self, models):
        assert "branch_code" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["branch_code"]["default"] == ""

    # --- Tax fields ---

    def test_iras_auto_inclusion_default_true(self, models):
        assert models["Employee"]["fields"]["iras_auto_inclusion"]["default"] is True

    def test_tax_reference_exists(self, models):
        assert "tax_reference" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["tax_reference"]["default"] == ""

    # --- Tags ---

    def test_tags_exists(self, models):
        assert "tags" in models["Employee"]["fields"]
        assert models["Employee"]["fields"]["tags"]["default"] == ""

    # --- Statutory fields ---

    def test_cpf_status_default_include(self, models):
        assert models["Employee"]["fields"]["cpf_status"]["default"] == "include"

    def test_amcs_enabled_default_false(self, models):
        assert models["Employee"]["fields"]["amcs_enabled"]["default"] is False

    def test_pmbs_enabled_default_false(self, models):
        assert models["Employee"]["fields"]["pmbs_enabled"]["default"] is False

    def test_community_chest_amount_default_zero(self, models):
        assert models["Employee"]["fields"]["community_chest_amount"]["default"] == 0.0

    def test_shg_override_amount_default_zero(self, models):
        assert models["Employee"]["fields"]["shg_override_amount"]["default"] == 0.0

    # --- Address (structured) ---

    def test_address_block_exists(self, models):
        assert models["Employee"]["fields"]["address_block"]["default"] == ""

    def test_address_street_exists(self, models):
        assert models["Employee"]["fields"]["address_street"]["default"] == ""

    def test_address_unit_exists(self, models):
        assert models["Employee"]["fields"]["address_unit"]["default"] == ""

    def test_address_building_exists(self, models):
        assert models["Employee"]["fields"]["address_building"]["default"] == ""

    def test_address_postal_code_exists(self, models):
        assert models["Employee"]["fields"]["address_postal_code"]["default"] == ""

    # --- Organization FK fields ---

    def test_organization_id_optional_none(self, models):
        f = models["Employee"]["fields"]["organization_id"]
        assert f["default"] is None
        assert "Optional" in f["annotation"]

    def test_branch_id_optional_none(self, models):
        f = models["Employee"]["fields"]["branch_id"]
        assert f["default"] is None
        assert "Optional" in f["annotation"]

    def test_cost_centre_id_optional_none(self, models):
        f = models["Employee"]["fields"]["cost_centre_id"]
        assert f["default"] is None
        assert "Optional" in f["annotation"]

    def test_pay_scheme_id_optional_none(self, models):
        f = models["Employee"]["fields"]["pay_scheme_id"]
        assert f["default"] is None
        assert "Optional" in f["annotation"]

    # --- Existing fields not removed ---

    def test_existing_fields_preserved(self, models):
        """All pre-existing Employee fields must still be present."""
        existing_fields = [
            "user_id",
            "company_id",
            "employee_id_internal",
            "department",
            "designation",
            "employment_type",
            "start_date",
            "end_date",
            "pass_type",
            "salary_monthly",
            "notice_period_days",
            "is_active",
            "date_of_birth",
            "gender",
            "marital_status",
            "race",
            "nric_fin",
            "nric_fin_last4",
            "work_pass_number",
            "work_pass_expiry",
            "immigration_status",
            "immigration_effective_date",
            "bank_name",
            "bank_account_number",
            "bank_account_last4",
            "bank_code",
            "residential_address",
            "postal_code",
            "reporting_manager_id",
            "leave_policy_id",
            "probation_months",
            "probation_end_date",
            "confirmation_status",
        ]
        emp_fields = models["Employee"]["fields"]
        for field in existing_fields:
            assert field in emp_fields, f"Existing field '{field}' was removed!"


# ---------------------------------------------------------------------------
# T299: EmergencyContact Model Extensions
# ---------------------------------------------------------------------------


class TestEmergencyContactExtensions:
    """Verify that EmergencyContact has the new phone and is_primary fields."""

    def test_phone_field_exists(self, models):
        assert "phone" in models["EmergencyContact"]["fields"]

    def test_is_primary_field_default_false(self, models):
        assert models["EmergencyContact"]["fields"]["is_primary"]["default"] is False

    def test_existing_fields_preserved(self, models):
        for field in ["employee_id", "company_id", "name", "relationship"]:
            assert (
                field in models["EmergencyContact"]["fields"]
            ), f"Existing field '{field}' was removed!"

    def test_indexes_include_company(self, models):
        indexes = models["EmergencyContact"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "company" in name for name in index_names
        ), "EmergencyContact must have a company_id index"


# ---------------------------------------------------------------------------
# T300: FamilyMember Model
# ---------------------------------------------------------------------------


class TestFamilyMemberModel:
    """Verify FamilyMember model definition and fields."""

    def test_model_exists(self, models):
        assert "FamilyMember" in models

    def test_required_fields(self, models):
        fm = models["FamilyMember"]["fields"]
        assert "employee_id" in fm
        assert "company_id" in fm

    def test_default_string_fields(self, models):
        fm = models["FamilyMember"]["fields"]
        assert fm["name"]["default"] == ""
        assert fm["relationship"]["default"] == ""
        assert fm["date_of_birth"]["default"] == ""
        assert fm["gender"]["default"] == ""
        assert fm["citizenship_status"]["default"] == ""
        assert fm["nric_fin"]["default"] == ""

    def test_indexes_defined(self, models):
        indexes = models["FamilyMember"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "FamilyMember" in init_source


# ---------------------------------------------------------------------------
# T301: EmployeeDocument Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeDocumentExtensions:
    """Verify EmployeeDocument has the new fields."""

    def test_expiry_date_field_exists(self, models):
        assert "expiry_date" in models["EmployeeDocument"]["fields"]
        assert models["EmployeeDocument"]["fields"]["expiry_date"]["default"] == ""

    def test_notification_days_before_default_30(self, models):
        assert models["EmployeeDocument"]["fields"]["notification_days_before"]["default"] == 30

    def test_file_url_field_exists(self, models):
        assert "file_url" in models["EmployeeDocument"]["fields"]
        assert models["EmployeeDocument"]["fields"]["file_url"]["default"] == ""

    def test_upload_date_field_exists(self, models):
        assert "upload_date" in models["EmployeeDocument"]["fields"]
        assert models["EmployeeDocument"]["fields"]["upload_date"]["default"] == ""

    def test_notes_field_exists(self, models):
        assert "notes" in models["EmployeeDocument"]["fields"]
        assert models["EmployeeDocument"]["fields"]["notes"]["default"] == ""

    def test_existing_fields_preserved(self, models):
        for field in [
            "employee_id",
            "company_id",
            "document_type",
            "file_name",
            "file_path",
            "file_size",
            "mime_type",
            "uploaded_by",
            "description",
            "is_confidential",
            "is_active",
        ]:
            assert (
                field in models["EmployeeDocument"]["fields"]
            ), f"Existing field '{field}' was removed!"

    def test_expiry_index_exists(self, models):
        indexes = models["EmployeeDocument"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "expiry" in name for name in index_names
        ), "EmployeeDocument must have an expiry_date index"


# ---------------------------------------------------------------------------
# T302: EmployeeNote Model
# ---------------------------------------------------------------------------


class TestEmployeeNoteModel:
    """Verify EmployeeNote model definition and fields."""

    def test_model_exists(self, models):
        assert "EmployeeNote" in models

    def test_required_fields(self, models):
        fields = models["EmployeeNote"]["fields"]
        assert "employee_id" in fields
        assert "company_id" in fields

    def test_default_values(self, models):
        fields = models["EmployeeNote"]["fields"]
        assert fields["note_type"]["default"] == "general"
        assert fields["content"]["default"] == ""
        assert fields["created_by"]["default"] == 0
        assert fields["is_confidential"]["default"] is False

    def test_indexes_defined(self, models):
        indexes = models["EmployeeNote"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "EmployeeNote" in init_source


# ---------------------------------------------------------------------------
# T304: EmployeeEvent Model
# ---------------------------------------------------------------------------


class TestEmployeeEventModel:
    """Verify EmployeeEvent model (timeline) definition and fields."""

    def test_model_exists(self, models):
        assert "EmployeeEvent" in models

    def test_required_fields(self, models):
        fields = models["EmployeeEvent"]["fields"]
        assert "employee_id" in fields
        assert "company_id" in fields

    def test_default_values(self, models):
        fields = models["EmployeeEvent"]["fields"]
        assert fields["event_type"]["default"] == ""
        assert fields["description"]["default"] == ""
        assert fields["changed_by"]["default"] == 0
        assert fields["old_value"]["default"] == ""
        assert fields["new_value"]["default"] == ""
        assert fields["event_date"]["default"] == ""

    def test_indexes_defined(self, models):
        indexes = models["EmployeeEvent"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("date" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "EmployeeEvent" in init_source


# ---------------------------------------------------------------------------
# T307: EmployeeSkill Model
# ---------------------------------------------------------------------------


class TestEmployeeSkillModel:
    """Verify EmployeeSkill model definition and fields."""

    def test_model_exists(self, models):
        assert "EmployeeSkill" in models

    def test_required_fields(self, models):
        fields = models["EmployeeSkill"]["fields"]
        assert "employee_id" in fields
        assert "company_id" in fields

    def test_default_values(self, models):
        fields = models["EmployeeSkill"]["fields"]
        assert fields["skill_name"]["default"] == ""
        assert fields["proficiency_level"]["default"] == ""
        assert fields["certification_name"]["default"] == ""
        assert fields["certification_number"]["default"] == ""
        assert fields["certified_date"]["default"] == ""
        assert fields["expiry_date"]["default"] == ""
        assert fields["issuing_body"]["default"] == ""

    def test_indexes_defined(self, models):
        indexes = models["EmployeeSkill"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("expiry" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "EmployeeSkill" in init_source


# ---------------------------------------------------------------------------
# T303: CustomFieldDefinition and CustomFieldValue Models
# ---------------------------------------------------------------------------


class TestCustomFieldDefinitionModel:
    """Verify CustomFieldDefinition model definition and fields."""

    def test_model_exists(self, models):
        assert "CustomFieldDefinition" in models

    def test_required_fields(self, models):
        fields = models["CustomFieldDefinition"]["fields"]
        assert "company_id" in fields

    def test_default_values(self, models):
        fields = models["CustomFieldDefinition"]["fields"]
        assert fields["field_name"]["default"] == ""
        assert fields["field_label"]["default"] == ""
        assert fields["field_type"]["default"] == "text"
        assert fields["dropdown_options"]["default"] == ""
        assert fields["is_required"]["default"] is False
        assert fields["display_order"]["default"] == 0
        assert fields["applies_to"]["default"] == "employee"

    def test_indexes_defined(self, models):
        indexes = models["CustomFieldDefinition"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("company" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "CustomFieldDefinition" in init_source


class TestCustomFieldValueModel:
    """Verify CustomFieldValue model definition and fields."""

    def test_model_exists(self, models):
        assert "CustomFieldValue" in models

    def test_default_values(self, models):
        fields = models["CustomFieldValue"]["fields"]
        assert fields["entity_type"]["default"] == "employee"
        assert fields["entity_id"]["default"] == 0
        assert fields["field_definition_id"]["default"] == 0
        assert fields["company_id"]["default"] == 0
        assert fields["value"]["default"] == ""

    def test_indexes_defined(self, models):
        indexes = models["CustomFieldValue"]["dataflow"].get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("entity" in name for name in index_names)
        assert any("field" in name for name in index_names)

    def test_exported_from_init(self, init_source):
        assert "CustomFieldValue" in init_source


# ---------------------------------------------------------------------------
# Registration: All new models exported from __init__.py
# ---------------------------------------------------------------------------


class TestAllNewModelsExported:
    """All 6 new models must be exported from hr_advisory.models.__init__.py."""

    def test_all_new_models_in_imports(self, init_source):
        new_model_names = [
            "FamilyMember",
            "EmployeeNote",
            "EmployeeEvent",
            "EmployeeSkill",
            "CustomFieldDefinition",
            "CustomFieldValue",
        ]
        for name in new_model_names:
            assert (
                name in init_source
            ), f"Model '{name}' not found in __init__.py imports or __all__"

    def test_all_new_models_in_all_list(self, init_source):
        """New models should be in __all__ for explicit public API."""
        # Parse the __all__ list from source
        tree = ast.parse(init_source)
        all_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        if isinstance(node.value, ast.List):
                            for elt in node.value.elts:
                                if isinstance(elt, ast.Constant):
                                    all_names.add(elt.value)

        for name in [
            "FamilyMember",
            "EmployeeNote",
            "EmployeeEvent",
            "EmployeeSkill",
            "CustomFieldDefinition",
            "CustomFieldValue",
        ]:
            assert name in all_names, f"Model '{name}' not found in __all__"

    def test_existing_models_still_exported(self, init_source):
        """Adding new models must not remove existing model exports."""
        existing = [
            "Company",
            "User",
            "Employee",
            "EmergencyContact",
            "EmployeeDocument",
            "EmploymentEvent",
            "SalaryComponent",
            "PayrollRun",
            "Payslip",
            "LeaveBalance",
            "LeaveApplication",
            "Claim",
            "AttendanceRecord",
        ]
        for name in existing:
            assert name in init_source, f"Existing model '{name}' was removed from __init__.py!"


# ---------------------------------------------------------------------------
# Model field count sanity checks
# ---------------------------------------------------------------------------


class TestModelFieldCounts:
    """Verify that new models have the expected number of fields (not empty)."""

    def test_family_member_has_fields(self, models):
        assert len(models["FamilyMember"]["fields"]) >= 6

    def test_employee_note_has_fields(self, models):
        assert len(models["EmployeeNote"]["fields"]) >= 4

    def test_employee_event_has_fields(self, models):
        assert len(models["EmployeeEvent"]["fields"]) >= 6

    def test_employee_skill_has_fields(self, models):
        assert len(models["EmployeeSkill"]["fields"]) >= 7

    def test_custom_field_definition_has_fields(self, models):
        assert len(models["CustomFieldDefinition"]["fields"]) >= 6

    def test_custom_field_value_has_fields(self, models):
        assert len(models["CustomFieldValue"]["fields"]) >= 4

    def test_employee_has_new_extension_fields(self, models):
        """Employee should have gained ~30+ new fields from T298."""
        new_fields = [
            "religion",
            "phone",
            "alias",
            "photo_url",
            "salary_type",
            "hourly_rate",
            "daily_rate",
            "payment_method",
            "payment_frequency",
            "overtime_eligible",
            "working_hours_type",
            "branch_code",
            "iras_auto_inclusion",
            "tax_reference",
            "tags",
            "cpf_status",
            "amcs_enabled",
            "pmbs_enabled",
            "community_chest_amount",
            "shg_override_amount",
            "address_block",
            "address_street",
            "address_unit",
            "address_building",
            "address_postal_code",
            "organization_id",
            "branch_id",
            "cost_centre_id",
            "pay_scheme_id",
        ]
        emp_fields = models["Employee"]["fields"]
        for field in new_fields:
            assert field in emp_fields, f"T298 field '{field}' not found on Employee"
