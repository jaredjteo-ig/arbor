/* ── Onboarding API Service ───────────────────────────────── */

import { apiClient, getValidAccessToken } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface OnboardingTemplate {
  id: number;
  company_id: number;
  name: string;
  description: string;
  is_default: boolean;
  version: number;
  is_active: boolean;
  created_at: string;
}

export interface OnboardingModule {
  id: number;
  template_id: number;
  name: string;
  description: string;
  phase: string;
  order: number;
  estimated_duration_minutes: number;
  is_mandatory: boolean;
  is_role_specific: boolean;
  role_filter: string;
}

export interface OnboardingStep {
  id: number;
  module_id: number;
  title: string;
  description: string;
  order: number;
  step_type: string;
  body_content: string;
  checklist_items: string;
  media_url: string;
  requires_completion: boolean;
  policy_id: number | null;
}

export interface OnboardingAssignment {
  id: number;
  employee_id: number;
  template_id: number;
  template_version: number;
  company_id: number;
  status: string;
  completion_percentage: number;
  assigned_at: string;
  due_date: string | null;
  completed_at: string | null;
  employee_name?: string;
  template_name?: string;
  department?: string;
  buddy_employee_id?: number | null;
  buddy_name?: string;
  buddy_email?: string;
  buddy_department?: string;
  buddy_designation?: string;
}

export interface OnboardingStepProgress {
  id: number;
  step_id: number;
  status: string;
  completed_at: string | null;
  document_url: string;
  notes: string;
}

/** A step-progress record with inlined step metadata, as returned by the backend. */
export interface StepProgressWithStep extends OnboardingStepProgress {
  step_title: string;
  step_type: string;
  step_description: string;
  body_content: string;
  checklist_items: string;
  media_url: string;
  module_id: number;
  policy_id?: number | null;
}

/** Module summary returned inside the assignment from my-progress / getAssignment.
 *
 * The my-progress endpoint returns: module_id, module_name, phase, is_mandatory, steps, step_count, completed_count.
 * The getAssignment endpoint spreads the full OnboardingModule record and adds steps_progress.
 * This interface covers both shapes.
 */
export interface AssignmentModuleSummary {
  /** From my-progress endpoint */
  module_id?: number;
  module_name?: string;
  /** From getAssignment endpoint (full module record fields) */
  id?: number;
  name?: string;
  description?: string;
  template_id?: number;
  order?: number;
  estimated_duration_minutes?: number;
  is_role_specific?: boolean;
  role_filter?: string;
  /** Common fields */
  phase: string;
  is_mandatory: boolean;
  /** Steps from my-progress (key: "steps") */
  steps: StepProgressWithStep[];
  /** Steps from getAssignment (key: "steps_progress") */
  steps_progress?: StepProgressWithStep[];
  step_count?: number;
  completed_count?: number;
}

/** The assignment record as enriched by the backend, with modules nested inside. */
export interface EnrichedAssignment extends OnboardingAssignment {
  modules: AssignmentModuleSummary[];
  completed_steps?: number;
  total_steps?: number;
}

/**
 * Response shape from GET /onboarding/my-progress and GET /onboarding/assignments/{id}.
 * The backend nests modules inside the assignment object.
 * `assignment` is null when the user has no active onboarding.
 */
export interface MyOnboardingProgress {
  assignment: EnrichedAssignment | null;
  message?: string;
}

export interface ImportResult {
  template_id: number;
  modules_created: number;
  steps_created: number;
  preboarding_tasks_created: number;
  policy_steps_created: number;
  warnings: string[];
  errors: string[];
}

export interface PreboardingTask {
  id: number;
  company_id: number;
  template_id: number;
  employee_id: number;
  task_name: string;
  owner_role: string; // hr, manager, it, office_manager
  trigger: string;
  deadline_date: string | null;
  status: string; // pending, done
  completed_at: string | null;
  completed_by: number | null;
  notes: string;
  /** Computed by backend overdue detection */
  is_overdue?: boolean;
}

export interface PreboardingListResponse {
  tasks: PreboardingTask[];
  total: number;
  pending: number;
  done: number;
}

/* ── API Methods ─────────────────────────────────────────── */

export const onboardingApi = {
  /* ── Template CRUD ──────────────────────────────────────── */

  /** List all onboarding templates for the current company. */
  listTemplates(): Promise<{ templates: OnboardingTemplate[]; count: number }> {
    return apiClient.get<{ templates: OnboardingTemplate[]; count: number }>(
      "/onboarding/templates",
    );
  },

  /** Get a single template by ID. */
  getTemplate(id: number): Promise<{
    template: OnboardingTemplate;
    modules: Array<{ module: OnboardingModule; steps: OnboardingStep[] }>;
  }> {
    return apiClient.get<{
      template: OnboardingTemplate;
      modules: Array<{ module: OnboardingModule; steps: OnboardingStep[] }>;
    }>(`/onboarding/templates/${id}`);
  },

  /** Create a new onboarding template. */
  createTemplate(
    data: Partial<OnboardingTemplate>,
  ): Promise<OnboardingTemplate> {
    return apiClient.post<OnboardingTemplate>("/onboarding/templates", data);
  },

  /** Update an existing template. */
  updateTemplate(
    id: number,
    data: Partial<OnboardingTemplate>,
  ): Promise<OnboardingTemplate> {
    return apiClient.patch<OnboardingTemplate>(
      `/onboarding/templates/${id}`,
      data,
    );
  },

  /** Delete a template. */
  deleteTemplate(id: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/onboarding/templates/${id}`);
  },

  /** Duplicate a template. */
  duplicateTemplate(id: number): Promise<OnboardingTemplate> {
    return apiClient.post<OnboardingTemplate>(
      `/onboarding/templates/${id}/duplicate`,
    );
  },

  /* ── Modules ────────────────────────────────────────────── */

  /** Add a module to a template. */
  addModule(
    templateId: number,
    data: Partial<OnboardingModule>,
  ): Promise<OnboardingModule> {
    return apiClient.post<OnboardingModule>(
      `/onboarding/templates/${templateId}/modules`,
      data,
    );
  },

  /** Update a module. */
  updateModule(
    templateId: number,
    moduleId: number,
    data: Partial<OnboardingModule>,
  ): Promise<OnboardingModule> {
    return apiClient.patch<OnboardingModule>(
      `/onboarding/templates/${templateId}/modules/${moduleId}`,
      data,
    );
  },

  /** Delete a module. */
  deleteModule(
    templateId: number,
    moduleId: number,
  ): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/onboarding/templates/${templateId}/modules/${moduleId}`,
    );
  },

  /** Reorder modules within a template. */
  reorderModules(
    templateId: number,
    moduleIds: number[],
  ): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/onboarding/templates/${templateId}/modules/reorder`,
      { module_ids: moduleIds },
    );
  },

  /* ── Steps ──────────────────────────────────────────────── */

  /** Add a step to a module. */
  addStep(
    templateId: number,
    moduleId: number,
    data: Partial<OnboardingStep>,
  ): Promise<OnboardingStep> {
    return apiClient.post<OnboardingStep>(
      `/onboarding/templates/${templateId}/modules/${moduleId}/steps`,
      data,
    );
  },

  /** Update a step. */
  updateStep(
    templateId: number,
    moduleId: number,
    stepId: number,
    data: Partial<OnboardingStep>,
  ): Promise<OnboardingStep> {
    return apiClient.patch<OnboardingStep>(
      `/onboarding/templates/${templateId}/modules/${moduleId}/steps/${stepId}`,
      data,
    );
  },

  /** Delete a step. */
  deleteStep(
    templateId: number,
    moduleId: number,
    stepId: number,
  ): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/onboarding/templates/${templateId}/modules/${moduleId}/steps/${stepId}`,
    );
  },

  /** Reorder steps within a module. */
  reorderSteps(
    templateId: number,
    moduleId: number,
    stepIds: number[],
  ): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/onboarding/templates/${templateId}/modules/${moduleId}/steps/reorder`,
      { step_ids: stepIds },
    );
  },

  /* ── Assignments ────────────────────────────────────────── */

  /** Assign a template to an employee. */
  assignTemplate(data: {
    employee_id: number;
    template_id: number;
    due_date?: string;
    buddy_employee_id?: number;
  }): Promise<OnboardingAssignment> {
    return apiClient.post<OnboardingAssignment>("/onboarding/assign", data);
  },

  /** Bulk assign a template to multiple employees. */
  assignBulk(data: {
    employee_ids: number[];
    template_id: number;
    due_date?: string;
  }): Promise<{ assignments: OnboardingAssignment[]; count: number }> {
    return apiClient.post<{
      assignments: OnboardingAssignment[];
      count: number;
    }>("/onboarding/assign-bulk", data);
  },

  /** List all assignments (admin view). */
  listAssignments(
    params?: Record<string, string>,
  ): Promise<{ assignments: OnboardingAssignment[]; count: number }> {
    return apiClient.get<{
      assignments: OnboardingAssignment[];
      count: number;
    }>("/onboarding/assignments", params);
  },

  /** Get a single assignment with full progress detail (admin view). */
  getAssignment(id: number): Promise<MyOnboardingProgress> {
    return apiClient.get<MyOnboardingProgress>(`/onboarding/assignments/${id}`);
  },

  /** Cancel an assignment. */
  cancelAssignment(id: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/onboarding/assignments/${id}`,
    );
  },

  /** Get onboarding assignment for a specific employee (admin view). */
  getEmployeeOnboarding(
    employeeId: number,
  ): Promise<{ assignments: OnboardingAssignment[] }> {
    return apiClient.get<{ assignments: OnboardingAssignment[] }>(
      `/onboarding/assignments`,
      { employee_id: String(employeeId) },
    );
  },

  /* ── Self-service (employee-facing) ─────────────────────── */

  /** Get the current employee's onboarding progress. */
  getMyProgress(): Promise<MyOnboardingProgress> {
    return apiClient.get<MyOnboardingProgress>("/onboarding/my-progress");
  },

  /** Mark a step as completed. progressId is the OnboardingStepProgress record ID. */
  completeStep(
    progressId: number,
  ): Promise<{ message: string; progress: OnboardingStepProgress }> {
    return apiClient.post<{
      message: string;
      progress: OnboardingStepProgress;
    }>(`/onboarding/steps/${progressId}/complete`);
  },

  /** Upload a document for a step. progressId is the OnboardingStepProgress record ID. */
  uploadStepDocument(
    progressId: number,
    formData: FormData,
  ): Promise<{
    message: string;
    progress: OnboardingStepProgress;
    document_url: string;
  }> {
    return apiClient.postFormData<{
      message: string;
      progress: OnboardingStepProgress;
      document_url: string;
    }>(`/onboarding/steps/${progressId}/upload`, formData);
  },

  /** Acknowledge a step (e.g. policy acknowledgement). progressId is the OnboardingStepProgress record ID. */
  acknowledgeStep(
    progressId: number,
  ): Promise<{ message: string; progress: OnboardingStepProgress }> {
    return apiClient.post<{
      message: string;
      progress: OnboardingStepProgress;
    }>(`/onboarding/steps/${progressId}/acknowledge`);
  },

  /* ── Import ─────────────────────────────────────────────── */

  /** Import a template from an Excel (.xlsx) file. */
  importTemplate(formData: FormData): Promise<ImportResult> {
    return apiClient.postFormData<ImportResult>(
      "/onboarding/templates/import",
      formData,
    );
  },

  /* ── Pre-boarding ───────────────────────────────────────── */

  /** Get pre-boarding tasks for an employee (with overdue detection). */
  getPreboarding(employeeId: number): Promise<PreboardingListResponse> {
    return apiClient.get<PreboardingListResponse>(
      `/onboarding/preboarding/${employeeId}`,
    );
  },

  /** Mark a pre-boarding task as done. */
  completePreboardingTask(taskId: number): Promise<{ task: PreboardingTask }> {
    return apiClient.patch<{ task: PreboardingTask }>(
      `/onboarding/preboarding/${taskId}`,
      { status: "done" },
    );
  },

  /* ── Export ─────────────────────────────────────────────── */

  /**
   * Export onboarding assignments as CSV.
   * Triggers a browser download of the file.
   */
  async exportAssignments(params?: {
    status?: string;
    department?: string;
    template_id?: number;
  }): Promise<void> {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const token = await getValidAccessToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.department) query.set("department", params.department);
    if (params?.template_id)
      query.set("template_id", String(params.template_id));

    const qs = query.toString();
    const url = `${API_BASE}/onboarding/assignments/export${qs ? `?${qs}` : ""}`;

    const response = await fetch(url, { method: "GET", headers });

    if (!response.ok) {
      throw new Error(`Failed to export assignments (${response.status})`);
    }

    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") ?? "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] ?? "onboarding-assignments.csv";

    const blobUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(blobUrl);
  },
};
