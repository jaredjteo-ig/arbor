---
type: DECISION
date: 2026-03-30
project: arbor
topic: Migrate platform from Nexus to NexusEngine with SAAS preset
phase: implement
tags: [nexus, platform, engine, saas-preset]
---

# Migrate to NexusEngine.builder().preset(Preset.SAAS)

## Decision

Replace manual `Nexus()` constructor in `platform.py` with `NexusEngine.builder().preset(Preset.SAAS).config(...).build()`. The SAAS preset provides CORS, security headers, CSRF protection, and rate limiting. Custom overrides (auto_discovery=False, enable_durability=False, explicit CORS headers) applied via `.config()`.

## Alternatives Considered

1. **Keep manual Nexus()** — rejected; this is the Layer 2 primitive approach. NexusEngine is the Engine layer (framework-first rule).
2. **Full preset with no overrides** — rejected; `enable_durability=False` is required (deduplicator caches GET responses without considering Authorization header), `auto_discovery=False` is required for DataFlow.

## Consequences

- Removed `_add_security_headers_middleware()` — SAAS preset handles security headers
- Removed `from hr_advisory.security.validation import SECURITY_HEADERS` from platform.py
- `SECURITY_HEADERS` constant still exists in `security/validation.py` for test use
