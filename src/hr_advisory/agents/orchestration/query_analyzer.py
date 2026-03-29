"""QueryAnalyzerAgent -- classifies HR queries by domain and risk.

This agent does NOT answer the question. It only:
  1. Identifies applicable regulatory domains
  2. Extracts entities (company name, salary amounts, dates, etc.)
  3. Assigns an initial risk tier (green / amber / red)
  4. Decides routing strategy (parallel / sequential / router)

Uses Chain-of-Thought to reason through classification before
producing the structured output.
"""

import dataclasses
import json
import logging
from typing import Any, Dict, List, Optional

from kaizen import Agent as BaseAgent  # kaizen 2.3.1+ canonical import

from hr_advisory.agents.config import QueryAnalyzerConfig, UNCERTAINTY_DEFAULTS
from hr_advisory.agents.signatures import QueryAnalyzerSignature
from hr_advisory.agents.specialists._base import _KaizenCompatMixin
from hr_advisory.workflows.guardrails import SYSTEM_PROMPT_SECURITY_FOOTER

logger = logging.getLogger(__name__)

VALID_DOMAINS = frozenset(
    [
        "employment_act",
        "cpf",
        "foreign_manpower",
        "fair_employment",
        "tax",
        "wsh",
        "pdpa",
        "compliance",
        "general",
    ]
)

VALID_RISK_TIERS = frozenset(["green", "amber", "red"])

VALID_INTENTS = frozenset(
    [
        "ADVISORY",
        "CALCULATION",
        "DOCUMENT",
        "EMERGENCY",
        "COMPLIANCE_CHECK",
        "CLARIFICATION_NEEDED",
    ]
)


class QueryAnalyzerAgent(_KaizenCompatMixin, BaseAgent):
    """Classify and route HR advisory queries.

    Extension points used:
      - _default_signature()     -> QueryAnalyzerSignature
      - _generate_system_prompt() -> CoT-style classification prompt
    """

    def __init__(
        self,
        config: Optional[QueryAnalyzerConfig] = None,
        shared_memory: Any = None,
        **kwargs,
    ):
        config = config or QueryAnalyzerConfig()
        super().__init__(
            agent_id="query_analyzer",
            config=dataclasses.asdict(config),
            signature=QueryAnalyzerSignature(),
        )
        self.shared_memory = shared_memory

    # ------------------------------------------------------------------
    # Extension points
    # ------------------------------------------------------------------

    def _default_signature(self):
        return QueryAnalyzerSignature()

    def _generate_system_prompt(self) -> str:
        from hr_advisory.workflows.singlish import SINGLISH_SYSTEM_PROMPT

        base_prompt = (
            "You are a Singapore HR regulatory query classifier.\n\n"
            "TASK: Classify the user's HR query. Do NOT answer it.\n\n"
            "If conversation history is provided, use it to understand context.\n"
            "For example, pronouns like 'they', 'it', 'that' may refer to entities\n"
            "or topics from earlier turns.\n\n"
            "STEP 1 -- Identify domains. Choose from:\n"
            "  employment_act    — Employment Act: leave, notice period, overtime, "
            "termination, salary, Part IV protections, rest days, public holidays, "
            "retrenchment. For LOCAL employees.\n"
            "  cpf              — Central Provident Fund: contribution rates, "
            "OW/AW ceilings, voluntary contributions, employer obligations.\n"
            "  foreign_manpower — Employment of Foreign Manpower Act (EFMA): "
            "Employment Pass (EP), S Pass, Work Permit, Dependant's Pass, LTVP, "
            "COMPASS framework, EP salary thresholds, foreign worker quotas (DRC), "
            "levies, Fair Consideration Framework, MOM work pass applications, "
            "employer obligations for foreign workers. ANY question about hiring "
            "or managing foreign employees belongs here.\n"
            "  fair_employment  — TAFEP/Workplace Fairness Act: discrimination, "
            "harassment, fair hiring, protected characteristics.\n"
            "  tax              — IRAS: IR8A, IR21, tax clearance, employer "
            "tax obligations.\n"
            "  wsh              — Workplace Safety and Health Act: safety incidents, "
            "risk assessments, MOM reporting, workplace injuries.\n"
            "  pdpa             — Personal Data Protection Act: employee data, "
            "consent, data breach, NRIC collection.\n"
            "  compliance       — Cross-domain compliance checks, audits.\n"
            "  general          — Only if no specific domain applies.\n\n"
            "STEP 2 -- Extract entities. Look for:\n"
            "  company_name, employee_type, salary_amount, dates, "
            "headcount, sector, nationality, pass_type\n\n"
            "STEP 3 -- Assess risk tier:\n"
            "  green  = straightforward, well-documented topic\n"
            "  amber  = involves thresholds, edge cases, or multiple acts\n"
            "  red    = potential litigation, penalty, or contradiction\n\n"
            "STEP 4 -- Decide routing:\n"
            "  router     = single specialist needed\n"
            "  parallel   = multiple independent specialists\n"
            "  sequential = specialists depend on each other\n\n"
            "STEP 5 -- Classify intent. Choose exactly one:\n"
            "  ADVISORY           = standard advisory question (route to specialists)\n"
            "  CALCULATION        = wants a number computed (salary, CPF, overtime, etc.)\n"
            "  DOCUMENT           = wants a document generated (letter, contract, template)\n"
            "  EMERGENCY          = workplace safety emergency requiring immediate action\n"
            "  COMPLIANCE_CHECK   = requesting a compliance audit or status check\n"
            "  CLARIFICATION_NEEDED = ambiguous query that could mean multiple things\n\n"
            "FEW-SHOT EXAMPLES:\n\n"
            'Query: "What are the notice period rules?"\n'
            '  -> intent: ADVISORY, domains: ["employment_act"]\n\n'
            'Query: "Calculate CPF for $5,500 salary, 35-year-old SC"\n'
            '  -> intent: CALCULATION, domains: ["cpf"]\n\n'
            'Query: "I need a resignation letter template"\n'
            '  -> intent: DOCUMENT, domains: ["employment_act"]\n\n'
            'Query: "Worker fell from scaffolding and is unconscious"\n'
            '  -> intent: EMERGENCY, domains: ["wsh"]\n\n'
            'Query: "Are we compliant with EFMA for our 50 foreign workers?"\n'
            '  -> intent: COMPLIANCE_CHECK, domains: ["foreign_manpower"]\n\n'
            'Query: "My staff wants to leave"\n'
            '  -> intent: CLARIFICATION_NEEDED, domains: ["employment_act"]\n'
            "     (ambiguous: resign or take leave?)\n\n"
            'Query: "Can I pay less CPF?"\n'
            '  -> intent: ADVISORY, domains: ["cpf"]\n'
            "     (clear advisory intent despite adversarial phrasing)\n\n"
            'Query: "How much OT should I pay my packer earning $2400?"\n'
            '  -> intent: CALCULATION, domains: ["employment_act"]\n\n'
            'Query: "Can I hire a software engineer from India on EP with $6,500/month?"\n'
            '  -> intent: ADVISORY, domains: ["foreign_manpower"]\n'
            "     (Employment Pass = EFMA, NOT Employment Act)\n\n"
            'Query: "What is the S Pass quota for my manufacturing company?"\n'
            '  -> intent: ADVISORY, domains: ["foreign_manpower"]\n\n'
            'Query: "My foreign worker permit is expiring, what do I do?"\n'
            '  -> intent: ADVISORY, domains: ["foreign_manpower"]\n\n'
            'Query: "What is the COMPASS scoring framework?"\n'
            '  -> intent: ADVISORY, domains: ["foreign_manpower"]\n\n'
            'Query: "How much levy do I pay for Work Permit holders?"\n'
            '  -> intent: CALCULATION, domains: ["foreign_manpower"]\n\n'
            "OUTPUT: Respond with a JSON object containing exactly:\n"
            '  "domains": [list of domain strings],\n'
            '  "entities": {extracted entity key-value pairs},\n'
            '  "risk_tier": "green" | "amber" | "red",\n'
            '  "routing_decision": {"strategy": "...", "specialists": [...]},\n'
            '  "intent": "ADVISORY" | "CALCULATION" | "DOCUMENT" | "EMERGENCY" '
            '| "COMPLIANCE_CHECK" | "CLARIFICATION_NEEDED"\n\n'
            "Respond ONLY with valid JSON. No explanation outside the JSON."
        )

        return f"{base_prompt}\n\n{SINGLISH_SYSTEM_PROMPT}" + SYSTEM_PROMPT_SECURITY_FOOTER

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        query_text: str,
        company_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classify a query and return structured analysis.

        Args:
            query_text: The user's HR question.
            company_context: Optional company profile dict.
            conversation_history: Optional formatted string of prior turns.

        Returns:
            Dict with keys: domains, entities, risk_tier, routing_decision,
            and optionally classification_failed and degraded flags.
        """
        classification_failed = False

        try:
            ctx_str = json.dumps(company_context) if company_context else "{}"

            result = self.run(
                query_text=query_text,
                company_context=ctx_str,
                conversation_history=conversation_history or "",
            )

            # Parse outputs (may be JSON strings from LLM)
            domains = self.extract_list(result, "domains", default=["general"])
            entities = self.extract_dict(result, "entities", default={})
            risk_tier = self.extract_str(
                result, "risk_tier", default=UNCERTAINTY_DEFAULTS["risk_tier"]
            )
            routing_decision = self.extract_dict(
                result, "routing_decision", default={"strategy": "router", "specialists": []}
            )

            # Extract intent
            intent = self.extract_str(result, "intent", default="ADVISORY").upper()

            # Validate domains
            domains = [d for d in domains if d in VALID_DOMAINS] or ["general"]

            # Validate risk tier — escalate on invalid values, never suppress
            if risk_tier not in VALID_RISK_TIERS:
                logger.warning(
                    "QueryAnalyzer returned invalid risk_tier '%s', escalating to amber",
                    risk_tier,
                )
                risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]

            # Validate intent — default to ADVISORY on invalid values
            if intent not in VALID_INTENTS:
                logger.warning(
                    "QueryAnalyzer returned invalid intent '%s', defaulting to ADVISORY",
                    intent,
                )
                intent = "ADVISORY"

        except Exception as exc:
            logger.error(
                "QueryAnalyzer classification failed for query: %.100s — %s",
                query_text,
                exc,
                exc_info=True,
            )
            classification_failed = True
            domains = ["general"]
            entities = {}
            risk_tier = UNCERTAINTY_DEFAULTS["risk_tier"]
            routing_decision = {"strategy": "router", "specialists": []}
            intent = "ADVISORY"

        analysis: Dict[str, Any] = {
            "domains": domains,
            "entities": entities,
            "risk_tier": risk_tier,
            "routing_decision": routing_decision,
            "intent": intent,
        }

        if classification_failed:
            analysis["classification_failed"] = True
            analysis["degraded"] = True

        # Write to shared memory so downstream agents can read it
        self.write_to_memory(
            content=analysis,
            tags=["query_analysis"] + domains,
            importance=0.9,
            segment="query_analysis",
        )

        return analysis
