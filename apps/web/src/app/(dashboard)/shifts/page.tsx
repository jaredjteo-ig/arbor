"use client";

import { useState, useCallback, useEffect } from "react";
import { AppCard } from "@/components/design-system/AppCard";
import { AppButton } from "@/components/design-system/AppButton";
import { AppInput } from "@/components/design-system/AppInput";
import { useAuth } from "@/contexts/AuthContext";
import {
  shiftsApi,
  type ShiftTemplate,
  type ShiftAssignment,
  type EmployeeHours,
} from "@/services/api/shifts";

/* ── Helpers ─────────────────────────────────────────────── */

function getMonday(d: Date): string {
  const date = new Date(d);
  const day = date.getDay();
  const diff = date.getDate() - day + (day === 0 ? -6 : 1);
  date.setDate(diff);
  return date.toISOString().split("T")[0];
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().split("T")[0];
}

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatCurrency(amount: number): string {
  return `$${amount.toLocaleString("en-SG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/* ── Component ───────────────────────────────────────────── */

export default function ShiftsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "hr_manager";

  const [weekStart, setWeekStart] = useState(getMonday(new Date()));
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [assignments, setAssignments] = useState<ShiftAssignment[]>([]);
  const [hours, setHours] = useState<EmployeeHours[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Template form
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    start_time: "09:00",
    end_time: "17:00",
    break_minutes: 60,
    colour: "#4A90C4",
  });

  // Assignment form
  const [showAssignForm, setShowAssignForm] = useState(false);
  const [newAssignment, setNewAssignment] = useState({
    employee_id: "",
    shift_template_id: "",
    date: "",
  });

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [templatesRes, scheduleRes, hoursRes] = await Promise.all([
        shiftsApi.listTemplates(),
        shiftsApi.getSchedule(weekStart),
        isAdmin
          ? shiftsApi.getHours(weekStart)
          : Promise.resolve({ employees: [] }),
      ]);
      setTemplates(templatesRes.templates || []);
      setAssignments(scheduleRes.assignments || []);
      setHours(hoursRes.employees || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load shift data.",
      );
    } finally {
      setLoading(false);
    }
  }, [weekStart, isAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateTemplate = useCallback(async () => {
    try {
      await shiftsApi.createTemplate({
        name: newTemplate.name,
        start_time: newTemplate.start_time,
        end_time: newTemplate.end_time,
        break_minutes: newTemplate.break_minutes,
        colour: newTemplate.colour,
      });
      setShowTemplateForm(false);
      setNewTemplate({
        name: "",
        start_time: "09:00",
        end_time: "17:00",
        break_minutes: 60,
        colour: "#4A90C4",
      });
      fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create template.",
      );
    }
  }, [newTemplate, fetchData]);

  const handleAssign = useCallback(async () => {
    try {
      await shiftsApi.createAssignment({
        employee_id: parseInt(newAssignment.employee_id),
        shift_template_id: parseInt(newAssignment.shift_template_id),
        date: newAssignment.date,
      });
      setShowAssignForm(false);
      setNewAssignment({ employee_id: "", shift_template_id: "", date: "" });
      fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign shift.");
    }
  }, [newAssignment, fetchData]);

  const handlePublish = useCallback(async () => {
    try {
      await shiftsApi.publishSchedule(weekStart);
      fetchData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to publish schedule.",
      );
    }
  }, [weekStart, fetchData]);

  const handleDeleteAssignment = useCallback(
    async (id: number) => {
      try {
        await shiftsApi.deleteAssignment(id);
        fetchData();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete.");
      }
    },
    [fetchData],
  );

  const prevWeek = () => setWeekStart(addDays(weekStart, -7));
  const nextWeek = () => setWeekStart(addDays(weekStart, 7));

  // Group assignments by date for the grid
  const assignmentsByDate: Record<string, ShiftAssignment[]> = {};
  for (let i = 0; i < 7; i++) {
    const d = addDays(weekStart, i);
    assignmentsByDate[d] = assignments.filter((a) => a.date === d);
  }

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <div className="h-8 w-48 rounded bg-gray-200 animate-pulse" />
        <div className="grid grid-cols-7 gap-2">
          {Array.from({ length: 7 }).map((_, i) => (
            <div
              key={i}
              className="h-40 rounded-lg bg-gray-100 animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1
          className="text-2xl font-semibold"
          style={{ color: "var(--color-foreground)" }}
        >
          Shift Scheduling
        </h1>
        <div className="flex items-center gap-2">
          {isAdmin && (
            <>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => setShowTemplateForm(true)}
              >
                Manage Templates
              </AppButton>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => setShowAssignForm(true)}
              >
                Assign Shift
              </AppButton>
              <AppButton variant="primary" size="sm" onClick={handlePublish}>
                Publish Week
              </AppButton>
            </>
          )}
        </div>
      </div>

      {error && (
        <div
          className="p-3 rounded-lg text-sm"
          style={{
            background: "var(--color-risk-red-bg)",
            color: "var(--color-risk-red)",
          }}
        >
          {error}
        </div>
      )}

      {/* Week Navigation */}
      <div className="flex items-center gap-4">
        <AppButton variant="text" size="sm" onClick={prevWeek}>
          ← Previous
        </AppButton>
        <span
          className="font-medium"
          style={{ color: "var(--color-foreground)" }}
        >
          Week of{" "}
          {new Date(weekStart).toLocaleDateString("en-SG", {
            day: "numeric",
            month: "short",
            year: "numeric",
          })}
        </span>
        <AppButton variant="text" size="sm" onClick={nextWeek}>
          Next →
        </AppButton>
      </div>

      {/* Weekly Grid */}
      <div className="grid grid-cols-7 gap-2">
        {DAY_LABELS.map((label, i) => {
          const dateStr = addDays(weekStart, i);
          const dayAssignments = assignmentsByDate[dateStr] || [];
          const isToday = dateStr === new Date().toISOString().split("T")[0];

          return (
            <div key={dateStr}>
              <div
                className="text-center text-xs font-medium py-1 rounded-t"
                style={{
                  background: isToday
                    ? "var(--color-primary)"
                    : "var(--color-surface-sidebar)",
                  color: isToday ? "white" : "var(--color-muted)",
                }}
              >
                {label} {new Date(dateStr).getDate()}
              </div>
              <div
                className="min-h-[120px] rounded-b-lg p-1 space-y-1"
                style={{
                  background: "var(--color-surface-card)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {dayAssignments.length === 0 && (
                  <div
                    className="text-xs text-center py-4"
                    style={{ color: "var(--color-muted)" }}
                  >
                    No shifts
                  </div>
                )}
                {dayAssignments.map((a) => {
                  const tpl = templates.find(
                    (t) => t.id === a.shift_template_id,
                  );
                  return (
                    <div
                      key={a.id}
                      className="text-xs p-1.5 rounded relative group"
                      style={{
                        background: tpl?.colour
                          ? `${tpl.colour}20`
                          : "var(--color-primary-bg)",
                        borderLeft: `3px solid ${tpl?.colour || "var(--color-primary)"}`,
                      }}
                    >
                      <div className="font-medium truncate">
                        {a.employee_name || `Emp #${a.employee_id}`}
                      </div>
                      <div style={{ color: "var(--color-muted)" }}>
                        {tpl?.name || "Shift"} {tpl?.start_time}–{tpl?.end_time}
                      </div>
                      {isAdmin && (
                        <button
                          onClick={() => handleDeleteAssignment(a.id)}
                          className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 text-xs rounded px-1"
                          style={{
                            background: "var(--color-risk-red-bg)",
                            color: "var(--color-risk-red)",
                          }}
                        >
                          ×
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Hours Tracking (Admin) */}
      {isAdmin && hours.length > 0 && (
        <AppCard>
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: "var(--color-foreground)" }}
          >
            Weekly Hours
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                <th
                  className="text-left py-2 font-medium"
                  style={{ color: "var(--color-muted)" }}
                >
                  Employee
                </th>
                <th
                  className="text-right py-2 font-medium"
                  style={{ color: "var(--color-muted)" }}
                >
                  Hours
                </th>
                <th
                  className="text-right py-2 font-medium"
                  style={{ color: "var(--color-muted)" }}
                >
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {hours.map((h) => (
                <tr
                  key={h.employee_id}
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <td className="py-2">{h.name}</td>
                  <td className="py-2 text-right">{h.total_hours}h</td>
                  <td className="py-2 text-right">
                    {h.exceeds_limit ? (
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          background: "var(--color-risk-red-bg)",
                          color: "var(--color-risk-red)",
                        }}
                      >
                        Exceeds 44h limit
                      </span>
                    ) : (
                      <span
                        className="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                        style={{
                          background: "var(--color-risk-green-bg)",
                          color: "var(--color-risk-green)",
                        }}
                      >
                        OK
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </AppCard>
      )}

      {/* Shift Templates */}
      {isAdmin && (
        <AppCard>
          <h2
            className="text-lg font-semibold mb-3"
            style={{ color: "var(--color-foreground)" }}
          >
            Shift Templates
          </h2>
          <div className="flex flex-wrap gap-3">
            {templates.map((t) => (
              <div
                key={t.id}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm"
                style={{
                  background: `${t.colour}15`,
                  border: `1px solid ${t.colour}40`,
                }}
              >
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ background: t.colour }}
                />
                <span className="font-medium">{t.name}</span>
                <span style={{ color: "var(--color-muted)" }}>
                  {t.start_time}–{t.end_time} ({t.work_hours}h)
                </span>
              </div>
            ))}
            {templates.length === 0 && (
              <p className="text-sm" style={{ color: "var(--color-muted)" }}>
                No templates yet. Create one to start scheduling.
              </p>
            )}
          </div>
        </AppCard>
      )}

      {/* Template Form Modal */}
      {showTemplateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <AppCard className="w-full max-w-md mx-4">
            <h2 className="text-lg font-semibold mb-4">New Shift Template</h2>
            <div className="space-y-3">
              <AppInput
                label="Template Name"
                value={newTemplate.name}
                onChange={(e) =>
                  setNewTemplate({ ...newTemplate, name: e.target.value })
                }
                placeholder="e.g. Morning, Afternoon, Night"
              />
              <div className="grid grid-cols-2 gap-3">
                <AppInput
                  label="Start Time"
                  value={newTemplate.start_time}
                  onChange={(e) =>
                    setNewTemplate({
                      ...newTemplate,
                      start_time: e.target.value,
                    })
                  }
                />
                <AppInput
                  label="End Time"
                  value={newTemplate.end_time}
                  onChange={(e) =>
                    setNewTemplate({ ...newTemplate, end_time: e.target.value })
                  }
                />
              </div>
              <AppInput
                label="Break (minutes)"
                variant="number"
                value={String(newTemplate.break_minutes)}
                onChange={(e) =>
                  setNewTemplate({
                    ...newTemplate,
                    break_minutes: parseInt(e.target.value) || 0,
                  })
                }
              />
              <div className="flex items-center gap-2">
                <label
                  className="text-sm font-medium"
                  style={{ color: "var(--color-foreground)" }}
                >
                  Colour
                </label>
                <input
                  type="color"
                  value={newTemplate.colour}
                  onChange={(e) =>
                    setNewTemplate({ ...newTemplate, colour: e.target.value })
                  }
                  className="w-8 h-8 rounded cursor-pointer"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <AppButton
                variant="text"
                onClick={() => setShowTemplateForm(false)}
              >
                Cancel
              </AppButton>
              <AppButton
                variant="primary"
                onClick={handleCreateTemplate}
                disabled={!newTemplate.name}
              >
                Create Template
              </AppButton>
            </div>
          </AppCard>
        </div>
      )}

      {/* Assignment Form Modal */}
      {showAssignForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <AppCard className="w-full max-w-md mx-4">
            <h2 className="text-lg font-semibold mb-4">Assign Shift</h2>
            <div className="space-y-3">
              <AppInput
                label="Employee ID"
                variant="number"
                value={newAssignment.employee_id}
                onChange={(e) =>
                  setNewAssignment({
                    ...newAssignment,
                    employee_id: e.target.value,
                  })
                }
                placeholder="Employee ID"
              />
              <div>
                <label
                  className="text-sm font-medium block mb-1"
                  style={{ color: "var(--color-foreground)" }}
                >
                  Shift Template
                </label>
                <select
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: "var(--color-surface-input)",
                    border: "1px solid var(--color-border)",
                    color: "var(--color-foreground)",
                    minHeight: "44px",
                  }}
                  value={newAssignment.shift_template_id}
                  onChange={(e) =>
                    setNewAssignment({
                      ...newAssignment,
                      shift_template_id: e.target.value,
                    })
                  }
                >
                  <option value="">Select template...</option>
                  {templates.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name} ({t.start_time}–{t.end_time})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label
                  className="text-sm font-medium block mb-1"
                  style={{ color: "var(--color-foreground)" }}
                >
                  Date
                </label>
                <input
                  type="date"
                  className="w-full px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: "var(--color-surface-input)",
                    border: "1px solid var(--color-border)",
                    color: "var(--color-foreground)",
                    minHeight: "44px",
                  }}
                  value={newAssignment.date}
                  onChange={(e) =>
                    setNewAssignment({ ...newAssignment, date: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <AppButton
                variant="text"
                onClick={() => setShowAssignForm(false)}
              >
                Cancel
              </AppButton>
              <AppButton
                variant="primary"
                onClick={handleAssign}
                disabled={
                  !newAssignment.employee_id ||
                  !newAssignment.shift_template_id ||
                  !newAssignment.date
                }
              >
                Assign
              </AppButton>
            </div>
          </AppCard>
        </div>
      )}
    </div>
  );
}
