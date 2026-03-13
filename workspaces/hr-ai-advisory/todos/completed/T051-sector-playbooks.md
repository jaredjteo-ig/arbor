# T051 — Sector-Specific Playbooks

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Sector Taxonomy**:

- `Sector` enum with 6 sectors: FNB, CONSTRUCTION, TECHNOLOGY, PROFESSIONAL_SERVICES, MANUFACTURING, RETAIL

**Data Models**:

- `ComplianceChallenge` frozen dataclass with title, description, risk tier, and relevant provisions — 4 challenges defined per sector (24 total)
- `SectorPlaybook` frozen dataclass with sector identity, key regulations, applicable provisions, common challenges, suggested questions, calculator focus areas, DRC category, and PWM applicability

**Sector Playbooks**:

- **F&B** — Part IV hours/overtime, Services DRC (35% S Pass / 8% WP), kitchen safety, PH pay for hourly workers. Calculator focus: CPF, quota/levy, leave
- **Construction** — Higher levy tiers (skilled vs unskilled), mandatory safety training (SOC/WSQ), workplace injury reporting, dormitory obligations. Calculator focus: CPF, quota/levy
- **Technology** — COMPASS framework for EP, stock option tax treatment, PDPA compliance for data roles, flexible work arrangements. Calculator focus: CPF
- **Professional Services** — EP salary thresholds, non-compete enforceability, MyCareersFuture advertising (FCF), CPF OW ceiling for high earners. Calculator focus: CPF, quota/levy
- **Manufacturing** — Shift work overtime across rotating schedules, noise exposure monitoring (85dB+), chemical handling WSH compliance, Manufacturing DRC. Calculator focus: CPF, quota/levy, leave
- **Retail** — Part-time employee pro-rated entitlements, PH working arrangements, weekend/evening scheduling, PWM for in-house cleaners. Calculator focus: CPF, leave, quota/levy

**Public API**:

- `get_playbook()` — retrieve a specific sector's playbook
- `get_all_playbooks()` — list all 6 sector playbooks
- `get_sector_challenges()` — get compliance challenges for a sector
- `get_sector_questions()` — get suggested natural-language questions for a sector
- `get_applicable_provisions()` — get provision IDs applicable to a sector
- `match_sector()` — fuzzy match free-text sector names (e.g., "F&B", "tech", "factory") to Sector enum via a 30-entry synonym mapping

## Files

- `src/hr_advisory/workflows/sector_playbooks.py` — sector-specific playbooks module
