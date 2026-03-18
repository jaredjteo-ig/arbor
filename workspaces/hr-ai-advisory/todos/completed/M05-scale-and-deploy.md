# Milestone 5: Scale, Polish & Deployment

**What users can do after this milestone**: The platform is production-ready with HRIS integrations, analytics, robust deployment, and comprehensive testing. Performance is optimized, accessibility is verified, and the platform is ready for PSG listing application.

**Tasks**: 10

---

## T053: HRIS integration — API adapters

Build integration adapters for Singapore HRIS platforms:

- Third-party HRIS API adapters: pull employee data (headcount, salary, CPF status) to auto-populate company profile
- Generic CSV import: for companies using Excel or unsupported HRIS
- Data sync is read-only from HRIS (we don't write back)
- OAuth-based authentication for each integration
- Sync scheduling (daily/weekly) with manual trigger option

---

## T054: Analytics dashboard

Build analytics for platform users:

- Workforce composition overview (headcount by category, visual breakdown)
- Compliance status over time (trend chart)
- Cost modeling: total CPF costs, levy costs, projected impact of hiring scenarios
- Advisory usage: queries by domain, most-asked topics
- For consultants: per-client analytics summary

---

## T055: Offline capabilities (Flutter)

Implement offline support for mobile:

- Cache previously viewed conversations locally (Hive/Isar)
- Bundle reference tables: CPF rates, levy rates, leave entitlements (updated on app launch)
- Downloaded documents available offline (app document directory)
- Company profile data synced locally with offline editing (queue for sync on reconnect)
- Offline indicator banner: "Offline mode — some features unavailable"
- Sync manager: queues write operations, syncs on connectivity return

---

## T056: Push notifications (Flutter + backend)

Implement push notification system:

- Firebase Cloud Messaging (FCM) for cross-platform
- Android notification channels: "Regulatory Updates" (default on), "Reminders" (configurable)
- Notification payload includes deep link to relevant screen
- Permission request after onboarding completion (not on first launch)
- Backend triggers: regulatory change → identify affected users by profile → send targeted notifications
- CPF filing deadline reminders, work pass renewal reminders

---

## T057: Performance optimization

Optimize platform performance:

- Advisory response: <3 seconds first token via SSE streaming
- Calculator results: <1 second
- Knowledge base retrieval: optimize pgvector queries with proper indexing
- React: code splitting by route, lazy loading of calculator and document modules
- Flutter: widget tree optimization, image caching
- API response caching (TanStack Query stale-while-revalidate patterns)
- Database query optimization (DataFlow query analysis)

---

## T058: Comprehensive E2E testing

Build end-to-end test suites:

- Playwright tests for React web: onboarding flow, advisory Q&A, all calculators, document generation, compliance check, emergency flow, multi-client switching
- Flutter integration tests: matching coverage for mobile
- Advisory accuracy E2E: 200+ scenarios with expected answers (built incrementally from T049 regression suite)
- Cross-domain query tests: retrenchment, hiring foreign workers, termination
- Edge cases: PR year transitions, part-time pro-ration, OW/AW ceiling interactions
- Load testing: concurrent advisory sessions (50+ simultaneous users)
- Accessibility testing: screen reader, keyboard navigation, high contrast

---

## T059: Security review and hardening

Security audit before deployment:

- PDPA compliance: data minimization, consent, retention, breach notification process
- Authentication: secure JWT handling, session management, password hashing
- API security: rate limiting, input validation, CORS, CSRF protection
- Data at rest encryption (PostgreSQL)
- Data in transit encryption (TLS everywhere)
- Secret management: all API keys in environment variables, never in code
- Dependency audit: check for known vulnerabilities
- No PII storage beyond what's necessary (advise users to use generic scenarios)
- OWASP Top 10 compliance check

---

## T060: Deployment configuration

Set up production deployment:

- Docker containerization (AsyncLocalRuntime for Kailash in containers)
- Docker Compose for development environment
- PostgreSQL + pgvector + Redis production setup
- Environment configuration: development, staging, production
- Health check endpoints
- Monitoring: error alerting, basic metrics (CPU, memory, request rate)
- SSL/TLS for all endpoints
- Backup and recovery procedures
- Deployment runbook in `deploy/deployment-config.md`

---

## T061: PSG listing preparation

Prepare for Productivity Solutions Grant pre-approval:

- Document platform capabilities in IMDA-required format
- Prepare pricing tiers that qualify for PSG
- Deployment track record (beta user testimonials)
- Compliance with IMDA evaluation criteria
- Submit application (3-6 month approval process)

---

## T062: Market sizing reconciliation and go-to-market

Reconcile market sizing between competitive analysis and value audit:

- Define single set of defensible assumptions for TAM/SAM/SOM
- Clarify go-to-market: open platform + association partnerships for distribution and credibility (not restriction)
- Pricing model decision: freemium with paid tiers, tiered by company size
- PSG subsidy impact on effective pricing
- Launch marketing plan
- Competitive monitoring: track Employment Hero and other entrants into Singapore HR advisory space

**Red team fix M1**: Reconcile "open to all" with association distribution strategy.
**Red team fix S6**: Reconcile market sizing disagreement.
**Red team fix M3**: Employment Hero competitive monitoring included.
