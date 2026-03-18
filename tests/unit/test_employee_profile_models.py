"""Unit tests for M39: Employee Profile Models & APIs.

Tests model field declarations, enum values, and new model definitions
for employee profile extensions (T298-T307).

Tier 1 (Unit): Fast (<1s), isolated, no external dependencies.

NOTE: These tests require a DATABASE_URL to be set and the database to be
reachable, because DataFlow models are registered at import time via the
@db.model decorator which requires a live connection. Tests that need
db.get_models() are marked as integration-tier and skipped if the DB
is not available. Field-level tests inspect the class annotations and
__dataflow__ dict directly, without requiring a DB connection.
"""

import os
import sys
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Mock DataFlow to avoid requiring a live database for unit tests.
# The @db.model decorator must still function: it should store __dataflow__
# on the class and register it. We mock DataFlow so that `model()` acts
# as a passthrough decorator that preserves the class and its __dataflow__.
# ---------------------------------------------------------------------------

_registered_models = {}


def _mock_model_decorator(cls):
    """Simulate @db.model: keep __dataflow__ and register the class."""
    _registered_models[cls.__name__] = cls
    return cls


def _mock_get_models():
    return dict(_registered_models)


# Create a mock DataFlow instance
_mock_db = MagicMock()
_mock_db.model = _mock_model_decorator
_mock_db.get_models = _mock_get_models

# Patch the database module BEFORE any model imports
# This replaces hr_advisory.models.database.db with our mock
_db_module = MagicMock()
_db_module.db = _mock_db
sys.modules.setdefault("hr_advisory.models.database", _db_module)

# Patch hr_advisory.models.enums if not importable (it may depend on database)
try:
    from hr_advisory.models.enums import RiskTier  # noqa: F401
except Exception:
    _enums_module = MagicMock()
    _enums_module.RiskTier = MagicMock()
    _enums_module.RiskTier.GREEN = MagicMock(value="green")
    sys.modules["hr_advisory.models.enums"] = _enums_module

# Now we can safely set the db reference in company_user's import chain
import hr_advisory.models.database  # noqa: E402

hr_advisory.models.database.db = _mock_db

# Clear registered models before importing (in case of re-runs)
_registered_models.clear()

# Import the models module -- this triggers @db.model decorators
from hr_advisory.models.company_user import (  # noqa: E402
    Employee,
    EmergencyContact,
    EmployeeDocument,
    ConfirmationStatus,
    EmploymentType,
    ImmigrationStatus,
)

# Import new models (these should exist after implementation)
from hr_advisory.models.company_user import (  # noqa: E402
    FamilyMember,
    EmployeeNote,
    EmployeeEvent,
    EmployeeSkill,
    CustomFieldDefinition,
    CustomFieldValue,
)


# ---------------------------------------------------------------------------
# T298: Employee Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeFieldExtensions:
    """Verify that all new fields are declared on the Employee model."""

    # --- Personal fields ---

    def test_religion_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "religion")
        assert emp.religion == ""

    def test_phone_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "phone")
        assert emp.phone == ""

    def test_alias_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "alias")
        assert emp.alias == ""

    def test_photo_url_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "photo_url")
        assert emp.photo_url == ""

    def test_nationality_field_already_exists(self):
        """nationality already exists on Employee -- verify it is still present."""
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "nationality")

    # --- Employment fields ---

    def test_salary_type_field_default_monthly(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.salary_type == "monthly"

    def test_hourly_rate_field_default_zero(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.hourly_rate == 0.0

    def test_daily_rate_field_default_zero(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.daily_rate == 0.0

    def test_payment_method_field_default_giro(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.payment_method == "giro"

    def test_payment_frequency_field_default_monthly(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.payment_frequency == "monthly"

    def test_overtime_eligible_field_default_true(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.overtime_eligible is True

    def test_working_hours_type_field_default_fixed(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.working_hours_type == "fixed"

    # --- Bank fields ---

    def test_branch_code_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "branch_code")
        assert emp.branch_code == ""

    # --- Tax fields ---

    def test_iras_auto_inclusion_field_default_true(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.iras_auto_inclusion is True

    def test_tax_reference_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "tax_reference")
        assert emp.tax_reference == ""

    # --- Tags ---

    def test_tags_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert hasattr(emp, "tags")
        assert emp.tags == ""

    # --- Statutory fields ---

    def test_cpf_status_field_default_include(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.cpf_status == "include"

    def test_amcs_enabled_field_default_false(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.amcs_enabled is False

    def test_pmbs_enabled_field_default_false(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.pmbs_enabled is False

    def test_community_chest_amount_default_zero(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.community_chest_amount == 0.0

    def test_shg_override_amount_default_zero(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.shg_override_amount == 0.0

    # --- Address (structured) ---

    def test_address_block_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.address_block == ""

    def test_address_street_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.address_street == ""

    def test_address_unit_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.address_unit == ""

    def test_address_building_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.address_building == ""

    def test_address_postal_code_field_exists(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.address_postal_code == ""

    # --- Organization FK fields ---

    def test_organization_id_optional_none(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.organization_id is None

    def test_branch_id_optional_none(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.branch_id is None

    def test_cost_centre_id_optional_none(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.cost_centre_id is None

    def test_pay_scheme_id_optional_none(self):
        emp = Employee(user_id=1, company_id=1)
        assert emp.pay_scheme_id is None

    # --- Existing fields not removed ---

    def test_existing_fields_preserved(self):
        """All pre-existing Employee fields must still be present."""
        emp = Employee(user_id=1, company_id=1)
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
        for field in existing_fields:
            assert hasattr(emp, field), f"Existing field '{field}' was removed!"


# ---------------------------------------------------------------------------
# T299: EmergencyContact Model Extensions
# ---------------------------------------------------------------------------


class TestEmergencyContactExtensions:
    """Verify that EmergencyContact has the new phone and is_primary fields."""

    def test_phone_field_exists(self):
        """EmergencyContact should have a 'phone' field (separate from phone_primary)."""
        ec = EmergencyContact(employee_id=1, company_id=1)
        assert hasattr(ec, "phone")

    def test_is_primary_field_exists(self):
        ec = EmergencyContact(employee_id=1, company_id=1)
        assert hasattr(ec, "is_primary")
        assert ec.is_primary is False

    def test_existing_fields_preserved(self):
        """Existing fields must still be present."""
        ec = EmergencyContact(employee_id=1, company_id=1)
        for field in ["employee_id", "company_id", "name", "relationship"]:
            assert hasattr(ec, field), f"Existing field '{field}' was removed!"

    def test_indexes_include_company(self):
        """Index on company_id should exist."""
        indexes = EmergencyContact.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "company" in name for name in index_names
        ), "EmergencyContact must have a company_id index"


# ---------------------------------------------------------------------------
# T300: FamilyMember Model
# ---------------------------------------------------------------------------


class TestFamilyMemberModel:
    """Verify FamilyMember model definition and fields."""

    def test_model_exists(self):
        assert FamilyMember is not None

    def test_required_fields(self):
        fm = FamilyMember(employee_id=1, company_id=1)
        assert fm.employee_id == 1
        assert fm.company_id == 1

    def test_default_string_fields(self):
        fm = FamilyMember(employee_id=1, company_id=1)
        assert fm.name == ""
        assert fm.relationship == ""
        assert fm.date_of_birth == ""
        assert fm.gender == ""
        assert fm.citizenship_status == ""
        assert fm.nric_fin == ""

    def test_indexes_defined(self):
        indexes = FamilyMember.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "FamilyMember" in models


# ---------------------------------------------------------------------------
# T301: EmployeeDocument Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeDocumentExtensions:
    """Verify EmployeeDocument has the new fields: expiry_date, notification_days_before."""

    def test_expiry_date_field_exists(self):
        doc = EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "expiry_date")
        assert doc.expiry_date == ""

    def test_notification_days_before_field_exists(self):
        doc = EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "notification_days_before")
        assert doc.notification_days_before == 30

    def test_file_url_field_exists(self):
        """T301 specifies file_url alongside existing file_path."""
        doc = EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "file_url")
        assert doc.file_url == ""

    def test_upload_date_field_exists(self):
        doc = EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "upload_date")
        assert doc.upload_date == ""

    def test_notes_field_exists(self):
        doc = EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "notes")
        assert doc.notes == ""

    def test_existing_fields_preserved(self):
        doc = EmployeeDocument(employee_id=1, company_id=1)
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
            assert hasattr(doc, field), f"Existing field '{field}' was removed!"

    def test_expiry_index_exists(self):
        indexes = EmployeeDocument.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "expiry" in name for name in index_names
        ), "EmployeeDocument must have an expiry_date index"


# ---------------------------------------------------------------------------
# T302: EmployeeNote Model
# ---------------------------------------------------------------------------


class TestEmployeeNoteModel:
    """Verify EmployeeNote model definition and fields."""

    def test_model_exists(self):
        assert EmployeeNote is not None

    def test_required_fields(self):
        note = EmployeeNote(employee_id=1, company_id=1)
        assert note.employee_id == 1
        assert note.company_id == 1

    def test_default_values(self):
        note = EmployeeNote(employee_id=1, company_id=1)
        assert note.note_type == "general"
        assert note.content == ""
        assert note.created_by == 0
        assert note.is_confidential is False

    def test_note_type_accepts_values(self):
        for note_type in ["general", "performance", "disciplinary", "confidential"]:
            note = EmployeeNote(employee_id=1, company_id=1, note_type=note_type)
            assert note.note_type == note_type

    def test_indexes_defined(self):
        indexes = EmployeeNote.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "EmployeeNote" in models


# ---------------------------------------------------------------------------
# T304: EmployeeEvent Model
# ---------------------------------------------------------------------------


class TestEmployeeEventModel:
    """Verify EmployeeEvent model (timeline) definition and fields."""

    def test_model_exists(self):
        assert EmployeeEvent is not None

    def test_required_fields(self):
        event = EmployeeEvent(employee_id=1, company_id=1)
        assert event.employee_id == 1
        assert event.company_id == 1

    def test_default_values(self):
        event = EmployeeEvent(employee_id=1, company_id=1)
        assert event.event_type == ""
        assert event.description == ""
        assert event.changed_by == 0
        assert event.old_value == ""
        assert event.new_value == ""
        assert event.event_date == ""

    def test_event_type_accepts_known_values(self):
        valid_types = [
            "created",
            "profile_updated",
            "salary_changed",
            "promoted",
            "department_changed",
            "probation_confirmed",
            "leave_approved",
            "terminated",
            "document_uploaded",
            "note_added",
        ]
        for event_type in valid_types:
            event = EmployeeEvent(employee_id=1, company_id=1, event_type=event_type)
            assert event.event_type == event_type

    def test_indexes_defined(self):
        indexes = EmployeeEvent.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("date" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "EmployeeEvent" in models


# ---------------------------------------------------------------------------
# T307: EmployeeSkill Model
# ---------------------------------------------------------------------------


class TestEmployeeSkillModel:
    """Verify EmployeeSkill model definition and fields."""

    def test_model_exists(self):
        assert EmployeeSkill is not None

    def test_required_fields(self):
        skill = EmployeeSkill(employee_id=1, company_id=1)
        assert skill.employee_id == 1
        assert skill.company_id == 1

    def test_default_values(self):
        skill = EmployeeSkill(employee_id=1, company_id=1)
        assert skill.skill_name == ""
        assert skill.proficiency_level == ""
        assert skill.certification_name == ""
        assert skill.certification_number == ""
        assert skill.certified_date == ""
        assert skill.expiry_date == ""
        assert skill.issuing_body == ""

    def test_proficiency_levels_accepted(self):
        for level in ["basic", "intermediate", "advanced", "expert"]:
            skill = EmployeeSkill(employee_id=1, company_id=1, proficiency_level=level)
            assert skill.proficiency_level == level

    def test_indexes_defined(self):
        indexes = EmployeeSkill.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("expiry" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "EmployeeSkill" in models


# ---------------------------------------------------------------------------
# T303: CustomFieldDefinition and CustomFieldValue Models
# ---------------------------------------------------------------------------


class TestCustomFieldDefinitionModel:
    """Verify CustomFieldDefinition model definition and fields."""

    def test_model_exists(self):
        assert CustomFieldDefinition is not None

    def test_required_fields(self):
        cfd = CustomFieldDefinition(company_id=1)
        assert cfd.company_id == 1

    def test_default_values(self):
        cfd = CustomFieldDefinition(company_id=1)
        assert cfd.field_name == ""
        assert cfd.field_label == ""
        assert cfd.field_type == "text"
        assert cfd.dropdown_options == ""
        assert cfd.is_required is False
        assert cfd.display_order == 0
        assert cfd.applies_to == "employee"

    def test_field_type_accepts_known_values(self):
        for ft in ["text", "number", "date", "dropdown", "checkbox"]:
            cfd = CustomFieldDefinition(company_id=1, field_type=ft)
            assert cfd.field_type == ft

    def test_indexes_defined(self):
        indexes = CustomFieldDefinition.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("company" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "CustomFieldDefinition" in models


class TestCustomFieldValueModel:
    """Verify CustomFieldValue model definition and fields."""

    def test_model_exists(self):
        assert CustomFieldValue is not None

    def test_default_values(self):
        cfv = CustomFieldValue()
        assert cfv.entity_type == "employee"
        assert cfv.entity_id == 0
        assert cfv.field_definition_id == 0
        assert cfv.company_id == 0
        assert cfv.value == ""

    def test_indexes_defined(self):
        indexes = CustomFieldValue.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("entity" in name for name in index_names)
        assert any("field" in name for name in index_names)

    def test_registered_in_mock_dataflow(self):
        models = _mock_get_models()
        assert "CustomFieldValue" in models


# ---------------------------------------------------------------------------
# Registration: All new models discoverable via mock DataFlow registry
# ---------------------------------------------------------------------------


class TestAllNewModelsRegistered:
    """All 6 new models must be importable and registered."""

    def test_new_models_importable(self):
        assert FamilyMember is not None
        assert EmployeeNote is not None
        assert EmployeeEvent is not None
        assert EmployeeSkill is not None
        assert CustomFieldDefinition is not None
        assert CustomFieldValue is not None

    def test_all_new_models_in_registry(self):
        models = _mock_get_models()
        new_model_names = [
            "FamilyMember",
            "EmployeeNote",
            "EmployeeEvent",
            "EmployeeSkill",
            "CustomFieldDefinition",
            "CustomFieldValue",
        ]
        for name in new_model_names:
            assert name in models, f"Model '{name}' not registered in DataFlow"

    def test_existing_models_still_registered(self):
        """Adding new models must not break existing model registration."""
        models = _mock_get_models()
        existing = [
            "Employee",
            "EmergencyContact",
            "EmployeeDocument",
        ]
        for name in existing:
            assert name in models, f"Existing model '{name}' was lost during M39 changes!"


# ---------------------------------------------------------------------------
# Enum / string constant coverage for new fields
# ---------------------------------------------------------------------------


class TestNewFieldEnumValues:
    """Verify enum-like string fields accept expected values."""

    def test_religion_values(self):
        valid = ["buddhist", "christian", "hindu", "islam", "sikh", "taoist", "none", "other"]
        for val in valid:
            emp = Employee(user_id=1, company_id=1, religion=val)
            assert emp.religion == val

    def test_salary_type_values(self):
        for val in ["monthly", "daily", "hourly"]:
            emp = Employee(user_id=1, company_id=1, salary_type=val)
            assert emp.salary_type == val

    def test_payment_method_values(self):
        for val in ["giro", "fast", "cheque", "cash"]:
            emp = Employee(user_id=1, company_id=1, payment_method=val)
            assert emp.payment_method == val

    def test_cpf_status_values(self):
        for val in ["include", "exclude", "full_employer"]:
            emp = Employee(user_id=1, company_id=1, cpf_status=val)
            assert emp.cpf_status == val

    def test_working_hours_type_values(self):
        for val in ["fixed", "shift", "flexible"]:
            emp = Employee(user_id=1, company_id=1, working_hours_type=val)
            assert emp.working_hours_type == val
