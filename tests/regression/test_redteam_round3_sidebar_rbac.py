"""Red-team round-3 — sidebar RBAC gate (P1).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding H1 / C7 — `NavigationSidebar.tsx` only checked
`role === "employee"` and showed the full owner-level sidebar to
every non-employee role. HR Manager Grace Koh saw Admin and
Integrations entries that lead to surfaces she had no business
touching (regulatory updates, KB management, Xero / CorpPass
connections). Backend correctly 404'd those endpoints but the
frontend leaked the surface.

This file pins the structural fix:

  - NavigationSidebar declares a SidebarRole type.
  - NavItem has an optional requiredRoles allow-list.
  - canSeeNavItem helper exists and is invoked when filtering each
    nav group.
  - /admin and /settings/integrations carry requiredRoles: ["owner"]
    so HR Manager / line-manager / IC never see them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SIDEBAR = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "components"
    / "shell"
    / "NavigationSidebar.tsx"
)


@pytest.mark.regression
def test_redteam3_sidebar_has_role_predicate():
    """The sidebar declares a SidebarRole type, a requiredRoles field on
    NavItem, and a canSeeNavItem predicate (P49 — predicate not role
    proxy)."""
    src = SIDEBAR.read_text()
    assert "SidebarRole" in src, "Sidebar must declare a SidebarRole type."
    assert "requiredRoles?" in src, (
        "NavItem must have an optional requiredRoles allow-list."
    )
    assert "function canSeeNavItem" in src, (
        "Sidebar must expose a canSeeNavItem predicate."
    )


@pytest.mark.regression
def test_redteam3_sidebar_admin_is_owner_only():
    """The Admin nav entry MUST carry requiredRoles: ['owner']."""
    src = SIDEBAR.read_text()
    # Match: { ...href: "/admin" ...requiredRoles: ["owner"] ... }
    # in a 600-char window so we tolerate formatting.
    idx = src.index('href: "/admin"')
    window = src[max(0, idx - 600) : idx + 600]
    assert 'requiredRoles: ["owner"]' in window, (
        "/admin nav entry must be gated to owner only."
    )


@pytest.mark.regression
def test_redteam3_sidebar_integrations_is_owner_only():
    """The Integrations nav entry MUST carry requiredRoles: ['owner']."""
    src = SIDEBAR.read_text()
    idx = src.index('href: "/settings/integrations"')
    window = src[max(0, idx - 600) : idx + 600]
    assert 'requiredRoles: ["owner"]' in window, (
        "/settings/integrations nav entry must be gated to owner only."
    )


@pytest.mark.regression
def test_redteam3_sidebar_filters_each_nav_group():
    """Every rendered nav group must filter through canSeeNavItem.
    Otherwise a future contributor could add requiredRoles to an item
    and have it silently rendered to everyone."""
    src = SIDEBAR.read_text()
    # The filter expression .filter((i) => canSeeNavItem(i, role)) must
    # appear at least once per group: core, tools, management, bottom.
    occurrences = src.count("canSeeNavItem(i, role)")
    assert occurrences >= 4, (
        "Sidebar must invoke canSeeNavItem on every nav group "
        f"(core/tools/management/bottom). Found only {occurrences}."
    )


@pytest.mark.regression
def test_redteam3_sidebar_role_resolved_from_user():
    """The role variable must come from useAuth().user.role, not a
    hardcoded constant or a role proxy."""
    src = SIDEBAR.read_text()
    # The resolution pattern: const role = (user?.role ?? "employee") as SidebarRole;
    assert re.search(r"const\s+role\s*=\s*\(user\?\.\s*role\s*\?\?", src), (
        "role must be resolved from user?.role with a fallback default."
    )
