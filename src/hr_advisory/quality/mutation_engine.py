"""Mutation engine for generating InstructionPatch candidates from QA clusters.

Takes a cluster of QA evaluations and proposes a specific addition to the
target agent's QA-LEARNED RULES section via an LLM call.

Usage:
    engine = MutationEngine()
    patch_dict = engine.propose(cluster)
    if patch_dict is not None:
        _patches[next_id] = patch_dict
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from hr_advisory.agents.config import UNCERTAINTY_DEFAULTS
from hr_advisory.config.settings import get_settings
from hr_advisory.models.qa import PatchStatus

logger = logging.getLogger(__name__)


class MutationEngine:
    """Proposes InstructionPatch candidates from QA failure clusters.

    Reads cluster data (affected_agent, failure_category, correction_texts)
    and uses an LLM to propose a specific rule addition to the agent's
    QA-LEARNED RULES section.

    All LLM configuration (provider, model) comes from get_settings().
    Never hardcodes model names.
    """

    def propose(self, cluster: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Propose an InstructionPatch from a failure cluster.

        Args:
            cluster: Dict with keys:
                - affected_agent: str
                - failure_category: str
                - count: int
                - evidence_ids: list[int]
                - correction_texts: list[str]

        Returns:
            Dict with InstructionPatch fields if successful, or None if
            the LLM call fails or returns empty output. Failures are logged
            with full context.
        """
        affected_agent = cluster.get("affected_agent")
        failure_category = cluster.get("failure_category")
        evidence_ids = cluster.get("evidence_ids", [])
        correction_texts = cluster.get("correction_texts", [])
        count = cluster.get("count", 0)

        if not affected_agent:
            raise ValueError(
                "cluster must contain 'affected_agent' -- cannot propose a patch "
                "without knowing which agent to target"
            )
        if not failure_category:
            raise ValueError(
                "cluster must contain 'failure_category' -- cannot propose a patch "
                "without knowing what type of failure to address"
            )

        prompt = self._build_prompt(
            affected_agent=affected_agent,
            failure_category=failure_category,
            correction_texts=correction_texts,
        )

        try:
            llm_response = self._call_llm(prompt)
        except Exception as exc:
            logger.error(
                "MutationEngine LLM call failed for agent=%s, category=%s: %s",
                affected_agent,
                failure_category,
                exc,
                exc_info=True,
            )
            return None

        if not llm_response or not llm_response.strip():
            logger.error(
                "MutationEngine received empty LLM response for agent=%s, category=%s. "
                "Cannot generate a patch without LLM output.",
                affected_agent,
                failure_category,
            )
            return None

        patch_dict: Dict[str, Any] = {
            "target_agent": affected_agent,
            "patch_type": "add_rule",
            "old_text": None,
            "new_text": llm_response.strip(),
            "evidence_count": count,
            "evidence_ids": evidence_ids,
            "failure_category": failure_category,
            "test_results": None,
            "status": PatchStatus.PROPOSED,
            "proposed_at": datetime.now(tz=timezone.utc).isoformat(),
            "approved_at": None,
            "deployed_at": None,
            "approved_by": None,
        }

        logger.info(
            "MutationEngine proposed patch for agent=%s, category=%s, evidence_count=%d",
            affected_agent,
            failure_category,
            count,
        )

        return patch_dict

    def _build_prompt(
        self,
        affected_agent: str,
        failure_category: str,
        correction_texts: list[str],
    ) -> str:
        """Build the LLM prompt for generating a QA-LEARNED RULE.

        Args:
            affected_agent: The target agent identifier.
            failure_category: The type of failure.
            correction_texts: Human reviewer correction texts.

        Returns:
            The formatted prompt string.
        """
        corrections_block = "\n".join(f"  - {text}" for text in correction_texts if text)

        return (
            f"You are a QA improvement specialist for an HR advisory system.\n\n"
            f"The agent '{affected_agent}' has repeatedly made the same type of error: "
            f"'{failure_category}'.\n\n"
            f"Human reviewers have provided the following corrections:\n"
            f"{corrections_block}\n\n"
            f"Based on these corrections, write a SINGLE concise rule to be added to "
            f"the agent's QA-LEARNED RULES section. The rule should:\n"
            f"1. Be specific and actionable\n"
            f"2. Reference the exact regulatory provisions if applicable\n"
            f"3. Describe what the agent should do differently\n"
            f"4. Be no longer than 3 sentences\n\n"
            f"Output ONLY the rule text, nothing else."
        )

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt.

        This method is intentionally separated for easy mocking in tests.
        In production, it uses the configured LLM provider from settings.

        Args:
            prompt: The prompt to send to the LLM.

        Returns:
            The LLM response text.

        Raises:
            Exception: If the LLM call fails for any reason.
        """
        settings = get_settings()

        # Use OpenAI if available
        if settings.openai_api_key:
            import asyncio
            from kaizen_agents.delegate import Delegate, TextDelta

            model = settings.openai_prod_model or settings.default_llm_model
            delegate = Delegate(
                model=model,
                system_prompt="You are a QA improvement specialist.",
                max_turns=1,
            )
            text_parts: list[str] = []

            async def _run() -> None:
                async for event in delegate.run(prompt):
                    if isinstance(event, TextDelta):
                        text_parts.append(event.text)

            try:
                asyncio.run(_run())
            except RuntimeError:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(lambda: asyncio.run(_run())).result(timeout=30)
            return "".join(text_parts)

        # Fallback to ollama
        if settings.ollama_model or settings.ollama_base_url:
            import urllib.request
            import json

            url = f"{settings.ollama_base_url}/api/generate"
            model = settings.ollama_model or "llama3.2"
            payload = json.dumps(
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                }
            ).encode()

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            return data.get("response", "")

        raise RuntimeError(
            "No LLM provider configured. Set OPENAI_API_KEY or OLLAMA_MODEL "
            "in your .env file. MutationEngine cannot propose patches without "
            "an LLM backend."
        )
