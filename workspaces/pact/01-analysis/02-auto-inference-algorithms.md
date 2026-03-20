# PACT-lite Auto-Inference Algorithms

## Detailed Algorithm Specification v0.1

**Status**: Working Draft
**Date**: 2026-03-21
**Companion to**: 01-pact-lite-design.md

---

## 1. D/T/R Inference from Employee Data

### 1.1 Input Data

The algorithm operates on three data sources already present in Arbor:

```
Source 1: Employee records
  Fields used: id, department, designation, reporting_manager_id, company_id, is_active

Source 2: User records
  Fields used: id, role (owner/hr_manager/consultant/employee), company_id

Source 3: Organization records (if populated)
  Fields used: id, parent_org_id, name, code, company_id
```

### 1.2 Algorithm: build_pact_tree(company_id)

```
FUNCTION build_pact_tree(company_id: int) -> PactTree:

  # ── Phase 1: Gather Data ──────────────────────────────────────

  employees = query_all_active_employees(company_id)
  users = query_all_active_users(company_id)
  organizations = query_organizations(company_id)

  IF employees is empty:
    RETURN single_node_tree(company_id)
    # Just BOD + D1 (Company) + R1 (Owner, vacant if no owner user)

  # ── Phase 2: Identify the Root ────────────────────────────────

  # The owner is the organizational root
  owner_user = find_user_with_role(users, "owner")
  owner_employee = find_employee_by_user_id(employees, owner_user.id) IF owner_user ELSE None

  # If no owner user exists (shouldn't happen), pick the employee
  # with no reporting_manager_id and the highest seniority designation
  IF owner_employee is None:
    root_candidates = [e for e in employees if e.reporting_manager_id is None]
    IF root_candidates:
      owner_employee = pick_highest_seniority(root_candidates)
    ELSE:
      # Everyone reports to someone — pick the one at the top of the longest chain
      owner_employee = find_chain_root(employees)

  # ── Phase 3: Discover Departments ─────────────────────────────

  # Group employees by department
  dept_groups = group_by(employees, key="department")

  # Filter out empty/blank departments — those employees go under root
  named_depts = {k: v for k, v in dept_groups.items() if k and k.strip()}
  orphan_employees = dept_groups.get("", []) + dept_groups.get(None, [])

  # Also check Organization model for departments not yet populated by employees
  org_depts = {org.name: org for org in organizations}

  # Merge: use employee-derived departments as primary, org model as supplement
  all_dept_names = set(named_depts.keys()) | set(org_depts.keys())

  # ── Phase 4: Identify Department Heads ────────────────────────

  dept_heads = {}  # dept_name -> employee

  FOR each dept_name in all_dept_names:
    dept_employees = named_depts.get(dept_name, [])

    IF len(dept_employees) == 0:
      # Department exists in Organization model but has no employees
      dept_heads[dept_name] = None  # Vacant head
      CONTINUE

    IF len(dept_employees) == 1:
      dept_heads[dept_name] = dept_employees[0]
      CONTINUE

    # Multiple employees — find the head
    # Strategy 1: The employee whose reporting_manager_id points OUTSIDE the department
    external_reporters = []
    FOR e in dept_employees:
      IF e.reporting_manager_id is None:
        external_reporters.append(e)
      ELIF find_employee_by_id(e.reporting_manager_id) not in dept_employees:
        external_reporters.append(e)

    IF len(external_reporters) == 1:
      dept_heads[dept_name] = external_reporters[0]
      CONTINUE

    IF len(external_reporters) > 1:
      # Multiple people report outside — pick highest seniority
      dept_heads[dept_name] = pick_highest_seniority(external_reporters)
      dept_heads[dept_name]._is_inferred = True
      CONTINUE

    # Strategy 2: Everyone reports within the department — find the one
    # at the top of the intra-department chain
    IF len(external_reporters) == 0:
      top = find_chain_root_within(dept_employees)
      dept_heads[dept_name] = top
      dept_heads[dept_name]._is_inferred = True
      CONTINUE

  # ── Phase 5: Build Reporting Chains ───────────────────────────

  # Within each department, order employees by reporting chain
  dept_members = {}  # dept_name -> ordered list of (employee, parent_employee)

  FOR each dept_name, head in dept_heads.items():
    dept_employees = named_depts.get(dept_name, [])
    members_excl_head = [e for e in dept_employees if e != head]

    # Build chain: who reports to whom within this department
    chain = build_reporting_chain(head, members_excl_head)
    dept_members[dept_name] = chain

  # ── Phase 6: Assemble PACT Tree ──────────────────────────────

  tree = PactTree()

  # BOD (governance root — vacant for SMEs)
  tree.add_node(PactNode(type="BOD", name="Board", is_vacant=True))

  # D1 (Company)
  d1 = tree.add_node(PactNode(type="D", name=company_name))

  # D1-R1 (Owner/Director)
  r1 = tree.add_child(d1, PactNode(
    type="R",
    name=owner_employee.designation or "Director",
    employee_id=owner_employee.id if owner_employee else None,
    is_primary_head=True,
    is_vacant=(owner_employee is None),
  ))

  # Departments as sub-D nodes under the owner
  dept_counter = 1
  FOR each dept_name in sorted(all_dept_names):
    head = dept_heads[dept_name]
    members = dept_members.get(dept_name, [])

    # Skip the department containing the owner (they're already D1-R1)
    IF head == owner_employee:
      # Add members directly under D1-R1
      member_counter = 2  # R1 is the owner
      FOR member, parent in members:
        tree.add_child(r1, PactNode(
          type="R",
          name=member.designation or "Staff",
          employee_id=member.id,
        ))
      CONTINUE

    # Create department node
    d_dept = tree.add_child(r1, PactNode(
      type="D",
      name=dept_name,
    ))

    # Department head
    r_head = tree.add_child(d_dept, PactNode(
      type="R",
      name=head.designation if head else f"{dept_name} Head",
      employee_id=head.id if head else None,
      is_primary_head=True,
      is_vacant=(head is None),
      is_inferred=getattr(head, '_is_inferred', False) if head else True,
    ))

    # Department members
    FOR member, parent in members:
      parent_node = find_node_by_employee(tree, parent.id) if parent else r_head
      tree.add_child(parent_node, PactNode(
        type="R",
        name=member.designation or "Staff",
        employee_id=member.id,
      ))

  # Orphan employees (no department) go directly under owner
  FOR orphan in orphan_employees:
    IF orphan == owner_employee:
      CONTINUE
    tree.add_child(r1, PactNode(
      type="R",
      name=orphan.designation or "Staff",
      employee_id=orphan.id,
    ))

  # ── Phase 7: Compute Addresses ───────────────────────────────

  tree.compute_addresses()  # Traverses tree, assigns D1-R1-D2-R1-R2 etc.

  RETURN tree
```

### 1.3 Seniority Ranking

When the algorithm must infer who is the head of a department:

```
SENIORITY_KEYWORDS = [
  # Rank 1 (highest)
  ("director", 1), ("managing director", 1), ("ceo", 1), ("coo", 1),
  ("cfo", 1), ("cto", 1), ("md", 1), ("gm", 1), ("general manager", 1),

  # Rank 2
  ("manager", 2), ("head", 2), ("chief", 2), ("vp", 2),

  # Rank 3
  ("supervisor", 3), ("team lead", 3), ("lead", 3), ("senior", 3),
  ("principal", 3),

  # Rank 4
  ("officer", 4), ("specialist", 4), ("analyst", 4),

  # Rank 5
  ("executive", 5), ("coordinator", 5), ("associate", 5),

  # Rank 6
  ("assistant", 6), ("clerk", 6), ("admin", 6),

  # Rank 7 (lowest)
  ("intern", 7), ("trainee", 7), ("temp", 7), ("staff", 7),
]

FUNCTION pick_highest_seniority(employees: list) -> Employee:
  best = employees[0]
  best_rank = 99

  FOR e in employees:
    designation_lower = e.designation.lower()
    FOR keyword, rank in SENIORITY_KEYWORDS:
      IF keyword in designation_lower AND rank < best_rank:
        best = e
        best_rank = rank
        BREAK

  RETURN best
```

### 1.4 Handling Special Cases

**Case: Ah Mei (multi-function role)**

Ah Mei is in department "Admin" but does HR, finance, and admin work. The algorithm places her in Admin as the head. Her cross-functional access is handled by bridges (see section 4.3 of the design doc) that the shadow agent will suggest based on observation.

**Case: Matrix reporting (employee reports to two managers)**

The `reporting_manager_id` field allows only one manager. PACT-lite uses this as the primary chain. If the shadow agent observes regular cross-department interaction, it suggests a bridge (secondary access path).

**Case: Department name variants**

The algorithm normalizes department names before grouping:

```
normalize("Human Resources") == normalize("HR") == normalize("human resources")
normalize("Information Technology") == normalize("IT") == normalize("Tech")
```

Normalization table (hardcoded for Singapore SME context):

```
DEPT_ALIASES = {
  "hr": "Human Resources",
  "human resource": "Human Resources",
  "it": "Technology",
  "tech": "Technology",
  "information technology": "Technology",
  "ops": "Operations",
  "finance": "Finance",
  "accounts": "Finance",
  "accounting": "Finance",
  "admin": "Administration",
  "administration": "Administration",
  "sales": "Sales",
  "marketing": "Marketing",
  "sales & marketing": "Sales & Marketing",
  "smk": "Sales & Marketing",
  "eng": "Engineering",
  "engineering": "Engineering",
}
```

---

## 2. Template Envelope Matching from Job Titles

### 2.1 Algorithm: match_envelope_template(employee)

```
FUNCTION match_envelope_template(employee: Employee, user: User) -> str:

  # ── Priority 1: User role override ────────────────────────────
  # The User.role field is authoritative for platform-level access

  IF user.role == "owner":
    RETURN "tmpl_owner"

  IF user.role == "hr_manager":
    RETURN "tmpl_hr_manager"

  IF user.role == "consultant":
    RETURN "tmpl_employee_office"  # Consultant gets read-heavy office template

  # ── Priority 2: Designation-based matching ────────────────────

  designation = normalize_designation(employee.designation)

  # Exact keyword match (check all templates)
  FOR template_id, keywords in TEMPLATE_KEYWORDS.items():
    IF any(kw in designation for kw in keywords):
      RETURN template_id

  # ── Priority 3: Department-based inference ────────────────────

  department = normalize_department(employee.department)

  DEPT_TO_TEMPLATE = {
    "Human Resources": "tmpl_hr_exec",
    "Finance": "tmpl_payroll_officer",
    "Operations": "tmpl_employee_field",
    "Technology": "tmpl_employee_office",
    "Sales": "tmpl_employee_office",
    "Marketing": "tmpl_employee_office",
    "Administration": "tmpl_employee_office",
  }

  IF department in DEPT_TO_TEMPLATE:
    RETURN DEPT_TO_TEMPLATE[department]

  # ── Priority 4: Safe default ──────────────────────────────────

  RETURN "tmpl_employee_office"


FUNCTION normalize_designation(designation: str) -> str:
  d = designation.lower().strip()
  # Remove common prefixes that don't affect template selection
  FOR prefix in ["senior ", "junior ", "lead ", "assistant ", "deputy "]:
    d = d.removeprefix(prefix)
  RETURN d
```

### 2.2 Template Keyword Registry

```
TEMPLATE_KEYWORDS = {
  "tmpl_owner": [
    "director", "managing director", "ceo", "owner", "founder",
    "chief executive", "md",
  ],
  "tmpl_hr_manager": [
    "hr manager", "hr director", "people manager", "admin manager",
    "human resource manager", "head of hr", "head of people",
  ],
  "tmpl_hr_exec": [
    "hr executive", "hr officer", "hr admin", "admin executive",
    "hr coordinator", "people operations",
  ],
  "tmpl_finance_manager": [
    "finance manager", "cfo", "financial controller", "accounts manager",
    "head of finance", "finance director", "chief financial",
  ],
  "tmpl_payroll_officer": [
    "payroll officer", "payroll executive", "payroll admin",
    "payroll specialist", "compensation",
  ],
  "tmpl_ops_manager": [
    "operations manager", "coo", "production manager", "warehouse manager",
    "logistics manager", "plant manager", "facilities manager",
  ],
  "tmpl_supervisor": [
    "supervisor", "team lead", "team leader", "shift supervisor",
    "section head", "foreman", "charge hand",
  ],
  "tmpl_sales_manager": [
    "sales manager", "business development", "account manager",
    "sales director", "head of sales", "commercial manager",
  ],
  "tmpl_it_manager": [
    "it manager", "tech lead", "systems administrator", "cto",
    "head of technology", "it director", "devops",
  ],
  "tmpl_employee_office": [
    "executive", "officer", "coordinator", "assistant", "clerk",
    "administrator", "analyst", "specialist", "associate",
  ],
  "tmpl_employee_field": [
    "technician", "driver", "worker", "operator", "installer",
    "mechanic", "electrician", "plumber", "cleaner", "helper",
    "packer", "assembler", "labourer",
  ],
  "tmpl_employee_self": [
    "intern", "trainee", "part-timer", "temp", "attachment",
    "volunteer", "relief",
  ],
}
```

### 2.3 Monotonic Tightening Validation

After template matching, the system validates that the assigned envelope is tighter than the parent's:

```
FUNCTION validate_envelope_tightening(child_envelope, parent_envelope) -> bool:

  # Financial: child limits must be <= parent limits
  IF child.financial.max_per_action > parent.financial.max_per_action:
    RETURN False
  IF child.financial.daily_cumulative > parent.financial.daily_cumulative:
    RETURN False

  # Operational: child allowed actions must be subset of parent
  IF NOT child.operational.allowed_actions.issubset(parent.operational.allowed_actions):
    RETURN False
  # Child blocked actions must be superset of parent
  IF NOT child.operational.blocked_actions.issuperset(parent.operational.blocked_actions):
    RETURN False

  # Data access: child max_classification must be <= parent
  IF clearance_rank(child.data_access.max_classification) > clearance_rank(parent.data_access.max_classification):
    RETURN False

  # Temporal: child operating hours must be within parent hours
  IF NOT is_time_subset(child.temporal.operating_hours, parent.temporal.operating_hours):
    RETURN False

  # Communication: child recipients must be subset of parent
  IF NOT child.communication.allowed_recipients.issubset(parent.communication.allowed_recipients):
    RETURN False

  RETURN True

CLEARANCE_RANKS = {
  "public": 0,
  "restricted": 1,
  "confidential": 2,
  "secret": 3,
  "top_secret": 4,
}
```

If validation fails, the child envelope is automatically tightened to match the parent's constraint in the violated dimension. This handles cases where a template is too broad for the position in the hierarchy.

---

## 3. Knowledge Clearance Auto-Classification

### 3.1 Model Classification Algorithm

The classification is static (computed once at system init) and stored in a registry:

```
FUNCTION build_model_clearance_registry() -> dict[str, str]:

  registry = {}

  # ── Rule 1: Models with PII fields → CONFIDENTIAL ────────────

  PII_FIELD_PATTERNS = [
    "nric", "fin", "bank_account", "salary", "encrypted",
    "tax_reference", "bank_code",
  ]

  FOR model in all_dataflow_models():
    has_pii = False
    FOR field in model.fields:
      IF any(pattern in field.name.lower() for pattern in PII_FIELD_PATTERNS):
        has_pii = True
        BREAK

    IF has_pii:
      registry[model.name] = "confidential"
      CONTINUE

    # ── Rule 2: Models referenced by PdpaAccessLog → CONFIDENTIAL

    IF model.name in PDPA_ACCESSED_MODELS:
      registry[model.name] = "confidential"
      CONTINUE

    # ── Rule 3: Personal data models → RESTRICTED ───────────────

    PERSONAL_INDICATORS = [
      "employee_id",  # Has employee_id but not PII → personal but not sensitive
    ]

    is_personal = any(
      field.name in PERSONAL_INDICATORS
      for field in model.fields
    )
    IF is_personal:
      registry[model.name] = "restricted"
      CONTINUE

    # ── Rule 4: Everything else → PUBLIC ────────────────────────

    registry[model.name] = "public"

  # ── Manual overrides for nuanced cases ────────────────────────

  MANUAL_OVERRIDES = {
    # Models that have employee_id but are organizational, not personal
    "CompanyPolicy": "public",
    "PublicHoliday": "public",
    "Organization": "public",
    "Branch": "public",
    "HolidayGroup": "public",
    "LeaveTypeConfig": "public",
    "ShiftTemplate": "public",
    "ClaimCategory": "public",
    "AppraisalTemplate": "public",
    "AppraisalPeriod": "public",
    "CostCentre": "public",
    "Project": "public",
    "ProjectRole": "public",
    "JobListing": "public",
    "Template": "public",
    "ContentUpdate": "public",
    "InventoryLocation": "public",
    "InventoryCategory": "public",
    "PayItem": "public",
    "PayScheme": "public",
    "AttendanceSettings": "public",
    "LatenessSettings": "public",
    "EarlyDepartureSettings": "public",
    "ShiftHourlyRate": "public",
    "ShiftMultiplier": "public",
    "PayslipSettings": "public",
    "ApprovalGroup": "public",
    "Company": "public",

    # Models that are personal but not PII
    "Conversation": "restricted",
    "AdvisorySession": "restricted",
    "Invitation": "restricted",
    "AdminPermission": "restricted",

    # Models with PII
    "Employee": "confidential",  # Contains NRIC, bank, salary fields
    "SalaryComponent": "confidential",
    "Payslip": "confidential",
    "PayslipItem": "confidential",
    "PayrollRun": "confidential",
    "PayrollLineItem": "confidential",
    "CpfYtdRecord": "confidential",
    "TaxFiling": "confidential",
    "FamilyMember": "confidential",
    "EmergencyContact": "confidential",
    "PdpaAccessLog": "confidential",
  }

  FOR model_name, clearance in MANUAL_OVERRIDES.items():
    registry[model_name] = clearance

  RETURN registry

PDPA_ACCESSED_MODELS = {
  "Employee",  # NRIC, bank account, salary, work pass
  "FamilyMember",  # NRIC
  "Candidate",  # NRIC
}
```

### 3.2 Field-Level Classification

Some models have mixed clearance at the field level. The Employee model is the primary example:

```
FIELD_CLEARANCE_OVERRIDES = {
  "Employee": {
    # PUBLIC fields (visible in org chart / directory)
    "name": "public",       # Via User.name
    "department": "public",
    "designation": "public",
    "photo_url": "public",
    "alias": "public",

    # RESTRICTED fields (visible to team + HR)
    "employment_type": "restricted",
    "start_date": "restricted",
    "confirmation_status": "restricted",
    "reporting_manager_id": "restricted",
    "working_hours_type": "restricted",

    # CONFIDENTIAL fields (HR/Finance only, PDPA-logged)
    "nric_fin": "confidential",
    "nric_fin_last4": "confidential",
    "salary_monthly": "confidential",
    "bank_name": "confidential",
    "bank_account_number": "confidential",
    "bank_account_last4": "confidential",
    "bank_code": "confidential",
    "branch_code": "confidential",
    "tax_reference": "confidential",
    "date_of_birth": "confidential",
    "gender": "confidential",
    "marital_status": "confidential",
    "race": "confidential",
    "religion": "confidential",
    "residential_address": "confidential",
    "postal_code": "confidential",
    "work_pass_number": "confidential",
    "work_pass_expiry": "confidential",
    "immigration_status": "confidential",
    "phone": "confidential",
    "hourly_rate": "confidential",
    "daily_rate": "confidential",
    "cpf_status": "confidential",
  },
}
```

### 3.3 Access Decision Algorithm

When a user accesses a model or field, the system checks:

```
FUNCTION can_access(
  user_pact_address: str,
  user_clearance: str,
  target_model: str,
  target_field: str | None,
  target_employee_id: int | None,
  requesting_user_id: int,
) -> AccessDecision:

  # Step 1: Determine required clearance
  model_clearance = MODEL_CLEARANCE_REGISTRY[target_model]

  IF target_field and target_model in FIELD_CLEARANCE_OVERRIDES:
    field_clearance = FIELD_CLEARANCE_OVERRIDES[target_model].get(target_field)
    IF field_clearance:
      required_clearance = max_clearance(model_clearance, field_clearance)
    ELSE:
      required_clearance = model_clearance
  ELSE:
    required_clearance = model_clearance

  # Step 2: Check clearance level
  IF clearance_rank(user_clearance) < clearance_rank(required_clearance):

    # Exception: employees can always access their own data
    IF target_employee_id and is_own_employee_record(requesting_user_id, target_employee_id):
      RETURN AccessDecision(
        allowed=True,
        reason="own_record",
        log_pdpa=True if required_clearance >= "confidential" else False,
      )

    RETURN AccessDecision(
      allowed=False,
      reason=f"Requires {required_clearance} clearance, you have {user_clearance}",
      gradient_zone="blocked",
    )

  # Step 3: Check containment (is this within the user's organizational scope?)
  IF target_employee_id:
    target_address = get_employee_pact_address(target_employee_id)
    IF NOT is_in_scope(user_pact_address, target_address):
      # User is trying to access data outside their org subtree
      # Check for bridges or KSPs
      IF has_bridge_or_ksp(user_pact_address, target_address):
        RETURN AccessDecision(allowed=True, reason="bridge", log_pdpa=True)
      ELSE:
        RETURN AccessDecision(
          allowed=False,
          reason="Outside your organizational scope",
          gradient_zone="blocked",
        )

  # Step 4: Log PDPA access if needed
  RETURN AccessDecision(
    allowed=True,
    reason="clearance_sufficient",
    log_pdpa=(required_clearance >= "confidential"),
  )
```

---

## 4. Shadow Agent Observation to Envelope Refinement Loop

### 4.1 Extended Observation Schema

The current `ObservationStore` records `{user_id, page, action_type, details, timestamp}`. PACT-lite extends this:

```
PactObservation = {
  # Existing fields
  user_id: str,
  page: str,
  action_type: str,
  details: dict,
  timestamp: str,
  session_id: str,

  # PACT extension fields
  pact_address: str,           # User's PACT address at time of action
  module: str,                 # Shadow agent module (employees, payroll, etc.)
  action: str,                 # Specific action (list, create, approve, etc.)
  target_model: str,           # DataFlow model accessed
  target_clearance: str,       # Clearance level of accessed data
  target_employee_id: int,     # If accessing another employee's data
  envelope_result: str,        # "auto" / "flagged" / "held" / "blocked"
  was_approved: bool | None,   # If held, was it approved by supervisor?
  approval_time_seconds: int,  # Time from hold to approval (if applicable)
  cross_department: bool,      # Was this a cross-department access?
  is_routine: bool,            # Does this match the user's established pattern?
}
```

### 4.2 Pattern Detection Engine

The inference engine runs periodically (every 24 hours) and on-demand when triggered by significant events:

```
FUNCTION detect_patterns(company_id: int, user_id: str) -> list[PactPattern]:

  observations = get_recent_observations(user_id, days=30)
  patterns = []

  # ── Pattern 1: Consistent Hold-then-Approve ──────────────────
  # If a user's actions are consistently held and then approved by
  # their supervisor, suggest widening the envelope.

  held_observations = [o for o in observations if o.envelope_result == "held"]
  approved_holds = [o for o in held_observations if o.was_approved]

  # Group by action type
  action_groups = group_by(approved_holds, key=lambda o: (o.module, o.action))

  FOR (module, action), group in action_groups.items():
    IF len(group) >= 3:  # At least 3 occurrences
      avg_approval_time = mean(o.approval_time_seconds for o in group)
      IF avg_approval_time < 300:  # Average approval under 5 minutes
        patterns.append(PactPattern(
          type="envelope_too_tight",
          module=module,
          action=action,
          evidence_count=len(group),
          avg_approval_time=avg_approval_time,
          suggestion=f"Allow {action} in {module} without supervisor approval",
          confidence=min(0.95, len(group) / 10),  # Caps at 95%
        ))

  # ── Pattern 2: Frequent Cross-Department Access ───────────────
  # If a user regularly accesses data in another department,
  # suggest a bridge or clearance adjustment.

  cross_dept = [o for o in observations if o.cross_department]
  cross_dept_groups = group_by(cross_dept, key="target_model")

  FOR target_model, group in cross_dept_groups.items():
    IF len(group) >= 5:  # At least 5 cross-department accesses
      patterns.append(PactPattern(
        type="cross_department_access",
        target_model=target_model,
        evidence_count=len(group),
        suggestion=f"Grant formal access to {target_model} data",
        confidence=min(0.90, len(group) / 15),
      ))

  # ── Pattern 3: Blocked Action Retry ───────────────────────────
  # If a user repeatedly attempts a blocked action, they may need
  # a clearance upgrade.

  blocked = [o for o in observations if o.envelope_result == "blocked"]
  blocked_groups = group_by(blocked, key=lambda o: (o.module, o.action))

  FOR (module, action), group in blocked_groups.items():
    IF len(group) >= 2:  # Attempted twice or more
      patterns.append(PactPattern(
        type="blocked_needs_clearance",
        module=module,
        action=action,
        evidence_count=len(group),
        suggestion=f"This person may need access to {action} in {module}",
        confidence=min(0.80, len(group) / 5),
      ))

  # ── Pattern 4: Anomalous Behavior ────────────────────────────
  # Deviation from established baseline.

  baseline = get_user_baseline(user_id)  # 30-day rolling average
  today_activity = get_today_observations(user_id)

  IF baseline:
    # Data volume anomaly
    today_access_count = len(today_activity)
    baseline_daily_avg = baseline.daily_access_count
    IF today_access_count > baseline_daily_avg * 3:
      patterns.append(PactPattern(
        type="anomalous_volume",
        evidence_count=today_access_count,
        baseline_value=baseline_daily_avg,
        suggestion=f"Unusual data access volume today ({today_access_count} vs avg {baseline_daily_avg})",
        confidence=0.70,
      ))

    # New module access
    today_modules = set(o.module for o in today_activity)
    baseline_modules = set(baseline.typical_modules)
    new_modules = today_modules - baseline_modules
    IF new_modules:
      patterns.append(PactPattern(
        type="new_module_access",
        new_modules=list(new_modules),
        suggestion=f"First time accessing {', '.join(new_modules)}",
        confidence=0.60,
      ))

  # ── Pattern 5: Unused Permissions ─────────────────────────────
  # If an envelope grants access that is never used after 60 days,
  # suggest tightening.

  current_envelope = get_envelope(user_id)
  used_actions = set((o.module, o.action) for o in observations)
  allowed_actions = set(current_envelope.all_allowed_actions())
  unused = allowed_actions - used_actions

  IF len(unused) > len(allowed_actions) * 0.5:  # >50% of permissions unused
    patterns.append(PactPattern(
      type="unused_permissions",
      unused_count=len(unused),
      total_count=len(allowed_actions),
      suggestion="Over half of this person's permissions are unused",
      confidence=0.50,  # Low confidence — absence of usage isn't proof of non-need
    ))

  RETURN patterns
```

### 4.3 Suggestion Generation

Patterns are converted to suggestions with a confidence threshold:

```
FUNCTION generate_suggestions(patterns: list[PactPattern], company_id: int) -> list[PactSuggestion]:

  suggestions = []

  FOR pattern in patterns:
    # Only surface high-confidence suggestions
    IF pattern.confidence < 0.70:
      CONTINUE

    # Check if a similar suggestion was already dismissed
    existing = find_similar_suggestion(company_id, pattern)
    IF existing and existing.dismiss_count >= 3:
      CONTINUE  # Stop suggesting after 3 dismissals
    IF existing and existing.status == "pending":
      CONTINUE  # Don't create duplicate

    # Generate human-readable suggestion
    suggestion = PactSuggestion(
      company_id=company_id,
      suggestion_type=pattern.type,
      title=pattern_to_title(pattern),
      description=pattern_to_description(pattern),
      evidence={
        "pattern_type": pattern.type,
        "evidence_count": pattern.evidence_count,
        "confidence": pattern.confidence,
        "observation_window_days": 30,
      },
      proposed_changes=pattern_to_changes(pattern),
      status="pending",
      target_address=get_target_address(pattern),
    )

    suggestions.append(suggestion)

  RETURN suggestions
```

### 4.4 Suggestion Titles and Descriptions (UX Copy)

```
FUNCTION pattern_to_title(pattern: PactPattern) -> str:

  MATCH pattern.type:
    CASE "envelope_too_tight":
      RETURN f"Streamline {pattern.module} approvals"

    CASE "cross_department_access":
      RETURN "Set up data sharing between teams"

    CASE "blocked_needs_clearance":
      RETURN "Update permissions for a team member"

    CASE "anomalous_volume":
      RETURN "Unusual activity detected"

    CASE "unused_permissions":
      RETURN "Review team permissions"

    CASE "new_module_access":
      RETURN "New area being used"


FUNCTION pattern_to_description(pattern: PactPattern) -> str:

  MATCH pattern.type:
    CASE "envelope_too_tight":
      user_name = get_user_name(pattern.user_id)
      RETURN (
        f"{user_name} regularly does {pattern.action} in {pattern.module}, "
        f"and you've approved it every time ({pattern.evidence_count} times "
        f"this month, usually within {format_duration(pattern.avg_approval_time)}). "
        f"Want to let them do this directly?"
      )

    CASE "cross_department_access":
      user_name = get_user_name(pattern.user_id)
      RETURN (
        f"{user_name} has been accessing {pattern.target_model} data "
        f"{pattern.evidence_count} times this month. This is outside their "
        f"normal team scope. Want to give them formal access?"
      )

    CASE "blocked_needs_clearance":
      user_name = get_user_name(pattern.user_id)
      RETURN (
        f"{user_name} has tried to {pattern.action} in {pattern.module} "
        f"{pattern.evidence_count} times but doesn't have permission. "
        f"If this is part of their job, you can grant access."
      )

    CASE "anomalous_volume":
      user_name = get_user_name(pattern.user_id)
      RETURN (
        f"{user_name} accessed {pattern.evidence_count} records today, "
        f"compared to their usual {pattern.baseline_value} per day. "
        f"This is logged for audit purposes. No action needed if "
        f"this was for legitimate work."
      )

    CASE "unused_permissions":
      RETURN (
        f"More than half of this person's system permissions haven't been "
        f"used in the past 60 days. You might want to review whether "
        f"they still need this level of access."
      )
```

### 4.5 Confirmation and Enforcement

When a suggestion is accepted:

```
FUNCTION apply_suggestion(suggestion: PactSuggestion, confirmed_by: int) -> None:

  changes = suggestion.proposed_changes

  MATCH suggestion.suggestion_type:

    CASE "envelope_too_tight":
      # Widen the envelope for the target role
      envelope = get_envelope(suggestion.target_address)
      envelope.operational.allowed_action_types.add(changes["add_action"])
      save_envelope(envelope)

      # Create EATP audit record
      create_eatp_delegation_record(
        delegator=get_parent_address(suggestion.target_address),
        delegate=suggestion.target_address,
        change="envelope_widened",
        details=changes,
      )

    CASE "cross_department_access":
      # Create a bridge between departments
      create_bridge(
        from_address=suggestion.target_address,
        to_department=changes["target_department"],
        scope=changes["access_scope"],
      )

    CASE "blocked_needs_clearance":
      # Upgrade clearance for the target role
      clearance = get_clearance(suggestion.target_address)
      clearance.max_clearance = changes["new_clearance"]
      save_clearance(clearance)

  # Mark suggestion as accepted
  suggestion.status = "accepted"
  suggestion.resolved_at = now()
  suggestion.resolved_by = confirmed_by
  save_suggestion(suggestion)

  # Create audit event
  create_pact_audit_event(
    event_type="suggestion_accepted",
    actor_address=get_user_pact_address(confirmed_by),
    target_address=suggestion.target_address,
    details={"suggestion_id": suggestion.id, "changes": changes},
  )
```

---

## 5. Complete Model Clearance Registry

For reference, here is the complete mapping of all 77 DataFlow models to PACT clearance levels using the correct EATP naming convention (PUBLIC / RESTRICTED / CONFIDENTIAL / SECRET / TOP_SECRET):

```python
MODEL_CLEARANCE_REGISTRY = {
    # ── PUBLIC (C0) — Organizational knowledge ──────────────────
    "Company": "public",
    "CompanyPolicy": "public",
    "PublicHoliday": "public",
    "Organization": "public",
    "Branch": "public",
    "HolidayGroup": "public",
    "LeaveTypeConfig": "public",
    "ShiftTemplate": "public",
    "ClaimCategory": "public",
    "AppraisalTemplate": "public",
    "AppraisalPeriod": "public",
    "CostCentre": "public",
    "Project": "public",
    "ProjectRole": "public",
    "JobListing": "public",
    "Template": "public",
    "ContentUpdate": "public",
    "InventoryLocation": "public",
    "InventoryCategory": "public",
    "PayItem": "public",
    "PayScheme": "public",
    "AttendanceSettings": "public",
    "LatenessSettings": "public",
    "EarlyDepartureSettings": "public",
    "ShiftHourlyRate": "public",
    "ShiftMultiplier": "public",
    "PayslipSettings": "public",
    "ApprovalGroup": "public",

    # ── RESTRICTED (C1) — Personal data, team + HR access ──────
    "User": "restricted",
    "Conversation": "restricted",
    "AdvisorySession": "restricted",
    "LeaveApplication": "restricted",
    "LeaveBalance": "restricted",
    "LeavePolicy": "restricted",
    "LeavePolicyEntitlement": "restricted",
    "AttendanceRecord": "restricted",
    "TimesheetApproval": "restricted",
    "ShiftAssignment": "restricted",
    "ShiftPublish": "restricted",
    "Claim": "restricted",
    "ClaimItem": "restricted",
    "ClaimGroup": "restricted",
    "ClaimAuditEntry": "restricted",
    "EmployeeSkill": "restricted",
    "EmployeeEvent": "restricted",
    "EmployeeNote": "restricted",
    "EmploymentEvent": "restricted",
    "CustomFieldValue": "restricted",
    "CustomFieldDefinition": "restricted",
    "ProjectAssignment": "restricted",
    "ProjectAllocation": "restricted",
    "ProjectOverhead": "restricted",
    "TimesheetEntry": "restricted",
    "InventoryItem": "restricted",
    "InventoryMovement": "restricted",
    "InventoryRequest": "restricted",
    "Appraisal": "restricted",
    "Candidate": "restricted",
    "InterviewSchedule": "restricted",
    "InterviewFeedback": "restricted",
    "Invitation": "restricted",
    "CompanyLLMConfig": "restricted",
    "CompanyLLMUsage": "restricted",
    "UserLLMConfig": "restricted",
    "AdminPermission": "restricted",

    # ── CONFIDENTIAL (C2) — PII, PDPA-logged ───────────────────
    "Employee": "confidential",
    "SalaryComponent": "confidential",
    "Payslip": "confidential",
    "PayslipItem": "confidential",
    "PayrollRun": "confidential",
    "PayrollLineItem": "confidential",
    "CpfYtdRecord": "confidential",
    "TaxFiling": "confidential",
    "FamilyMember": "confidential",
    "EmergencyContact": "confidential",
    "EmployeeDocument": "confidential",
    "PdpaAccessLog": "confidential",

    # ── SECRET (C3) — Not auto-assigned ─────────────────────────
    # Applied to individual records only (medical certs, etc.)

    # ── TOP_SECRET (C4) — Not used in SME context ──────────────
}
```
