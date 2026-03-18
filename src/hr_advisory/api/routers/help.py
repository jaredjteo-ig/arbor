"""Help centre API router — FAQ articles and getting-started guide.

Provides real, actionable content about using the Arbor platform features
for Singapore SME HR compliance and advisory.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["help"])


# ── Response models ──────────────────────────────────────────


class HelpArticle(BaseModel):
    id: str
    title: str
    content: str
    category: str
    order: int


class HelpArticleListResponse(BaseModel):
    articles: list[HelpArticle]
    total: int
    categories: list[str]


class GettingStartedStep(BaseModel):
    step_number: int
    title: str
    description: str
    action_label: str
    action_path: str


class GettingStartedResponse(BaseModel):
    title: str
    introduction: str
    steps: list[GettingStartedStep]


# ── Content ──────────────────────────────────────────────────

_FAQ_ARTICLES: list[HelpArticle] = [
    # ── Advisory ──
    HelpArticle(
        id="faq-advisory-01",
        title="How does the HR Advisory chat work?",
        content=(
            "The Advisory chat lets you ask any HR question in plain English. "
            "Arbor searches its knowledge base of Singapore employment law -- including the Employment Act, "
            "CPF Act, WICA, PDPA, and tripartite guidelines -- then gives you a grounded answer with "
            "specific provision references. Every response includes a confidence score and risk tier "
            "(green, amber, or red) so you know when the answer is straightforward and when you should "
            "seek professional advice. You can ask follow-up questions in the same conversation."
        ),
        category="Advisory",
        order=1,
    ),
    HelpArticle(
        id="faq-advisory-02",
        title="What do the risk tiers (green, amber, red) mean?",
        content=(
            "Green means the answer is well-supported by clear statutory provisions and is "
            "straightforward to apply. Amber means there is some ambiguity -- the law may require "
            "interpretation for your specific situation, or multiple provisions interact in complex ways. "
            "Red means the topic is high-risk (e.g. dismissal, discrimination, data breach) and you should "
            "consult an employment law specialist before acting. Arbor will never give definitive legal "
            "advice on red-tier topics -- it will explain what the law says and recommend next steps."
        ),
        category="Advisory",
        order=2,
    ),
    HelpArticle(
        id="faq-advisory-03",
        title="Can I trust the answers Arbor gives?",
        content=(
            "Arbor grounds every answer in specific provisions from Singapore employment legislation and "
            "tripartite guidelines. Each response shows which provisions were cited and whether those "
            "citations were validated against the knowledge base. However, Arbor is an advisory tool, not "
            "a lawyer. For complex or high-stakes situations (terminations, claims, investigations), always "
            "verify with a qualified employment law professional. The confidence score tells you how well "
            "the answer is supported by the knowledge base."
        ),
        category="Advisory",
        order=3,
    ),
    # ── Calculators ──
    HelpArticle(
        id="faq-calc-01",
        title="How do the CPF, leave, and salary calculators work?",
        content=(
            "The Calculators page provides three tools:\n\n"
            "CPF Calculator: Enter an employee's gross salary, age, and citizenship status to see "
            "the exact employer and employee CPF contribution amounts, broken down by Ordinary, Special, "
            "and MediSave accounts. Rates are based on the latest CPF Board schedule.\n\n"
            "Leave Calculator: Enter years of service and employment type to see statutory entitlements "
            "for annual leave, sick leave, and hospitalisation leave under the Employment Act.\n\n"
            "Salary Calculator: Enter a gross salary to see the net take-home pay after CPF deductions "
            "and the total cost to the employer including employer CPF contributions."
        ),
        category="Calculators",
        order=1,
    ),
    HelpArticle(
        id="faq-calc-02",
        title="Are the calculator results legally accurate?",
        content=(
            "The calculators use the statutory rates and formulas published by CPF Board and MOM. "
            "They are accurate for standard employment situations. However, special cases (e.g. employees "
            "with multiple employers, voluntary CPF top-ups, employees on reduced pay during notice period) "
            "may have different calculations. Always cross-check with CPF Board's official calculator for "
            "payroll submissions."
        ),
        category="Calculators",
        order=2,
    ),
    # ── Compliance ──
    HelpArticle(
        id="faq-compliance-01",
        title="What does the Compliance Dashboard show?",
        content=(
            "The Compliance Dashboard checks your company's compliance posture across key regulatory "
            "domains: Employment Act, CPF, workplace safety (WSH/WICA), fair employment (TGFEP), "
            "data protection (PDPA), and foreign manpower (EFMA). For each domain, it shows whether "
            "your company has the required policies, processes, and documentation in place. "
            "The overall compliance score helps you prioritise which areas need attention first."
        ),
        category="Compliance",
        order=1,
    ),
    HelpArticle(
        id="faq-compliance-02",
        title="How does gap analysis work?",
        content=(
            "Gap analysis compares your company's current practices against the full set of regulatory "
            "requirements in each domain. It identifies specific gaps -- for example, if you employ "
            "foreign workers but have not documented your fair consideration framework, or if you lack "
            "a data breach response plan required by PDPA. Each gap is rated by severity (critical, high, "
            "medium) with a specific recommendation for how to close it."
        ),
        category="Compliance",
        order=2,
    ),
    # ── Documents ──
    HelpArticle(
        id="faq-docs-01",
        title="What document templates are available?",
        content=(
            "Arbor provides templates for common employment documents required by Singapore law, including:\n\n"
            "- Key Employment Terms (KETs) -- mandatory under EA s95 for all employees\n"
            "- Employment contracts\n"
            "- Payslip templates -- compliant with EA s88A requirements\n"
            "- Leave application forms\n"
            "- Warning letters for misconduct proceedings\n"
            "- Termination letters with proper notice provisions\n\n"
            "Each template is pre-filled with the mandatory fields and compliance notes required by law. "
            "You fill in company-specific details and the system generates a ready-to-use document."
        ),
        category="Documents",
        order=1,
    ),
    HelpArticle(
        id="faq-docs-02",
        title="Are the generated documents legally valid?",
        content=(
            "The templates include all fields and clauses required by Singapore employment legislation "
            "(Employment Act, CPF Act, etc.). They are designed to meet minimum statutory requirements. "
            "However, Arbor-generated documents are starting points -- you should review them for your "
            "specific business context and have legal counsel review any document before use in "
            "situations involving disputes, terminations, or significant contractual obligations."
        ),
        category="Documents",
        order=2,
    ),
    # ── Alerts ──
    HelpArticle(
        id="faq-alerts-01",
        title="What are regulatory alerts?",
        content=(
            "Regulatory alerts notify you when Singapore employment laws, CPF rates, or tripartite "
            "guidelines change in ways that affect your business. Each alert explains what changed, "
            "how it affects your company, what you need to do, and by when. Alerts are classified by "
            "severity (critical, high, medium, low) so you can prioritise the most urgent changes. "
            "You can view alerts in a list or calendar view to see upcoming effective dates."
        ),
        category="Alerts",
        order=1,
    ),
    # ── Emergency ──
    HelpArticle(
        id="faq-emergency-01",
        title="What is the Emergency HR hub?",
        content=(
            "The Emergency hub provides step-by-step guidance for urgent HR situations that require "
            "immediate action: TADM/ECT claims, workplace injuries, wrongful dismissal allegations, "
            "MOM inspections, discrimination complaints, and employee data breaches. Each guide tells "
            "you your immediate legal obligations, what documents to gather, the full process timeline, "
            "and when to get professional legal help. These guides are based on actual statutory "
            "requirements and regulatory processes."
        ),
        category="Emergency",
        order=1,
    ),
    HelpArticle(
        id="faq-emergency-02",
        title="When should I escalate to a specialist?",
        content=(
            "Each emergency guide lists specific situations where you should seek professional help. "
            "In general, escalate when: the financial exposure exceeds $10,000, multiple employees "
            "are involved, there are allegations of discrimination or wrongful dismissal, government "
            "authorities have initiated an investigation, or you are unsure whether your practices "
            "are compliant. The Emergency hub lets you submit an escalation request to connect with "
            "an employment law specialist."
        ),
        category="Emergency",
        order=2,
    ),
    # ── Company Profile ──
    HelpArticle(
        id="faq-profile-01",
        title="Why should I set up my company profile?",
        content=(
            "Your company profile helps Arbor give you more relevant advice. When Arbor knows your "
            "industry, headcount, and workforce composition, it can highlight regulations that "
            "specifically apply to your business. For example, companies in the food services sector "
            "have PWM obligations, companies with foreign workers have levy and quota requirements, "
            "and companies above certain headcount thresholds have additional reporting obligations. "
            "Without a profile, Arbor gives general guidance; with a profile, it can flag what "
            "specifically matters to you."
        ),
        category="Getting Started",
        order=1,
    ),
    # ── Account & Security ──
    HelpArticle(
        id="faq-account-01",
        title="How is my data protected?",
        content=(
            "Arbor uses industry-standard security practices: encrypted connections (HTTPS/TLS), "
            "JWT-based authentication with automatic token rotation, and role-based access control. "
            "Your company data and conversation history are stored securely and not shared with "
            "other users or companies. Arbor complies with PDPA data protection requirements. "
            "Advisory conversations are retained for your reference but can be deleted on request."
        ),
        category="Account & Security",
        order=1,
    ),
]

_GETTING_STARTED: GettingStartedResponse = GettingStartedResponse(
    title="Get started with Arbor",
    introduction=(
        "Arbor is your AI-powered HR compliance assistant for Singapore employment law. "
        "It helps you understand your legal obligations, calculate statutory contributions, "
        "check your compliance status, generate compliant documents, and respond to "
        "emergencies. Here is how to get the most out of it."
    ),
    steps=[
        GettingStartedStep(
            step_number=1,
            title="Set up your company profile",
            description=(
                "Tell Arbor about your company -- industry, headcount, and workforce composition. "
                "This helps Arbor highlight the specific regulations that apply to your business, "
                "such as PWM requirements for certain sectors or foreign worker levy obligations."
            ),
            action_label="Go to Company Profile",
            action_path="/profile",
        ),
        GettingStartedStep(
            step_number=2,
            title="Ask your first question",
            description=(
                "Open the Advisory chat and ask any HR question in plain English. For example: "
                "'What are my obligations when terminating an employee?' or 'How much CPF do I "
                "need to contribute for a 60-year-old employee earning $4,000?' Arbor will give "
                "you a grounded answer with specific provision references."
            ),
            action_label="Open Advisory",
            action_path="/advisory",
        ),
        GettingStartedStep(
            step_number=3,
            title="Run a compliance check",
            description=(
                "Use the Compliance Dashboard to see where your company stands across key "
                "regulatory domains. The gap analysis identifies specific areas where you may "
                "need to take action, ranked by severity."
            ),
            action_label="Check Compliance",
            action_path="/compliance",
        ),
        GettingStartedStep(
            step_number=4,
            title="Use the calculators",
            description=(
                "Calculate CPF contributions, leave entitlements, and net salary for your "
                "employees. These tools use the latest statutory rates so you can ensure your "
                "payroll is accurate."
            ),
            action_label="Open Calculators",
            action_path="/calculators",
        ),
        GettingStartedStep(
            step_number=5,
            title="Check regulatory alerts",
            description=(
                "Review the latest changes to employment law, CPF rates, and tripartite "
                "guidelines that may affect your business. Each alert tells you what changed, "
                "how it affects you, and what you need to do."
            ),
            action_label="View Alerts",
            action_path="/alerts",
        ),
        GettingStartedStep(
            step_number=6,
            title="Know where to go in an emergency",
            description=(
                "Familiarise yourself with the Emergency HR hub before you need it. It provides "
                "step-by-step guidance for urgent situations like workplace injuries, TADM claims, "
                "MOM inspections, and data breaches -- including your immediate legal obligations "
                "and deadlines."
            ),
            action_label="View Emergency Hub",
            action_path="/emergency",
        ),
    ],
)


# ── Endpoints ────────────────────────────────────────────────


@router.get("/articles", response_model=HelpArticleListResponse)
async def list_help_articles(
    category: str | None = None,
) -> HelpArticleListResponse:
    """Return FAQ articles about using Arbor.

    Optionally filter by category. No authentication required --
    help content is publicly accessible.
    """
    articles = list(_FAQ_ARTICLES)

    if category:
        articles = [a for a in articles if a.category.lower() == category.lower()]

    articles.sort(key=lambda a: (a.category, a.order))

    categories = sorted(set(a.category for a in _FAQ_ARTICLES))

    return HelpArticleListResponse(
        articles=articles,
        total=len(articles),
        categories=categories,
    )


@router.get("/getting-started", response_model=GettingStartedResponse)
async def getting_started_guide() -> GettingStartedResponse:
    """Return the getting-started guide content.

    No authentication required -- onboarding content is publicly accessible.
    """
    return _GETTING_STARTED
