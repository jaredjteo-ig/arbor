"""Unit tests for M39: Employee Profile Models & APIs.

Tests model field declarations, enum values, and new model definitions
for employee profile extensions (T298-T307).

Tier 1 (Unit): Fast (<1s), isolated, no external dependencies.
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://aite:aite@localhost:5432/aite")


# ---------------------------------------------------------------------------
# T298: Employee Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeFieldExtensions:
    """Verify that all new fields are declared on the Employee model."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import Employee

        self.Employee = Employee

    # --- Personal fields ---

    def test_religion_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "religion")
        assert emp.religion == ""

    def test_phone_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "phone")
        assert emp.phone == ""

    def test_alias_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "alias")
        assert emp.alias == ""

    def test_photo_url_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "photo_url")
        assert emp.photo_url == ""

    def test_nationality_field_already_exists(self):
        """nationality already exists on Employee -- verify it is still present."""
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "nationality")

    # --- Employment fields ---

    def test_salary_type_field_default_monthly(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.salary_type == "monthly"

    def test_hourly_rate_field_default_zero(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.hourly_rate == 0.0

    def test_daily_rate_field_default_zero(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.daily_rate == 0.0

    def test_payment_method_field_default_giro(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.payment_method == "giro"

    def test_payment_frequency_field_default_monthly(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.payment_frequency == "monthly"

    def test_overtime_eligible_field_default_true(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.overtime_eligible is True

    def test_working_hours_type_field_default_fixed(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.working_hours_type == "fixed"

    # --- Bank fields ---

    def test_branch_code_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "branch_code")
        assert emp.branch_code == ""

    # --- Tax fields ---

    def test_iras_auto_inclusion_field_default_true(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.iras_auto_inclusion is True

    def test_tax_reference_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "tax_reference")
        assert emp.tax_reference == ""

    # --- Tags ---

    def test_tags_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert hasattr(emp, "tags")
        assert emp.tags == ""

    # --- Statutory fields ---

    def test_cpf_status_field_default_include(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.cpf_status == "include"

    def test_amcs_enabled_field_default_false(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.amcs_enabled is False

    def test_pmbs_enabled_field_default_false(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.pmbs_enabled is False

    def test_community_chest_amount_default_zero(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.community_chest_amount == 0.0

    def test_shg_override_amount_default_zero(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.shg_override_amount == 0.0

    # --- Address (structured) ---

    def test_address_block_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.address_block == ""

    def test_address_street_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.address_street == ""

    def test_address_unit_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.address_unit == ""

    def test_address_building_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.address_building == ""

    def test_address_postal_code_field_exists(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.address_postal_code == ""

    # --- Organization FK fields ---

    def test_organization_id_optional_none(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.organization_id is None

    def test_branch_id_optional_none(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.branch_id is None

    def test_cost_centre_id_optional_none(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.cost_centre_id is None

    def test_pay_scheme_id_optional_none(self):
        emp = self.Employee(user_id=1, company_id=1)
        assert emp.pay_scheme_id is None

    # --- Existing fields not removed ---

    def test_existing_fields_preserved(self):
        """All pre-existing Employee fields must still be present."""
        emp = self.Employee(user_id=1, company_id=1)
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

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import EmergencyContact

        self.EmergencyContact = EmergencyContact

    def test_phone_field_exists(self):
        """EmergencyContact should have a 'phone' field (separate from phone_primary)."""
        ec = self.EmergencyContact(employee_id=1, company_id=1)
        assert hasattr(ec, "phone")

    def test_is_primary_field_exists(self):
        ec = self.EmergencyContact(employee_id=1, company_id=1)
        assert hasattr(ec, "is_primary")
        assert ec.is_primary is False

    def test_existing_fields_preserved(self):
        """Existing fields must still be present."""
        ec = self.EmergencyContact(employee_id=1, company_id=1)
        for field in ["employee_id", "company_id", "name", "relationship"]:
            assert hasattr(ec, field), f"Existing field '{field}' was removed!"

    def test_indexes_include_company(self):
        """Index on company_id should exist."""
        indexes = self.EmergencyContact.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "company" in name for name in index_names
        ), "EmergencyContact must have a company_id index"


# ---------------------------------------------------------------------------
# T300: FamilyMember Model
# ---------------------------------------------------------------------------


class TestFamilyMemberModel:
    """Verify FamilyMember model definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import FamilyMember

        self.FamilyMember = FamilyMember

    def test_model_exists(self):
        assert self.FamilyMember is not None

    def test_required_fields(self):
        fm = self.FamilyMember(employee_id=1, company_id=1)
        assert fm.employee_id == 1
        assert fm.company_id == 1

    def test_default_string_fields(self):
        fm = self.FamilyMember(employee_id=1, company_id=1)
        assert fm.name == ""
        assert fm.relationship == ""
        assert fm.date_of_birth == ""
        assert fm.gender == ""
        assert fm.citizenship_status == ""
        assert fm.nric_fin == ""

    def test_indexes_defined(self):
        indexes = self.FamilyMember.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "FamilyMember" in models


# ---------------------------------------------------------------------------
# T301: EmployeeDocument Model Extensions
# ---------------------------------------------------------------------------


class TestEmployeeDocumentExtensions:
    """Verify EmployeeDocument has the new fields: expiry_date, notification_days_before."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import EmployeeDocument

        self.EmployeeDocument = EmployeeDocument

    def test_expiry_date_field_exists(self):
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "expiry_date")
        assert doc.expiry_date == ""

    def test_notification_days_before_field_exists(self):
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "notification_days_before")
        assert doc.notification_days_before == 30

    def test_file_url_field_exists(self):
        """T301 specifies file_url alongside existing file_path."""
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "file_url")
        assert doc.file_url == ""

    def test_upload_date_field_exists(self):
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "upload_date")
        assert doc.upload_date == ""

    def test_notes_field_exists(self):
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
        assert hasattr(doc, "notes")
        assert doc.notes == ""

    def test_existing_fields_preserved(self):
        doc = self.EmployeeDocument(employee_id=1, company_id=1)
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
        indexes = self.EmployeeDocument.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any(
            "expiry" in name for name in index_names
        ), "EmployeeDocument must have an expiry_date index"


# ---------------------------------------------------------------------------
# T302: EmployeeNote Model
# ---------------------------------------------------------------------------


class TestEmployeeNoteModel:
    """Verify EmployeeNote model definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import EmployeeNote

        self.EmployeeNote = EmployeeNote

    def test_model_exists(self):
        assert self.EmployeeNote is not None

    def test_required_fields(self):
        note = self.EmployeeNote(employee_id=1, company_id=1)
        assert note.employee_id == 1
        assert note.company_id == 1

    def test_default_values(self):
        note = self.EmployeeNote(employee_id=1, company_id=1)
        assert note.note_type == "general"
        assert note.content == ""
        assert note.created_by == 0
        assert note.is_confidential is False

    def test_note_type_accepts_values(self):
        for note_type in ["general", "performance", "disciplinary", "confidential"]:
            note = self.EmployeeNote(employee_id=1, company_id=1, note_type=note_type)
            assert note.note_type == note_type

    def test_indexes_defined(self):
        indexes = self.EmployeeNote.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "EmployeeNote" in models


# ---------------------------------------------------------------------------
# T304: EmployeeEvent Model
# ---------------------------------------------------------------------------


class TestEmployeeEventModel:
    """Verify EmployeeEvent model (timeline) definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import EmployeeEvent

        self.EmployeeEvent = EmployeeEvent

    def test_model_exists(self):
        assert self.EmployeeEvent is not None

    def test_required_fields(self):
        event = self.EmployeeEvent(employee_id=1, company_id=1)
        assert event.employee_id == 1
        assert event.company_id == 1

    def test_default_values(self):
        event = self.EmployeeEvent(employee_id=1, company_id=1)
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
            event = self.EmployeeEvent(employee_id=1, company_id=1, event_type=event_type)
            assert event.event_type == event_type

    def test_indexes_defined(self):
        indexes = self.EmployeeEvent.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("date" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "EmployeeEvent" in models


# ---------------------------------------------------------------------------
# T307: EmployeeSkill Model
# ---------------------------------------------------------------------------


class TestEmployeeSkillModel:
    """Verify EmployeeSkill model definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import EmployeeSkill

        self.EmployeeSkill = EmployeeSkill

    def test_model_exists(self):
        assert self.EmployeeSkill is not None

    def test_required_fields(self):
        skill = self.EmployeeSkill(employee_id=1, company_id=1)
        assert skill.employee_id == 1
        assert skill.company_id == 1

    def test_default_values(self):
        skill = self.EmployeeSkill(employee_id=1, company_id=1)
        assert skill.skill_name == ""
        assert skill.proficiency_level == ""
        assert skill.certification_name == ""
        assert skill.certification_number == ""
        assert skill.certified_date == ""
        assert skill.expiry_date == ""
        assert skill.issuing_body == ""

    def test_proficiency_levels_accepted(self):
        for level in ["basic", "intermediate", "advanced", "expert"]:
            skill = self.EmployeeSkill(employee_id=1, company_id=1, proficiency_level=level)
            assert skill.proficiency_level == level

    def test_indexes_defined(self):
        indexes = self.EmployeeSkill.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("employee" in name for name in index_names)
        assert any("company" in name for name in index_names)
        assert any("expiry" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "EmployeeSkill" in models


# ---------------------------------------------------------------------------
# T303: CustomFieldDefinition and CustomFieldValue Models
# ---------------------------------------------------------------------------


class TestCustomFieldDefinitionModel:
    """Verify CustomFieldDefinition model definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import CustomFieldDefinition

        self.CustomFieldDefinition = CustomFieldDefinition

    def test_model_exists(self):
        assert self.CustomFieldDefinition is not None

    def test_required_fields(self):
        cfd = self.CustomFieldDefinition(company_id=1)
        assert cfd.company_id == 1

    def test_default_values(self):
        cfd = self.CustomFieldDefinition(company_id=1)
        assert cfd.field_name == ""
        assert cfd.field_label == ""
        assert cfd.field_type == "text"
        assert cfd.dropdown_options == ""
        assert cfd.is_required is False
        assert cfd.display_order == 0
        assert cfd.applies_to == "employee"

    def test_field_type_accepts_known_values(self):
        for ft in ["text", "number", "date", "dropdown", "checkbox"]:
            cfd = self.CustomFieldDefinition(company_id=1, field_type=ft)
            assert cfd.field_type == ft

    def test_indexes_defined(self):
        indexes = self.CustomFieldDefinition.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("company" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "CustomFieldDefinition" in models


class TestCustomFieldValueModel:
    """Verify CustomFieldValue model definition and fields."""

    @pytest.fixture(autouse=True)
    def _load_model(self):
        from hr_advisory.models.company_user import CustomFieldValue

        self.CustomFieldValue = CustomFieldValue

    def test_model_exists(self):
        assert self.CustomFieldValue is not None

    def test_default_values(self):
        cfv = self.CustomFieldValue()
        assert cfv.entity_type == "employee"
        assert cfv.entity_id == 0
        assert cfv.field_definition_id == 0
        assert cfv.company_id == 0
        assert cfv.value == ""

    def test_indexes_defined(self):
        indexes = self.CustomFieldValue.__dataflow__.get("indexes", [])
        index_names = [idx["name"] for idx in indexes]
        assert any("entity" in name for name in index_names)
        assert any("field" in name for name in index_names)

    def test_registered_in_dataflow(self):
        from hr_advisory.models import db

        models = db.get_models()
        assert "CustomFieldValue" in models


# ---------------------------------------------------------------------------
# Registration: All new models discoverable via db.get_models()
# ---------------------------------------------------------------------------


class TestAllNewModelsRegistered:
    """All 7 new models plus enums must be importable from hr_advisory.models."""

    def test_new_models_importable_from_package(self):
        from hr_advisory.models import (
            FamilyMember,
            EmployeeNote,
            EmployeeEvent,
            EmployeeSkill,
            CustomFieldDefinition,
            CustomFieldValue,
        )

        assert FamilyMember is not None
        assert EmployeeNote is not None
        assert EmployeeEvent is not None
        assert EmployeeSkill is not None
        assert CustomFieldDefinition is not None
        assert CustomFieldValue is not None

    def test_all_new_models_in_dataflow_registry(self):
        from hr_advisory.models import db

        models = db.get_models()
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
        from hr_advisory.models import db

        models = db.get_models()
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
            assert name in models, f"Existing model '{name}' was lost during M39 changes!"


# ---------------------------------------------------------------------------
# Enum / string constant coverage for new fields
# ---------------------------------------------------------------------------


class TestNewFieldEnumValues:
    """Verify enum-like string fields accept expected values."""

    def test_religion_values(self):
        from hr_advisory.models.company_user import Employee

        valid = ["buddhist", "christian", "hindu", "islam", "sikh", "taoist", "none", "other"]
        for val in valid:
            emp = Employee(user_id=1, company_id=1, religion=val)
            assert emp.religion == val

    def test_salary_type_values(self):
        from hr_advisory.models.company_user import Employee

        for val in ["monthly", "daily", "hourly"]:
            emp = Employee(user_id=1, company_id=1, salary_type=val)
            assert emp.salary_type == val

    def test_payment_method_values(self):
        from hr_advisory.models.company_user import Employee

        for val in ["giro", "fast", "cheque", "cash"]:
            emp = Employee(user_id=1, company_id=1, payment_method=val)
            assert emp.payment_method == val

    def test_cpf_status_values(self):
        from hr_advisory.models.company_user import Employee

        for val in ["include", "exclude", "full_employer"]:
            emp = Employee(user_id=1, company_id=1, cpf_status=val)
            assert emp.cpf_status == val

    def test_working_hours_type_values(self):
        from hr_advisory.models.company_user import Employee

        for val in ["fixed", "shift", "flexible"]:
            emp = Employee(user_id=1, company_id=1, working_hours_type=val)
            assert emp.working_hours_type == val
