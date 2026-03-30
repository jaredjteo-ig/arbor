"""Kaizen signatures for HR action agents.

The domain-specific specialist signatures have been removed — the Delegate
engine handles all advisory domains via tools. Only action agent signatures
remain here.
"""

from kaizen import InputField, OutputField, Signature


class DocumentGenerationSignature(Signature):
    """Document generation agent.

    Given a template identifier, company context, and specific parameters,
    produce a complete HR document (contract, policy, form, letter).
    """

    __intent__ = "Generate HR documents from templates"
    __guidelines__ = [
        "Use the template structure faithfully",
        "Fill all placeholders with company-specific values",
        "Flag any missing required parameters as warnings",
        "Include statutory minimum clauses where applicable",
    ]

    # Inputs
    template_id: str = InputField(
        description="Identifier of the document template to use",
    )
    company_context: str = InputField(
        description="JSON string of company profile for document personalisation",
        default="{}",
    )
    specific_params: str = InputField(
        description="JSON object of template-specific parameters (e.g. employee name, salary)",
        default="{}",
    )

    # Outputs
    generated_content: str = OutputField(
        description="The fully generated document content",
    )
    warnings: str = OutputField(
        description="JSON list of warnings about missing data or compliance notes",
    )
