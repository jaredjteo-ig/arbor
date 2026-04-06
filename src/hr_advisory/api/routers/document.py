"""Document and template endpoints.

Handles template listing, document generation from templates,
preview, and download with company-specific customisation.
"""

import hashlib
import logging
import re
from collections import OrderedDict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.templates.content import TEMPLATES, TemplateDefinition

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory document store for generated documents (production: use object storage).
# Bounded to prevent memory exhaustion in long-running processes.
_generated_docs: OrderedDict[str, dict] = OrderedDict()
MAX_GENERATED_DOCS = 1000


def _sanitize_filename(title: str, extension: str = ".txt") -> str:
    """Sanitize a title for use in Content-Disposition headers.

    Removes all characters except alphanumeric, hyphen, underscore, dot, and space.
    Replaces spaces with hyphens, truncates to 100 characters, and ensures the
    correct file extension.
    """
    # Keep only safe characters
    safe = re.sub(r"[^a-zA-Z0-9\-_. ]", "", title)
    # Replace spaces with hyphens
    safe = safe.replace(" ", "-")
    # Collapse multiple hyphens
    safe = re.sub(r"-+", "-", safe).strip("-")
    # Truncate (leaving room for extension)
    max_base = 100 - len(extension)
    safe = safe[:max_base] if len(safe) > max_base else safe
    # Ensure it has the correct extension
    if not safe.endswith(extension):
        safe = safe + extension
    # Fallback if empty
    if safe == extension:
        safe = "document" + extension
    return safe


def _template_to_dict(idx: int, t: TemplateDefinition) -> dict:
    """Convert a TemplateDefinition to an API response dict."""
    return {
        "id": idx + 1,
        "name": t.name,
        "description": t.description,
        "category": t.category,
        "template_type": t.template_type,
        "provisions_count": len(t.linked_provisions),
        "required_fields": t.required_fields,
        "optional_fields": t.optional_fields,
        "compliance_notes": t.compliance_notes,
    }


def _template_detail(idx: int, t: TemplateDefinition) -> dict:
    """Full template detail including content."""
    result = _template_to_dict(idx, t)
    result["content"] = t.content
    result["linked_provisions"] = t.linked_provisions
    result["version"] = 1
    return result


def _fill_template(template: TemplateDefinition, field_values: dict) -> str:
    """Fill template placeholders with provided field values."""
    content = template.content
    for key, value in field_values.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    return content


def _highlight_unfilled(content: str) -> list[dict]:
    """Identify unfilled placeholders in generated content.

    Returns a list of {field, line} for any remaining {{placeholder}} markers.
    """
    unfilled = []
    for i, line in enumerate(content.split("\n"), 1):
        for match in re.finditer(r"\{\{(\w+)\}\}", line):
            unfilled.append({"field": match.group(1), "line": i})
    return unfilled


@router.get("/templates")
async def list_templates(
    category: str | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all available document templates, optionally filtered by category."""
    templates = TEMPLATES
    if category:
        templates = [t for t in templates if t.category.lower() == category.lower()]

    return {
        "templates": [
            _template_to_dict(idx, t) for idx, t in enumerate(TEMPLATES) if t in templates
        ],
        "total": len(templates),
    }


@router.get("/templates/{template_id}")
async def get_template(
    template_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a specific template by ID (1-indexed)."""
    idx = template_id - 1
    if idx < 0 or idx >= len(TEMPLATES):
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_detail(idx, TEMPLATES[idx])


@router.post("/preview")
async def preview_document(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Preview a document with partial field values.

    Like generate, but does not require all fields and returns
    a list of unfilled placeholders for the UI to highlight.
    """
    body = await request.json()
    template_id: int = body.get("template_id", 0)
    field_values: dict = body.get("fields", {})

    idx = template_id - 1
    if idx < 0 or idx >= len(TEMPLATES):
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[idx]
    content = _fill_template(template, field_values)
    unfilled = _highlight_unfilled(content)

    filled_count = len(template.required_fields) - len(
        [f for f in template.required_fields if f not in field_values or not field_values[f]]
    )
    total_required = len(template.required_fields)

    return {
        "template_id": template_id,
        "document": {
            "title": template.name,
            "content": content,
            "format": "text",
        },
        "unfilled_fields": unfilled,
        "completion": {
            "filled": filled_count,
            "total": total_required,
            "percentage": round(filled_count / total_required * 100) if total_required else 100,
        },
        "provisions_applied": template.linked_provisions,
    }


@router.post("/generate")
async def generate_document(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Generate a customised document from a template.

    Accepts template ID and field values, then fills in
    the template placeholders with the provided data.
    Returns a document_id that can be used for download.
    """
    body = await request.json()
    template_id: int = body.get("template_id", 0)
    company_id: int | None = body.get("company_id")
    validate_company_access(current_user, requested_company_id=company_id)
    field_values: dict = body.get("fields", {})

    idx = template_id - 1
    if idx < 0 or idx >= len(TEMPLATES):
        raise HTTPException(status_code=404, detail="Template not found")

    template = TEMPLATES[idx]

    # Check required fields
    missing = [f for f in template.required_fields if f not in field_values]
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    content = _fill_template(template, field_values)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Generate a document ID for download reference
    doc_hash = hashlib.sha256(f"{template_id}:{timestamp}:{content[:100]}".encode()).hexdigest()[
        :12
    ]
    document_id = f"doc_{doc_hash}"

    doc_record = {
        "document_id": document_id,
        "template_id": template_id,
        "company_id": company_id,
        "title": template.name,
        "content": content,
        "format": "text",
        "provisions_applied": template.linked_provisions,
        "compliance_notes": template.compliance_notes,
        "timestamp": timestamp,
        "fields": field_values,
    }

    # Evict oldest entries if at capacity
    while len(_generated_docs) >= MAX_GENERATED_DOCS:
        _generated_docs.popitem(last=False)

    # Store for later download
    _generated_docs[document_id] = doc_record

    return {
        "template_id": template_id,
        "company_id": company_id,
        "document_id": document_id,
        "document": {
            "title": template.name,
            "content": content,
            "format": "text",
        },
        "provisions_applied": template.linked_provisions,
        "compliance_notes": template.compliance_notes,
        "timestamp": timestamp,
    }


@router.get("/download/{document_id}")
async def download_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
) -> PlainTextResponse:
    """Download a previously generated document as plain text.

    Returns the document with Content-Disposition header for file download.
    Enforces tenant isolation — users can only download documents belonging
    to their company.
    """
    doc = _generated_docs.get(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found or expired")

    # Enforce tenant isolation: user can only download their company's documents
    validate_company_access(current_user, requested_company_id=doc.get("company_id"))

    filename = _sanitize_filename(doc["title"], ".txt")

    return PlainTextResponse(
        content=doc["content"],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/history")
async def list_generated_documents(
    company_id: int | None = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List previously generated documents, scoped to the user's company.

    Non-admin users always see only their own company's documents.
    Platform admins can optionally filter by company_id.
    """
    role = current_user.get("role", "")
    user_company_id = current_user.get("company_id")

    # Determine the effective company filter
    if company_id is not None:
        # Explicit company requested — validate access
        validate_company_access(current_user, requested_company_id=company_id)
        effective_company_id = company_id
    elif role == "platform_admin":
        # Admins without explicit filter see all
        effective_company_id = None
    else:
        # Non-admin users always scoped to their own company
        effective_company_id = user_company_id

    docs = list(_generated_docs.values())
    if effective_company_id is not None:
        docs = [d for d in docs if d.get("company_id") == effective_company_id]

    # Return summary (without full content)
    return {
        "documents": [
            {
                "document_id": d["document_id"],
                "title": d["title"],
                "template_id": d["template_id"],
                "company_id": d.get("company_id"),
                "timestamp": d["timestamp"],
            }
            for d in sorted(docs, key=lambda x: x["timestamp"], reverse=True)
        ],
        "total": len(docs),
    }
