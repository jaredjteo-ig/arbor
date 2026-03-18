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
  status: "active" | "invited" | "inactive";
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
  notice_period_days: number;
  is_active: boolean;
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
}

export interface LeaveBalance {
  name: string;
  entitlement: number;
  used: number;
  pending: number;
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
};
