"""Employee Classification Engine -- deterministic Singapore employment classification.

Provides data classes for input/output and a workflow factory that builds
a Kailash Core SDK workflow for classifying employees under Singapore
employment legislation (Employment Act, CPF, work pass validation, leave).
"""

from hr_advisory.workflows.classification.data_classes import (
    EmployeeClassificationInput,
    EmployeeClassificationResult,
)
from hr_advisory.workflows.classification.employee_classifier import (
    create_employee_classification_workflow,
)

__all__ = [
    "EmployeeClassificationInput",
    "EmployeeClassificationResult",
    "create_employee_classification_workflow",
]
