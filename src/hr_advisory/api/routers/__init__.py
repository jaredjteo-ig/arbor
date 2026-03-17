"""API routers for the HR Advisory platform.

Each router handles a logical domain of endpoints. All routers are
registered with the Nexus platform via include_router().
"""

from hr_advisory.api.routers.admin import router as admin_router
from hr_advisory.api.routers.advisory import router as advisory_router
from hr_advisory.api.routers.alerts import router as alerts_router
from hr_advisory.api.routers.auth import router as auth_router
from hr_advisory.api.routers.calculator import router as calculator_router
from hr_advisory.api.routers.clients import router as clients_router
from hr_advisory.api.routers.compliance import router as compliance_router
from hr_advisory.api.routers.document import router as document_router
from hr_advisory.api.routers.employees import router as employees_router
from hr_advisory.api.routers.emergency import router as emergency_router
from hr_advisory.api.routers.help import router as help_router
from hr_advisory.api.routers.kb import router as kb_router
from hr_advisory.api.routers.learning import router as learning_router
from hr_advisory.api.routers.profile import router as profile_router
from hr_advisory.api.routers.qa import router as qa_router
from hr_advisory.api.routers.search import router as search_router
from hr_advisory.api.routers.settings import router as settings_router
from hr_advisory.api.routers.shadow import router as shadow_router

__all__ = [
    "admin_router",
    "advisory_router",
    "alerts_router",
    "auth_router",
    "calculator_router",
    "clients_router",
    "compliance_router",
    "document_router",
    "employees_router",
    "emergency_router",
    "help_router",
    "kb_router",
    "learning_router",
    "profile_router",
    "qa_router",
    "search_router",
    "settings_router",
    "shadow_router",
]
