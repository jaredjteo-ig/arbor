# Milestone 1: Foundation

**What users can do after this milestone**: Nothing yet — this is the infrastructure that everything else builds on. Project structure, design system, database schema, agent architecture, authentication, and the API layer are in place and tested.

**Tasks**: 15

---

## T001: Project scaffolding and repository structure

Set up the monorepo structure:

- `src/` — Backend (Python, Kailash SDK)
- `apps/web/` — React web app
- `apps/mobile/` — Flutter mobile app
- `docs/` — Project documentation
- `.env.example` — Environment variable template (LLM API keys, database URLs)
- `docker-compose.dev.yml` — Local development environment (PostgreSQL + pgvector + Redis)

Install Kailash dependencies: `kailash`, `kailash-dataflow`, `kailash-nexus`, `kailash-kaizen`.
Set up Python virtual environment, `pyproject.toml`, and test runner (pytest).
Set up React project with Vite/Next.js, TypeScript, TanStack Query, React Hook Form.
Set up Flutter project with Riverpod, GoRouter, Dio.
Root `conftest.py` that auto-loads `.env`.

**Red team fix S2**: Include `apps/web/` and `apps/mobile/` from day one — both platforms from the start.

---

## T002: Design system — shared tokens and i18n infrastructure

Create the canonical design token specification shared between React and Flutter:

- Colors: primary navy (#1E3A5F), secondary teal (#0D6E4F), semantic colors, risk-tier colors (green/amber/red)
- Typography: Source Sans 3 font family, scale from 11px overline to 28px page title, 16px body minimum
- Text size scaling: Normal / Large / Extra Large built into the token system from the start (not retrofitted later)
- Spacing: 4px base scale (xs through 3xl)
- Border radius: sm(6px) through full(9999px)
- Shadows: card, raised, modal

Implement in React as CSS custom properties or theme object.
Implement in Flutter as static const design system Dart files.
Create a shared `tokens.json` that generates both platform files.

**i18n infrastructure** (set up now, English only at launch):

- React: i18next configured, all user-facing strings in translation files from the first component onward
- Flutter: ARB files configured, all user-facing strings externalized from the first widget onward
- Date formatting: Singapore standard ("15 Mar 2026"), currency: "S$" prefix consistently
- Layout flexible for text that may be 30% longer in Chinese (future)

**Red team fix R2-O03**: i18n infrastructure from M1 is dramatically easier than retrofitting later.
**Red team fix R2-O04**: Text size accessibility built into design tokens from the start.

---

## T003: Design system — base components (React)

Build Tier 1 components in `apps/web/src/components/design-system/`:

- AppButton (primary, secondary, outlined, text, danger variants)
- AppInput (text, number, dropdown, textarea)
- AppCard (standard, elevated, flat)
- ChatBubble (user variant, system variant with risk-tier border colors)
- ChatInput (text + voice button + suggested prompts)
- SourceCitation (clickable reference: "[Employment Act, Section 88A]")
- RiskTierBadge (GREEN/AMBER/RED with text labels, not color-only)
- AlertBanner (info, warning, error, success)
- NavigationSidebar (collapsible, 240px to 60px)
- StepIndicator (for multi-step forms)
- LoadingState (skeleton screens)
- EmptyState (illustration + message + CTA)
- ErrorState (network error, server error, service unavailable — with retry actions)
- Toast/Snackbar
- FeedbackButtons (thumbs up/down + optional text field — reusable on all advisory responses)

All components respect text size scaling from T002 tokens.
Follow accessibility requirements: 48px min touch targets, WCAG AAA contrast, visible focus indicators, no color-only status communication.
All user-facing strings use i18n keys (not hardcoded English).

---

## T004: Design system — base components (Flutter)

Build matching Tier 1 components in `apps/mobile/lib/core/design/components/`:

- Same component inventory as T003 adapted for Flutter/Material Design (including ErrorState and FeedbackButtons)
- Bottom navigation bar (5 items: Home, Chat, Tools, Docs, More)
- BottomSheet (for filters, quick actions)
- Voice input button with haptic feedback
- Pull-to-refresh wrapper
- Large touch targets (48x48dp minimum)

All components respect text size scaling from T002 tokens.
All user-facing strings use ARB localization.
Use Riverpod for state management in all components.

---

## T005: App shell and navigation (React)

Build the web app layout structure:

- AppShell: persistent left sidebar + main content area
- NavigationSidebar with sections: Dashboard, Advisory, Calculators, Documents, Compliance (primary); Alerts, Company Profile, Settings, Help (secondary)
- TopBar: search input, notification bell with badge count, profile avatar with dropdown (profile, settings, logout)
- Responsive: sidebar collapses to icon-only on smaller screens
- Routing with React Router: all routes as specified in the frontend architecture (/, /advisory, /calculators/_, /documents/_, /compliance/_, /alerts/_, /profile/_, /settings, /clients/_)
- Error boundary wrapper with ErrorState component for unhandled errors

---

## T006: App shell and navigation (Flutter)

Build the mobile app layout structure:

- Bottom navigation: Home, Chat, Tools, Docs, More
- GoRouter configuration with all routes
- Navigation guards (auth check, onboarding completion check)
- Deep linking support for push notification navigation
- App lifecycle management (foreground/background state)

---

## T007: DataFlow models — regulatory knowledge base

Define and implement all DataFlow models for the structured KB:

- `Act` model: title, short_name, authority_type, issuing_body, current_version_date, official_url
- `Domain` model: name, description, parent_domain_id (self-referential)
- `Provision` model: source_act_id, section, title, formal_text, plain_summary, interpretation_notes (common misinterpretations and correct interpretation per authority), effective_date, superseded_date, superseded_by_id, authority_level (enum: statute/subsidiary/tripartite_guideline/advisory/best_practice), domain_id, next_review_date, embedding (pgvector)
- `ApplicabilityRule` model: provision_id, rule_type, criteria_type, criteria_value (JSON), notes
- `CrossReference` model: source_provision_id, target_provision_id, relationship_type, notes
- `PracticalExample` model: provision_id, scenario, calculation (JSON), outcome
- `RateTable` model: table_type, effective_date, expiry_date, criteria (JSON), rate_value, source_url
- `UserFeedback` model: session_id, user_id, rating (thumbs up/down), feedback_text, created_at

Use `soft_delete=True` on Provision and RateTable (never truly delete regulatory content).
Set up PostgreSQL with pgvector extension.
Custom DataFlow node for vector similarity queries with applicability rule filtering.
Smoke test: verify pgvector end-to-end (schema creation, embedding insertion, similarity search query).

**Red team fix R2-COC-REC6**: `interpretation_notes` field prevents convention drift — agents get institutional interpretation, not just institutional facts.

---

## T008: DataFlow models — company and user

Define and implement DataFlow models for users and companies:

- `Company` model: name, uen, sector, sub_sector, headcount_local, headcount_pr, headcount_ep, headcount_sp, headcount_wp, salary_ranges (JSON), profile_completeness_score. Use `multi_tenant=True` for consultant mode.
- `User` model: email, name, company_id, role (owner/hr_manager/consultant), preferences (JSON including text_size, notification_prefs, language)
- `Conversation` model: user_id, company_id, title, created_at, updated_at (groups related AdvisorySessions)
- `AdvisorySession` model: conversation_id, user_id, company_id, query_text, response_text, provisions_cited (JSON), agents_involved (JSON), confidence_score, risk_tier, trust_lineage (JSON), genesis_record (JSON), feedback_rating, feedback_text
- `ContentUpdate` model: source_url, change_summary, affected_domains (JSON), urgency, status, author_id, published_at
- `Template` model: name, template_type, content, version, linked_provision_ids (JSON)

**Red team fix C4**: Company model supports multi-tenant for consultant multi-client access.

---

## T009: Nexus multi-channel API setup

Configure Nexus as the unified API gateway:

- Use `auto_discovery=False` (critical for DataFlow integration)
- Register workflow endpoints by category: advisory/_, calculator/_, compliance/_, document/_, profile/_, kb/_, auth/_, search/_
- Session management with company context (company_id, user_id, conversation_history, risk_tier_escalations)
- Session backend: Redis for production, in-memory for development
- SSE streaming endpoint for advisory responses (word-by-word streaming from Kaizen agents)
- Search API endpoints: KB semantic search (pgvector) + full-text search with domain/applicability/date filters
- CORS configuration for React web app
- Rate limiting
- Health check endpoints

---

## T010: Kaizen agent architecture — orchestration and memory

Set up the orchestration tier and memory infrastructure (the foundation for all agents):

**Orchestration agents**:

- `QueryAnalyzerAgent` (BaseAgent): classifies queries by domain, extracts entities, identifies risk tier. Chain-of-Thought pattern. Routes, does not answer.
- `OrchestratorAgent` (TrustedSupervisorAgent): receives QueryAnalyzer output, decides which specialists to engage. Uses supervisor-worker pattern with parallel/sequential/router dispatch.
- `ResponseSynthesizerAgent` (BaseAgent): reads all specialist outputs from SharedMemoryPool, synthesizes plain-language answer, adds citations, applies risk-tier disclaimers.

**Memory infrastructure**:

- `SharedMemoryPool` configuration: all specialist outputs tagged with domain, provision_ids, confidence, risk_tier, cross_domain_flags
- `ShortTermMemory` per session (conversation context across turns)
- `LongTermMemory` per company (patterns and preferences over time)

**Multi-turn context management**:

- Conversation context maintained across follow-up questions within a session
- Test with 10+ turn conversations to verify context continuity

---

## T010A: Kaizen agent architecture — domain specialists

Build all domain specialist agents (Tier 2):

- `EmploymentActAgent` (TrustedAgent): EA provisions, Part IV, leave, termination, notice periods
- `CPFAgent` (TrustedAgent): contribution rates, age bands, PR years, OW/AW ceilings
- `ForeignManpowerAgent` (TrustedAgent): DRC quotas, levies, COMPASS, pass types, sector rules
- `FairEmploymentAgent` (TrustedAgent): TAFEP, Workplace Fairness Legislation, FWA, anti-discrimination
- `TaxAgent` (TrustedAgent): IRAS employer obligations, BIK treatment, withholding tax
- `WSHAgent` (TrustedAgent): Workplace Safety and Health Act, sector requirements
- `ComplianceAgent` (TrustedAgent): cross-domain compliance checking, reads other specialists' outputs

Each agent grounded in KB — must cite from structured provisions, never from training data.
Constraint envelopes: hard boundaries per agent (TaxAgent cannot advise on employment law, ComplianceAgent cannot make legal determinations).

---

## T010B: Kaizen agent architecture — action agents

Build action agents (Tier 3):

- `DocumentGenerationAgent` (TrustedAgent): templates, contracts, policies via Core SDK workflows
- `CalculatorAgent` (TrustedAgent): thin wrapper dispatching to deterministic Core SDK calculator workflows

All agents are `TrustedAgent` (not plain BaseAgent) with EATP trust chains.
End-to-end test: verify a query flows through QueryAnalyzer → Orchestrator → Specialist(s) → ResponseSynthesizer and returns a complete response with citations.

---

## T011: Core SDK — employee classification workflow

Build the deterministic Employee Classification Engine as a Core SDK workflow:

- Input: monthly_basic_salary, job_role_description, is_manual_labor (workman test), citizenship_status (SC/PR/foreigner), pr_year (if PR), pass_type (if foreign), employment_type (FT/PT/contract), sector
- Nodes: input validation, EA coverage check (salary threshold + role type), Part IV applicability, CPF status (citizenship + age tier), pass type validation
- Output: complete classification object with all regulatory categories, which EA parts apply, CPF obligation status, applicable leave types
- 100% deterministic — no LLM involvement
- Comprehensive test coverage for all employee categories from the regulatory landscape analysis

**Red team fix S4**: Include PR year as required input for all CPF-related classifications.

---

## T012: Authentication and authorization

Build the complete authentication system:

**Backend (Nexus middleware)**:

- User registration (email + password with validation)
- Google OAuth2 sign-in
- JWT token issuance and refresh
- Password reset flow (email-based)
- Session management (token expiry, logout, active session tracking)
- Role-based access control middleware (owner / hr_manager / consultant)

**React frontend**:

- Login page (email + Google)
- Signup page (email + Google)
- Password reset page
- Auth context provider (token storage, auto-refresh, logout)
- Protected route wrapper

**Flutter frontend**:

- Matching login/signup/reset screens
- Secure token storage (flutter_secure_storage)
- Auth state provider (Riverpod)
- Navigation guard integration with GoRouter (T006)

**Red team fix R2-G01**: Authentication is foundational infrastructure that blocks onboarding and every authenticated feature.

---

## T013: API service layer (React + Flutter)

Build the API integration layer for both frontends:

React (`apps/web/src/services/api/`):

- Base API client with auth headers, error mapping, retry logic
- SSE client for streaming advisory responses (EventSource wrapper)
- Service modules: advisory.ts, calculators.ts, documents.ts, compliance.ts, profile.ts, alerts.ts, auth.ts, search.ts
- TanStack Query hooks for all API calls
- Error handling: network errors, auth errors (auto-redirect to login), server errors

Flutter (`apps/mobile/lib/core/network/`):

- Dio-based API client with auth interceptor and error interceptor
- SSE client for streaming advisory responses
- Repository pattern per feature
- Riverpod providers wrapping repositories

Both platforms share the same API contract from Nexus.
