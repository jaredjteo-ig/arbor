"""Document templates for Arbor HR Advisory.

Each template is an EA-compliant document with placeholder fields
that get filled in during document generation.
"""

from hr_advisory.templates.content import TEMPLATES, get_template_by_type

__all__ = ["TEMPLATES", "get_template_by_type"]
