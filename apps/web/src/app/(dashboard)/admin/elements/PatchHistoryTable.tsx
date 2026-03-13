"use client";

import { useState } from "react";
import { AppCard } from "@/components/design-system";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { QAPatch, QAPatchStatus } from "@/types/api";

/* ── Constants ────────────────────────────────────────────── */

type FilterStatus =
  | "all"
  | QAPatchStatus
  | "testing"
  | "ready_for_approval"
  | "rolled_back";

const STATUS_OPTIONS: { value: FilterStatus; label: string }[] = [
  { value: "all", label: "All statuses" },
  { value: "proposed", label: "Proposed" },
  { value: "testing", label: "Testing" },
  { value: "ready_for_approval", label: "Ready for Approval" },
  { value: "approved", label: "Approved" },
  { value: "deployed", label: "Deployed" },
  { value: "rejected", label: "Rejected" },
  { value: "rolled_back", label: "Rolled Back" },
];

/** Status badge styles */
function statusBadge(status: string): {
  bg: string;
  text: string;
  label: string;
} {
  switch (status) {
    case "deployed":
      return {
        bg: "bg-[var(--color-success-bg)] border-[var(--color-success)]",
        text: "text-[var(--color-success)]",
        label: "Deployed",
      };
    case "rejected":
    case "rolled_back":
      return {
        bg: "bg-[var(--color-risk-red-bg)] border-[var(--color-risk-red)]",
        text: "text-[var(--color-risk-red)]",
        label: status === "rejected" ? "Rejected" : "Rolled Back",
      };
    case "approved":
      return {
        bg: "bg-[var(--color-info-bg)] border-[var(--color-info)]",
        text: "text-[var(--color-info)]",
        label: "Approved",
      };
    case "ready_for_approval":
      return {
        bg: "bg-[var(--color-info-bg)] border-[var(--color-info)]",
        text: "text-[var(--color-info)]",
        label: "Ready",
      };
    case "testing":
      return {
        bg: "bg-[var(--color-risk-amber-bg)] border-[var(--color-risk-amber)]",
        text: "text-[var(--color-risk-amber)]",
        label: "Testing",
      };
    default:
      return {
        bg: "bg-[var(--color-risk-amber-bg)] border-[var(--color-risk-amber)]",
        text: "text-[var(--color-risk-amber)]",
        label: "Proposed",
      };
  }
}

/** Pretty-print agent names */
function agentLabel(agent: string): string {
  return agent.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Pretty-print failure category */
function categoryLabel(category: string): string {
  return category.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── Component ────────────────────────────────────────────── */

interface PatchHistoryTableProps {
  patches: QAPatch[];
}

export function PatchHistoryTable({ patches }: PatchHistoryTableProps) {
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filtered =
    filter === "all" ? patches : patches.filter((p) => p.status === filter);

  const sorted = [...filtered].sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <AppCard
      variant="flat"
      header={
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h4 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Patch History
          </h4>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as FilterStatus)}
            className="text-xs border border-[var(--color-gray-200)] rounded-md px-2 py-1.5 bg-[var(--color-surface-card)] text-[var(--color-gray-700)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      }
    >
      {sorted.length === 0 ? (
        <p className="text-sm text-[var(--color-gray-500)] text-center py-8">
          {filter === "all"
            ? "No instruction patches yet."
            : `No patches with status "${filter}".`}
        </p>
      ) : (
        <div className="overflow-x-auto -mx-5">
          <table className="w-full text-sm" style={{ minWidth: "600px" }}>
            <thead>
              <tr className="border-b border-[var(--color-gray-200)] bg-[var(--color-gray-100)]">
                <th className="w-8 px-2 py-2" />
                <th className="text-left px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Target Agent
                </th>
                <th className="text-left px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Failure Type
                </th>
                <th className="text-left px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Status
                </th>
                <th className="text-left px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Proposed
                </th>
                <th className="text-center px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Evidence
                </th>
                <th className="text-left px-3 py-2 font-medium text-[var(--color-gray-700)]">
                  Approved By
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((patch) => {
                const badge = statusBadge(patch.status);
                const isExpanded = expandedId === patch.id;

                return (
                  <PatchRow
                    key={patch.id}
                    patch={patch}
                    badge={badge}
                    isExpanded={isExpanded}
                    onToggle={() => setExpandedId(isExpanded ? null : patch.id)}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </AppCard>
  );
}

/* ── Patch Row (sub-component kept under 200 lines together) ── */

function PatchRow({
  patch,
  badge,
  isExpanded,
  onToggle,
}: {
  patch: QAPatch;
  badge: { bg: string; text: string; label: string };
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const Chevron = isExpanded ? ChevronDown : ChevronRight;

  return (
    <>
      <tr
        className="border-b border-[var(--color-gray-100)] last:border-0 hover:bg-[var(--color-gray-50)] transition-colors cursor-pointer"
        onClick={onToggle}
      >
        <td className="px-2 py-2.5 text-center">
          <Chevron className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
        </td>
        <td className="px-3 py-2.5 text-[var(--color-gray-900)] font-medium text-xs">
          {agentLabel(patch.affected_agent)}
        </td>
        <td className="px-3 py-2.5 text-[var(--color-gray-700)] text-xs">
          {categoryLabel(patch.failure_category)}
        </td>
        <td className="px-3 py-2.5">
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${badge.bg} ${badge.text}`}
          >
            {badge.label}
          </span>
        </td>
        <td className="px-3 py-2.5 text-xs text-[var(--color-gray-500)] whitespace-nowrap">
          {new Date(patch.created_at).toLocaleDateString()}
        </td>
        <td className="px-3 py-2.5 text-xs text-[var(--color-gray-700)] text-center">
          {patch.evidence_count}
        </td>
        <td className="px-3 py-2.5 text-xs text-[var(--color-gray-500)]">
          {patch.approved_by ?? "--"}
        </td>
      </tr>

      {/* Expanded detail */}
      {isExpanded && (
        <tr>
          <td colSpan={7} className="px-5 py-3 bg-[var(--color-gray-50)]">
            <div className="space-y-3 text-xs">
              {/* Rationale */}
              <div>
                <p className="font-semibold text-[var(--color-gray-900)] mb-0.5">
                  Rationale
                </p>
                <p className="text-[var(--color-gray-700)]">
                  {patch.rationale}
                </p>
              </div>

              {/* Current vs proposed instruction */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <p className="font-semibold text-[var(--color-gray-900)] mb-0.5">
                    Current Instruction
                  </p>
                  <p className="text-[var(--color-gray-600)] whitespace-pre-wrap bg-[var(--color-surface-card)] rounded p-2 border border-[var(--color-gray-200)]">
                    {patch.current_instruction}
                  </p>
                </div>
                <div>
                  <p className="font-semibold text-[var(--color-gray-900)] mb-0.5">
                    Proposed Instruction
                  </p>
                  <p className="text-[var(--color-gray-600)] whitespace-pre-wrap bg-[var(--color-surface-card)] rounded p-2 border border-[var(--color-gray-200)]">
                    {patch.proposed_instruction}
                  </p>
                </div>
              </div>

              {/* Approved info */}
              {patch.approved_at && (
                <p className="text-[var(--color-gray-500)]">
                  Approved on {new Date(patch.approved_at).toLocaleDateString()}{" "}
                  by {patch.approved_by ?? "Unknown"}
                </p>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
