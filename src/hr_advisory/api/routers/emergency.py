"""Emergency HR response API router.

Exposes structured emergency response guides for crisis situations.
Data is sourced from the emergency_responses workflow module.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.workflows.emergency_responses import (
    EMERGENCY_RESPONSES,
    EmergencyResponse,
    get_emergency_response,
    list_emergency_topics,
)


router = APIRouter(tags=["emergency"])


# ── Response models ──────────────────────────────────────────


class EmergencyStepResponse(BaseModel):
    step_number: int
    action: str
    deadline: str
    detail: str


class EmergencyScenarioResponse(BaseModel):
    topic_id: str
    title: str
    icon: str
    description: str
    immediate_obligations: list[EmergencyStepResponse]
    documents_needed: list[str]
    process_steps: list[EmergencyStepResponse]
    when_to_get_help: list[str]
    key_provisions: list[str]


class EmergencyTopicSummary(BaseModel):
    topic_id: str
    title: str
    icon: str
    description: str


class EmergencyScenarioListResponse(BaseModel):
    scenarios: list[EmergencyScenarioResponse]
    total: int


class EscalationRequest(BaseModel):
    topic_id: str
    description: str
    company_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    urgency: str = "high"


class EscalationResponse(BaseModel):
    escalation_id: str
    topic_id: str
    status: str
    message: str


# ── Helpers ──────────────────────────────────────────────────

_escalation_counter = 0


def _to_scenario_response(er: EmergencyResponse) -> EmergencyScenarioResponse:
    """Convert a dataclass EmergencyResponse to a Pydantic response model."""
    return EmergencyScenarioResponse(
        topic_id=er.topic_id,
        title=er.title,
        icon=er.icon,
        description=er.description,
        immediate_obligations=[
            EmergencyStepResponse(
                step_number=s.step_number,
                action=s.action,
                deadline=s.deadline,
                detail=s.detail,
            )
            for s in er.immediate_obligations
        ],
        documents_needed=list(er.documents_needed),
        process_steps=[
            EmergencyStepResponse(
                step_number=s.step_number,
                action=s.action,
                deadline=s.deadline,
                detail=s.detail,
            )
            for s in er.process_steps
        ],
        when_to_get_help=list(er.when_to_get_help),
        key_provisions=list(er.key_provisions),
    )


# ── Endpoints ────────────────────────────────────────────────


@router.get("/scenarios", response_model=EmergencyScenarioListResponse)
async def list_emergency_scenarios(
    current_user: dict = Depends(get_current_user),
) -> EmergencyScenarioListResponse:
    """List all available emergency scenarios with full response content.

    Returns the complete emergency response guide for each scenario,
    including immediate obligations, documents needed, process steps,
    and when to seek professional help.
    """
    scenarios = [_to_scenario_response(er) for er in EMERGENCY_RESPONSES.values()]
    return EmergencyScenarioListResponse(
        scenarios=scenarios,
        total=len(scenarios),
    )


@router.get("/scenarios/{topic_id}", response_model=EmergencyScenarioResponse)
async def get_emergency_scenario(
    topic_id: str,
    current_user: dict = Depends(get_current_user),
) -> EmergencyScenarioResponse:
    """Get a specific emergency scenario by topic ID."""
    er = get_emergency_response(topic_id)
    if er is None:
        raise HTTPException(status_code=404, detail=f"Emergency scenario '{topic_id}' not found")
    return _to_scenario_response(er)


@router.get("/contacts")
async def list_emergency_contacts(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return emergency contact information for HR crisis situations.

    Provides specialist contact details for each emergency topic,
    plus general emergency contacts (MOM, TADM, WSHC helplines).
    """
    general_contacts = [
        {
            "name": "Ministry of Manpower (MOM)",
            "phone": "6438 5122",
            "email": "mom_qsm@mom.gov.sg",
            "hours": "Mon-Fri 8:30am-5:30pm",
            "description": "General employment enquiries and complaints",
        },
        {
            "name": "Tripartite Alliance for Dispute Management (TADM)",
            "phone": "6838 7969",
            "email": "enquiry@tadm.sg",
            "hours": "Mon-Fri 8:30am-5:30pm",
            "description": "Employment dispute mediation and claims",
        },
        {
            "name": "Workplace Safety and Health Council (WSHC)",
            "phone": "6317 9100",
            "email": "",
            "hours": "Mon-Fri 8:30am-5:30pm",
            "description": "Workplace accident reporting and safety enquiries",
        },
        {
            "name": "Tripartite Alliance for Fair and Progressive Employment Practices (TAFEP)",
            "phone": "6838 0969",
            "email": "query@tafep.sg",
            "hours": "Mon-Fri 8:30am-5:30pm",
            "description": "Discrimination complaints and fair employment guidance",
        },
    ]

    # Build topic-specific contacts from known emergency scenarios
    topic_contacts = []
    for topic_id, er in EMERGENCY_RESPONSES.items():
        topic_contacts.append(
            {
                "topic_id": topic_id,
                "title": er.title,
                "primary_contact": (
                    "TADM"
                    if "tadm" in topic_id or "claim" in topic_id
                    else (
                        "WSHC"
                        if "injury" in topic_id
                        else "TAFEP" if "discrimination" in topic_id else "MOM"
                    )
                ),
                "escalation_available": True,
            }
        )

    return {
        "general_contacts": general_contacts,
        "topic_contacts": topic_contacts,
        "emergency_note": (
            "For life-threatening emergencies, call 995 (ambulance) or 999 (police). "
            "The contacts listed here are for employment-related emergencies only."
        ),
    }


@router.post("/escalate", response_model=EscalationResponse)
async def escalate_emergency(
    req: EscalationRequest,
    current_user: dict = Depends(get_current_user),
) -> EscalationResponse:
    """Submit an emergency escalation request.

    This records the escalation and would trigger notifications
    to the appropriate specialist in production.
    """
    # Validate topic exists
    if req.topic_id not in EMERGENCY_RESPONSES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown emergency topic: '{req.topic_id}'",
        )

    global _escalation_counter
    _escalation_counter += 1
    escalation_id = f"ESC-{_escalation_counter:04d}"

    return EscalationResponse(
        escalation_id=escalation_id,
        topic_id=req.topic_id,
        status="submitted",
        message=(
            f"Your emergency escalation has been submitted (reference: {escalation_id}). "
            "An employment law specialist will contact you within 2 business hours. "
            "In the meantime, follow the immediate obligations listed in the emergency guide."
        ),
    )
