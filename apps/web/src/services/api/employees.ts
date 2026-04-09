/* ── Employees API Service ────────────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface Employee {
  id: number;
  name: string;
  email: string;
  department: string;
  designation?: string;
  job_title?: string;
  status: "active" | "invited" | "inactive" | "terminated";
  is_active?: boolean;
  start_date?: string;
  employment_type?: string;
  confirmation_status?: string;
}

export interface EmployeeRecord {
  id: number;
  name: string;
  email: string;
  department: string;
  job_title: string;
  start_date: string;
  employment_type: string;
}

export interface EmployeeDetail {
  id: number;
  user_id: number;
  company_id: number;
  email: string;
  name: string;
  employee_id_internal: string;
  department: string;
  designation: string;
  employment_type: string;
  start_date: string;
  end_date: string;
  nationality: string;
  pass_type: string;
  salary_monthly: number;
  salary_type: string;
  payment_method: string;
  payment_frequency: string;
  working_hours_type: string;
  overtime_eligible: boolean;
  tags: string;
  notice_period_days: number;
  is_active: boolean;
  /* Tax & CPF */
  iras_auto_inclusion: string;
  tax_reference: string;
  cpf_status: string;
  /* Personal */
  date_of_birth: string;
  gender: string;
  marital_status: string;
  race: string;
  /* Identity (masked) */
  nric_fin: string;
  nric_fin_last4: string;
  /* Work pass */
  work_pass_number: string;
  work_pass_expiry: string;
  immigration_status: string;
  immigration_effective_date: string;
  /* Banking (masked) */
  bank_name: string;
  bank_account_number: string;
  bank_account_last4: string;
  bank_code: string;
  /* Address */
  residential_address: string;
  postal_code: string;
  /* Org */
  reporting_manager_id: number | null;
  /* Probation */
  probation_months: number;
  probation_end_date: string;
  confirmation_status: string;
}

export interface SalaryComponent {
  id: number;
  component_type: string;
  name: string;
  amount: number;
  frequency: string;
  is_taxable: boolean;
  is_cpf_applicable: boolean;
  effective_from: string;
  effective_to: string;
  is_active: boolean;
}

export interface EmergencyContact {
  id: number;
  name: string;
  relationship: string;
  phone_primary: string;
  phone_secondary: string;
  email: string;
  is_next_of_kin: boolean;
  priority: number;
}

export interface EmploymentEvent {
  id: number;
  event_type: string;
  event_date: string;
  description: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  effective_date: string;
  notes: string;
}

export interface EmployeeDocument {
  id: number;
  document_type: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  description: string;
  is_confidential: boolean;
  expiry_date?: string;
  uploaded_at?: string;
}

export interface LeaveBalance {
  leave_type: string;
  year: number;
  entitlement_days: number;
  used_days: number;
  pending_days: number;
}

export interface CompanyPolicy {
  id: string;
  title: string;
  summary: string;
  content: string[];
  category?: string;
}

export interface InviteEmployeeData {
  email: string;
  role: string;
  department?: string;
  designation?: string;
}

export interface InviteResponse {
  message: string;
  invite_url: string;
}

export interface Invitation {
  id: number;
  email: string;
  role: string;
  status: "pending" | "expired" | "accepted" | "revoked";
  created_at: string;
  expires_at: string;
  invite_url?: string;
}

export interface InviteValidation {
  email: string;
  company_name: string;
  role: string;
  status: string;
}

export interface FamilyMember {
  id: number;
  employee_id: number;
  name: string;
  relationship: string;
  date_of_birth: string;
  gender: string;
  citizenship_status: string;
  nric_fin?: string;
  nric_fin_last4?: string;
}

export interface EmployeeNote {
  id: number;
  employee_id: number;
  note_type: string;
  content: string;
  created_by: number;
  is_confidential: boolean;
  created_at?: string;
}

export interface EmployeeSkill {
  id: number;
  employee_id: number;
  skill_name: string;
  proficiency_level: string;
  certification_name: string;
  certification_number: string;
  certified_date: string;
  expiry_date: string;
  issuing_body: string;
}

export interface CustomFieldDefinition {
  id: number;
  company_id: number;
  field_name: string;
  field_label: string;
  field_type: string;
  dropdown_options: string;
  is_required: boolean;
  display_order: number;
  applies_to: string;
}

export interface CustomFieldValue {
  id: number;
  entity_type: string;
  entity_id: number;
  field_definition_id: number;
  value: string;
}

export interface AdminLeaveBalance {
  leave_type: string;
  year: number;
  entitlement_days: number;
  used_days: number;
  pending_days: number;
}

export interface ExitSettlement {
  employee_id: number;
  exit_type: string;
  last_working_day: string;
  notice_served: boolean;
  breakdown: {
    prorated_salary: number;
    leave_encashment: {
      unused_days: number;
      daily_rate: number;
      amount: number;
    };
    notice_period: {
      notice_period_days: number;
      shortfall_days: number;
      amount: number;
      note: string;
    };
    retrenchment_benefit: {
      amount: number;
      explanation: string;
    } | null;
  };
  total_settlement: number;
  message: string;
}

/* ── Public (no-auth) helpers ─────────────────────────────── */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Validate an employee invitation token.
 * This is a public endpoint — no auth token required.
 * Throws an object with `status` and `message` on failure so callers
 * can distinguish expired / already-used / invalid states.
 */
export async function validateInvite(token: string): Promise<InviteValidation> {
  const response = await fetch(`${API_BASE}/employees/invite/${token}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!response.ok) {
    let message = "This invitation link is not valid.";
    try {
      const body = await response.json();
      // Nexus gateway may wrap the response
      const inner = body?.data?.content
        ? typeof body.data.content === "string"
          ? JSON.parse(body.data.content)
          : body.data.content
        : body;
      if (inner?.detail) message = inner.detail;
    } catch {
      /* non-JSON body */
    }
    throw { status: response.status, message };
  }

  const body = await response.json();
  // Unwrap Nexus envelope if present
  if (body?.data?.content) {
    const content = body.data.content;
    return typeof content === "string" ? JSON.parse(content) : content;
  }
  return body as InviteValidation;
}

/* ── API Methods ─────────────────────────────────────────── */

export const employeesApi = {
  /** Admin: list all employees for the current company. */
  list(): Promise<{ employees: Employee[]; count: number }> {
    return apiClient.get<{ employees: Employee[]; count: number }>(
      "/employees",
    );
  },

  /** Employee: get own employee record. */
  me(): Promise<EmployeeRecord> {
    return apiClient.get<EmployeeRecord>("/employees/me");
  },

  /** Admin: invite a new employee by email. */
  invite(data: InviteEmployeeData): Promise<InviteResponse> {
    return apiClient.post<InviteResponse>("/employees/invite", data);
  },

  /** Admin: list all invitations for the current company. */
  listInvitations(): Promise<Invitation[]> {
    return apiClient.get<Invitation[]>("/employees/invitations");
  },

  /** Admin: revoke a pending invitation. */
  revokeInvitation(id: number): Promise<void> {
    return apiClient.delete<void>(`/employees/invite/${id}`);
  },

  /** Admin: resend an invitation (generates fresh link). */
  resendInvitation(id: number): Promise<{ invite_url: string }> {
    return apiClient.post<{ invite_url: string }>(
      `/employees/invite/${id}/resend`,
    );
  },

  /** Get leave balances for the current employee. */
  leaveBalances(): Promise<{ balances: LeaveBalance[] }> {
    return apiClient.get<{ balances: LeaveBalance[] }>("/employees/me/leave");
  },

  /** Get company policies (company-specific or platform defaults). */
  policies(): Promise<{ policies: CompanyPolicy[] }> {
    return apiClient.get<{ policies: CompanyPolicy[] }>("/employees/policies");
  },

  /* ── Extended Employee Endpoints (M16) ──────────────────── */

  /** Admin: get full employee detail by ID. */
  getEmployee(id: number): Promise<EmployeeDetail> {
    return apiClient.get<EmployeeDetail>(`/employees/${id}`);
  },

  /** Admin: partial update employee fields. */
  updateEmployee(
    id: number,
    data: Partial<EmployeeDetail>,
  ): Promise<EmployeeDetail> {
    return apiClient.patch<EmployeeDetail>(`/employees/${id}`, data);
  },

  /** List salary components for an employee. */
  listSalaryComponents(
    employeeId: number,
  ): Promise<{ components: SalaryComponent[] }> {
    return apiClient.get<{ components: SalaryComponent[] }>(
      `/employees/${employeeId}/salary-components`,
    );
  },

  /** Add a new salary component. */
  createSalaryComponent(
    employeeId: number,
    data: Omit<SalaryComponent, "id">,
  ): Promise<SalaryComponent> {
    return apiClient.post<SalaryComponent>(
      `/employees/${employeeId}/salary-components`,
      data,
    );
  },

  /** Update an existing salary component. */
  updateSalaryComponent(
    employeeId: number,
    componentId: number,
    data: Partial<SalaryComponent>,
  ): Promise<SalaryComponent> {
    return apiClient.patch<SalaryComponent>(
      `/employees/${employeeId}/salary-components/${componentId}`,
      data,
    );
  },

  /** List emergency contacts for an employee. */
  listEmergencyContacts(
    employeeId: number,
  ): Promise<{ contacts: EmergencyContact[] }> {
    return apiClient.get<{ contacts: EmergencyContact[] }>(
      `/employees/${employeeId}/emergency-contacts`,
    );
  },

  /** Add a new emergency contact. */
  createEmergencyContact(
    employeeId: number,
    data: Omit<EmergencyContact, "id">,
  ): Promise<EmergencyContact> {
    return apiClient.post<EmergencyContact>(
      `/employees/${employeeId}/emergency-contacts`,
      data,
    );
  },

  /** List employment history / events for an employee. */
  listEmploymentHistory(
    employeeId: number,
  ): Promise<{ events: EmploymentEvent[] }> {
    return apiClient.get<{ events: EmploymentEvent[] }>(
      `/employees/${employeeId}/history`,
    );
  },

  /** List documents for an employee. */
  listDocuments(
    employeeId: number,
  ): Promise<{ documents: EmployeeDocument[] }> {
    return apiClient.get<{ documents: EmployeeDocument[] }>(
      `/employees/${employeeId}/documents`,
    );
  },

  /** Upload a document for an employee. */
  uploadDocument(
    employeeId: number,
    formData: FormData,
  ): Promise<EmployeeDocument> {
    return apiClient.postFormData<EmployeeDocument>(
      `/employees/${employeeId}/documents`,
      formData,
    );
  },

  /** Delete a document. */
  deleteDocument(
    employeeId: number,
    docId: number,
  ): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/employees/${employeeId}/documents/${docId}`,
    );
  },

  /** Get org chart data. */
  getOrgChart(): Promise<unknown> {
    return apiClient.get("/employees/org-chart/data");
  },

  /** Preview CSV import — returns parsed records for review. */
  importPreview(formData: FormData): Promise<{ records: unknown[] }> {
    return apiClient.postFormData<{ records: unknown[] }>(
      "/employees/import/preview",
      formData,
    );
  },

  /** Confirm CSV import after preview. */
  importConfirm(records: unknown[]): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>("/employees/import/confirm", {
      records,
    });
  },

  /** List employees due for probation review. */
  getProbationDue(): Promise<{ employees: Employee[] }> {
    return apiClient.get<{ employees: Employee[] }>("/employees/probation/due");
  },

  /** Confirm an employee (end probation). */
  confirmEmployee(id: number, remarks?: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/employees/${id}/confirm`, {
      remarks,
    });
  },

  /** Extend an employee's probation period. */
  extendProbation(
    id: number,
    newEndDate: string,
    remarks?: string,
  ): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/employees/${id}/extend-probation`,
      { new_end_date: newEndDate, remarks },
    );
  },

  /** Process employee exit (resignation/termination/retrenchment/contract end). */
  processExit(
    id: number,
    data: {
      exit_type: string;
      last_working_day: string;
      reason?: string;
      notice_served?: boolean;
    },
  ): Promise<ExitSettlement> {
    return apiClient.post<ExitSettlement>(`/employees/${id}/exit`, data);
  },

  /* ── Family Members ──────────────────────────────────────── */

  /** List family members for an employee. */
  listFamilyMembers(
    employeeId: number,
  ): Promise<{ family_members: FamilyMember[]; count: number }> {
    return apiClient.get<{ family_members: FamilyMember[]; count: number }>(
      `/employees/${employeeId}/family-members`,
    );
  },

  /** Add a new family member. */
  createFamilyMember(
    employeeId: number,
    data: Partial<FamilyMember>,
  ): Promise<FamilyMember> {
    return apiClient.post<FamilyMember>(
      `/employees/${employeeId}/family-members`,
      data,
    );
  },

  /** Update an existing family member. */
  updateFamilyMember(
    employeeId: number,
    memberId: number,
    data: Partial<FamilyMember>,
  ): Promise<FamilyMember> {
    return apiClient.patch<FamilyMember>(
      `/employees/${employeeId}/family-members/${memberId}`,
      data,
    );
  },

  /** Delete a family member. */
  deleteFamilyMember(employeeId: number, memberId: number): Promise<void> {
    return apiClient.delete<void>(
      `/employees/${employeeId}/family-members/${memberId}`,
    );
  },

  /* ── Employee Notes ──────────────────────────────────────── */

  /** List notes for an employee. */
  listNotes(
    employeeId: number,
  ): Promise<{ notes: EmployeeNote[]; count: number }> {
    return apiClient.get<{ notes: EmployeeNote[]; count: number }>(
      `/employees/${employeeId}/notes`,
    );
  },

  /** Add a new note. */
  createNote(
    employeeId: number,
    data: Partial<EmployeeNote>,
  ): Promise<EmployeeNote> {
    return apiClient.post<EmployeeNote>(`/employees/${employeeId}/notes`, data);
  },

  /** Update an existing note. */
  updateNote(
    employeeId: number,
    noteId: number,
    data: Partial<EmployeeNote>,
  ): Promise<EmployeeNote> {
    return apiClient.patch<EmployeeNote>(
      `/employees/${employeeId}/notes/${noteId}`,
      data,
    );
  },

  /** Delete a note. */
  deleteNote(employeeId: number, noteId: number): Promise<void> {
    return apiClient.delete<void>(`/employees/${employeeId}/notes/${noteId}`);
  },

  /* ── Employee Skills & Certifications ────────────────────── */

  /** List skills and certifications for an employee. */
  listSkills(
    employeeId: number,
  ): Promise<{ skills: EmployeeSkill[]; count: number }> {
    return apiClient.get<{ skills: EmployeeSkill[]; count: number }>(
      `/employees/${employeeId}/skills`,
    );
  },

  /** Add a new skill or certification. */
  createSkill(
    employeeId: number,
    data: Partial<EmployeeSkill>,
  ): Promise<EmployeeSkill> {
    return apiClient.post<EmployeeSkill>(
      `/employees/${employeeId}/skills`,
      data,
    );
  },

  /** Update an existing skill or certification. */
  updateSkill(
    employeeId: number,
    skillId: number,
    data: Partial<EmployeeSkill>,
  ): Promise<EmployeeSkill> {
    return apiClient.patch<EmployeeSkill>(
      `/employees/${employeeId}/skills/${skillId}`,
      data,
    );
  },

  /** Delete a skill or certification. */
  deleteSkill(employeeId: number, skillId: number): Promise<void> {
    return apiClient.delete<void>(`/employees/${employeeId}/skills/${skillId}`);
  },

  /* ── Custom Field Definitions ────────────────────────────── */

  /** List custom field definitions for the current company. */
  listCustomFields(): Promise<{
    custom_fields: CustomFieldDefinition[];
    count: number;
  }> {
    return apiClient.get<{
      custom_fields: CustomFieldDefinition[];
      count: number;
    }>("/employees/custom-fields");
  },

  /** Create a new custom field definition. */
  createCustomField(
    data: Partial<CustomFieldDefinition>,
  ): Promise<CustomFieldDefinition> {
    return apiClient.post<CustomFieldDefinition>(
      "/employees/custom-fields",
      data,
    );
  },

  /** Update a custom field definition. */
  updateCustomField(
    fieldId: number,
    data: Partial<CustomFieldDefinition>,
  ): Promise<CustomFieldDefinition> {
    return apiClient.patch<CustomFieldDefinition>(
      `/employees/custom-fields/${fieldId}`,
      data,
    );
  },

  /** Delete a custom field definition. */
  deleteCustomField(fieldId: number): Promise<void> {
    return apiClient.delete<void>(`/employees/custom-fields/${fieldId}`);
  },

  /* ── Custom Field Values ─────────────────────────────────── */

  /** List custom field values for an employee. */
  listCustomFieldValues(
    employeeId: number,
  ): Promise<{ values: CustomFieldValue[]; count: number }> {
    return apiClient.get<{ values: CustomFieldValue[]; count: number }>(
      `/employees/${employeeId}/custom-field-values`,
    );
  },

  /** Set a custom field value for an employee. */
  setCustomFieldValue(
    employeeId: number,
    data: Partial<CustomFieldValue>,
  ): Promise<CustomFieldValue> {
    return apiClient.post<CustomFieldValue>(
      `/employees/${employeeId}/custom-field-values`,
      data,
    );
  },

  /** Update an existing custom field value. */
  updateCustomFieldValue(
    employeeId: number,
    valueId: number,
    data: Partial<CustomFieldValue>,
  ): Promise<CustomFieldValue> {
    return apiClient.patch<CustomFieldValue>(
      `/employees/${employeeId}/custom-field-values/${valueId}`,
      data,
    );
  },

  /* ── Leave Balances (Admin) ──────────────────────────────── */

  /** Admin: get leave balances for a specific employee. */
  getEmployeeLeaveBalances(
    employeeId: number,
  ): Promise<{ balances: AdminLeaveBalance[] }> {
    return apiClient.get<{ balances: AdminLeaveBalance[] }>(
      `/employees/${employeeId}/leave-balances`,
    );
  },
};
