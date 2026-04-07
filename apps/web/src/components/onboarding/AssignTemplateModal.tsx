"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AppButton,
  AppInput,
  DatePicker,
  toast,
} from "@/components/design-system";
import { X, ClipboardList } from "lucide-react";
import {
  onboardingApi,
  type OnboardingTemplate,
} from "@/services/api/onboarding";
import { employeesApi, type Employee } from "@/services/api/employees";

/* ═══════════════════════════════════════════════════════════
   AssignTemplateModal
   Allows HR to assign an onboarding template to an employee.
   ═══════════════════════════════════════════════════════════ */

export function AssignTemplateModal({
  isOpen,
  employeeId,
  employeeName,
  onClose,
  onAssigned,
}: {
  isOpen: boolean;
  employeeId: number;
  employeeName: string;
  onClose: () => void;
  onAssigned: () => void;
}) {
  const [templates, setTemplates] = useState<OnboardingTemplate[]>([]);
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("");
  const [dueDate, setDueDate] = useState("");
  const [buddyEmployeeId, setBuddyEmployeeId] = useState<string>("");
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchTemplates = useCallback(async () => {
    setIsLoadingTemplates(true);
    try {
      const data = await onboardingApi.listTemplates();
      const active = (data.templates ?? []).filter((t) => t.is_active);
      setTemplates(active);
      // Pre-select the default template if one exists
      const defaultTpl = active.find((t) => t.is_default);
      if (defaultTpl) {
        setSelectedTemplateId(String(defaultTpl.id));
      } else if (active.length === 1) {
        setSelectedTemplateId(String(active[0].id));
      }
    } catch {
      toast.error("Failed to load onboarding templates.");
    } finally {
      setIsLoadingTemplates(false);
    }
  }, []);

  const fetchEmployees = useCallback(async () => {
    try {
      const data = await employeesApi.list();
      const active = (data.employees ?? []).filter(
        (e) => e.status === "active" && e.id !== employeeId,
      );
      setEmployees(active);
    } catch {
      // Non-critical — buddy is optional
    }
  }, [employeeId]);

  useEffect(() => {
    if (isOpen) {
      fetchTemplates();
      fetchEmployees();
      setDueDate("");
      setBuddyEmployeeId("");
    }
  }, [isOpen, fetchTemplates, fetchEmployees]);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedTemplateId) {
      toast.error("Please select a template.");
      return;
    }
    setIsSubmitting(true);
    try {
      await onboardingApi.assignTemplate({
        employee_id: employeeId,
        template_id: parseInt(selectedTemplateId, 10),
        due_date: dueDate || undefined,
        buddy_employee_id: buddyEmployeeId
          ? parseInt(buddyEmployeeId, 10)
          : undefined,
      });
      toast.success(`Onboarding assigned to ${employeeName}.`);
      onAssigned();
      onClose();
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to assign template";
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const templateOptions = templates.map((t) => ({
    value: String(t.id),
    label: t.is_default ? `${t.name} (default)` : t.name,
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-md mx-4 rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <ClipboardList className="h-5 w-5 text-[var(--color-primary)]" />
            <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
              Assign Onboarding
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-5 w-5 text-[var(--color-gray-500)]" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Employee info */}
          <div className="rounded-[8px] bg-[var(--color-gray-50)] border border-[var(--color-gray-200)] px-3 py-2">
            <p className="text-xs text-[var(--color-gray-500)]">Employee</p>
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              {employeeName}
            </p>
          </div>

          {/* Template selector */}
          {isLoadingTemplates ? (
            <div className="flex items-center gap-2 py-3">
              <span className="inline-block h-4 w-4 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-[var(--color-gray-500)]">
                Loading templates...
              </span>
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-[8px] bg-amber-50 border border-amber-200 px-3 py-3">
              <p className="text-sm text-amber-800">
                No active onboarding templates found. Create a template first
                from the Onboarding tab.
              </p>
            </div>
          ) : (
            <AppInput
              variant="select"
              label="Onboarding template"
              value={selectedTemplateId}
              onChange={(e) =>
                setSelectedTemplateId((e.target as HTMLSelectElement).value)
              }
              options={templateOptions}
              placeholder="Select a template..."
            />
          )}

          {/* Due date */}
          <DatePicker
            label="Due date (optional)"
            value={dueDate}
            onChange={setDueDate}
            min={new Date().toISOString().split("T")[0]}
            placeholder="Select due date"
            helperText="When the employee should complete onboarding by."
          />

          {/* Buddy picker */}
          {employees.length > 0 && (
            <AppInput
              variant="select"
              label="Assign buddy (optional)"
              value={buddyEmployeeId}
              onChange={(e) =>
                setBuddyEmployeeId((e.target as HTMLSelectElement).value)
              }
              options={employees.map((emp) => ({
                value: String(emp.id),
                label: emp.department
                  ? `${emp.name} - ${emp.department}`
                  : emp.name,
              }))}
              placeholder="Select a buddy..."
              helperText="A colleague who will help the new hire settle in."
            />
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <AppButton
              type="button"
              variant="outlined"
              size="sm"
              onClick={onClose}
              className="flex-1"
            >
              Cancel
            </AppButton>
            <AppButton
              type="submit"
              variant="primary"
              size="sm"
              loading={isSubmitting}
              disabled={templates.length === 0 || !selectedTemplateId}
              className="flex-1"
            >
              Assign Onboarding
            </AppButton>
          </div>
        </form>
      </div>
    </div>
  );
}
