"""Core SDK workflows for deterministic calculations and document generation."""

from hr_advisory.workflows.classification import (
    EmployeeClassificationInput,
    EmployeeClassificationResult,
    create_employee_classification_workflow,
)

__all__ = [
    "EmployeeClassificationInput",
    "EmployeeClassificationResult",
    "create_employee_classification_workflow",
]
