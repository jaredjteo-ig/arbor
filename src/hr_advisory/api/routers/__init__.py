"""API routers for the HR Advisory platform.

Each router handles a logical domain of endpoints. All routers are
registered with the Nexus platform via include_router().
"""

from hr_advisory.api.routers.admin import router as admin_router
from hr_advisory.api.routers.advisory import router as advisory_router
from hr_advisory.api.routers.alerts import router as alerts_router
from hr_advisory.api.routers.appraisals import router as appraisals_router
from hr_advisory.api.routers.banking import router as banking_router
from hr_advisory.api.routers.approval_groups import router as approval_groups_router
from hr_advisory.api.routers.auth import router as auth_router
from hr_advisory.api.routers.calculator import router as calculator_router
from hr_advisory.api.routers.company import router as company_router
from hr_advisory.api.routers.compliance import router as compliance_router
from hr_advisory.api.routers.document import router as document_router
from hr_advisory.api.routers.employees import router as employees_router
from hr_advisory.api.routers.emergency import router as emergency_router
from hr_advisory.api.routers.help import router as help_router
from hr_advisory.api.routers.inventory import router as inventory_router
from hr_advisory.api.routers.kb import router as kb_router
from hr_advisory.api.routers.onboarding import router as onboarding_router
from hr_advisory.api.routers.learning import router as learning_router
from hr_advisory.api.routers.leave import router as leave_router
from hr_advisory.api.routers.llm_config import router as llm_config_router
from hr_advisory.api.routers.llm_config import user_llm_router
from hr_advisory.api.routers.payroll import router as payroll_router
from hr_advisory.api.routers.policies import router as policies_router
from hr_advisory.api.routers.profile import router as profile_router
from hr_advisory.api.routers.projects import router as projects_router
from hr_advisory.api.routers.push import router as push_router
from hr_advisory.api.routers.qa import router as qa_router
from hr_advisory.api.routers.recruitment import router as recruitment_router
from hr_advisory.api.routers.reports import router as reports_router
from hr_advisory.api.routers.search import router as search_router
from hr_advisory.api.routers.settings import router as settings_router
from hr_advisory.api.routers.shadow import router as shadow_router
from hr_advisory.api.routers.shifts import router as shifts_router
from hr_advisory.api.routers.claims import router as claims_router
from hr_advisory.api.routers.attendance import router as attendance_router
from hr_advisory.api.routers.integrations import router as integrations_router

__all__ = [
    "admin_router",
    "advisory_router",
    "alerts_router",
    "appraisals_router",
    "banking_router",
    "approval_groups_router",
    "attendance_router",
    "auth_router",
    "calculator_router",
    "claims_router",
    "company_router",
    "compliance_router",
    "document_router",
    "employees_router",
    "emergency_router",
    "help_router",
    "inventory_router",
    "kb_router",
    "onboarding_router",
    "learning_router",
    "leave_router",
    "llm_config_router",
    "user_llm_router",
    "payroll_router",
    "policies_router",
    "profile_router",
    "projects_router",
    "push_router",
    "qa_router",
    "recruitment_router",
    "reports_router",
    "search_router",
    "settings_router",
    "shadow_router",
    "shifts_router",
    "integrations_router",
]
