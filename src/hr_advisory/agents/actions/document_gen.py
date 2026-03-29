"""DocumentGenerationAgent -- generates HR documents from templates.

Generates:
  - Employment contracts (full-time, part-time, fixed-term)
  - Company HR policies (leave, grievance, anti-harassment)
  - MOM-required forms and notices
  - Termination and warning letters

Uses the LLM to fill templates with company-specific values and ensure
statutory minimum clauses are present.
"""

import json
import logging
from typing import Any, Dict, Optional

from kaizen import Agent as BaseAgent  # kaizen 2.3.1+ canonical import

from hr_advisory.agents.config import DocumentGenerationConfig
from hr_advisory.agents.specialists._base import _KaizenCompatMixin
from hr_advisory.agents.specialists.signatures import DocumentGenerationSignature

logger = logging.getLogger(__name__)


class DocumentGenerationAgent(_KaizenCompatMixin, BaseAgent):
    """Generate HR documents from templates.

    Extension points used:
      - _default_signature()      -> DocumentGenerationSignature
      - _generate_system_prompt() -> document generation prompt
    """

    domain = "document_generation"
    domain_label = "Document Generation"

    def __init__(
        self,
        config: Optional[DocumentGenerationConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        import os

        config = config or DocumentGenerationConfig()
        model = os.environ.get("OPENAI_PROD_MODEL", os.environ.get("DEFAULT_LLM_MODEL", ""))
        super().__init__(model=model, system_prompt=self._generate_system_prompt())
        self.agent_id = "document_generation"
        self.shared_memory = shared_memory
        self._docgen_config = config

    def _default_signature(self):
        return DocumentGenerationSignature()

    def _generate_system_prompt(self) -> str:
        return (
            "You are an HR document generation specialist for Singapore SMEs.\n\n"
            "TASK: Generate a complete HR document based on the template and "
            "company-specific parameters provided.\n\n"
            "RULES:\n"
            "1. Follow the template structure faithfully\n"
            "2. Fill all placeholders with company-specific values\n"
            "3. Include statutory minimum clauses required by Singapore law\n"
            "4. Flag missing required parameters as warnings\n"
            "5. Use plain language suitable for SME owners\n"
            "6. Include section references where statutory minimums apply\n\n"
            "OUTPUT: Respond with a JSON object containing:\n"
            '  "generated_content": "the complete document text",\n'
            '  "warnings": ["warning 1", "warning 2", ...]\n\n'
            "Respond ONLY with valid JSON."
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        template_id: str,
        company_context: Optional[Dict[str, Any]] = None,
        specific_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a document from a template.

        Args:
            template_id: Identifier of the document template.
            company_context: Company profile for personalisation.
            specific_params: Template-specific parameters (employee name, salary, etc.).

        Returns:
            Dict with keys: generated_content, warnings.
        """
        ctx_str = json.dumps(company_context) if company_context else "{}"
        params_str = json.dumps(specific_params) if specific_params else "{}"

        result = self.run(
            template_id=template_id,
            company_context=ctx_str,
            specific_params=params_str,
        )

        generated_content = self.extract_str(
            result,
            "generated_content",
            default="Unable to generate document.",
        )
        warnings = self.extract_list(result, "warnings", default=[])

        output = {
            "template_id": template_id,
            "generated_content": generated_content,
            "warnings": warnings,
        }

        self.write_to_memory(
            content={"template_id": template_id, "status": "generated"},
            tags=["document_generation", template_id],
            importance=0.7,
            segment="action_output",
        )

        return output
