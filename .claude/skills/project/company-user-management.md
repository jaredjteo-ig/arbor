---
name: company-user-management
description: "Company and user profile management patterns. Use when working on company onboarding, user CRUD, role management, workforce composition, or profile endpoints."
---

# Company & User Management

DataFlow-backed models for company profiles and user accounts.

## DataFlow Models

### Company

```python
# Key fields (auto-generates CompanyCreateNode, CompanyReadNode, etc.)
name: str
uen: Optional[str]          # Singapore Unique Entity Number (8-10 alphanum, ends with letter)
sector: Optional[str]       # e.g., "F&B", "Retail", "Tech", "Construction"
headcount_local: int        # Singapore citizens
headcount_pr: int           # Permanent residents
headcount_ep: int           # Employment Pass holders
headcount_sp: int           # S-Pass holders
headcount_wp: int           # Work Permit holders
profile_completeness_score: float  # 0.0-1.0
```

### User

```python
# Key fields (auto-generates UserCreateNode, UserReadNode, etc.)
email: str
name: str
company_id: Optional[int]  # Multi-tenant link
role: str                   # "owner" | "hr_manager" | "consultant" | "platform_admin"
password_hash: str          # bcrypt-hashed
is_active: bool
last_login_at: Optional[datetime]
```

## Roles

| Role             | Access                                | Company Scope    |
| ---------------- | ------------------------------------- | ---------------- |
| `owner`          | Full company access + admin endpoints | Own company      |
| `hr_manager`     | Full company access + admin endpoints | Own company      |
| `consultant`     | Read access, advisory queries         | Multiple clients |
| `platform_admin` | Cross-company access                  | All companies    |

## API Endpoints

| Endpoint                          | Method | Purpose                                             |
| --------------------------------- | ------ | --------------------------------------------------- |
| `/profile/{company_id}`           | GET    | Company profile with workforce + completeness score |
| `/profile/`                       | POST   | Create new company profile                          |
| `/profile/{company_id}`           | PUT    | Update company profile                              |
| `/profile/{company_id}/workforce` | GET    | Workforce composition (local ratio)                 |
| `/auth/register`                  | POST   | Create user account                                 |
| `/auth/me`                        | GET    | Current user profile                                |

## Onboarding Flow

1. `POST /auth/register` — Create user with optional `company_id`
2. `POST /profile/` — Create company profile (name, UEN, sector)
3. `PUT /profile/{id}` — Add workforce composition (headcounts)
4. `POST /advisory/query` — First advisory query

Profile completeness score drives trust chain quality (higher = more context for accurate advice).

## Tenant Isolation

- Users access only their own company's data
- `platform_admin` bypasses company checks
- Enforced via `validate_company_access(current_user, requested_company_id)`

## Key Files

- `src/hr_advisory/models/company_user.py` — DataFlow model definitions
- `src/hr_advisory/api/routers/profile.py` — Profile endpoints
- `src/hr_advisory/api/routers/auth.py` — Auth/user endpoints
- `src/hr_advisory/services/auth_service.py` — Auth business logic
- `docs/02-api-reference.md` — Full API documentation

## Consult Agent

For profile/user work: `arbor-platform-specialist`
