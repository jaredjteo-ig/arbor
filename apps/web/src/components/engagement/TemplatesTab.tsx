"use client";

import { useState } from "react";
import { Copy, FileText, Loader2 } from "lucide-react";
import {
  engagementApi,
  parseSections,
  type EngagementTemplate,
  type Methodology,
} from "@/services/api/engagement";

interface TemplatesTabProps {
  templates: EngagementTemplate[];
  onChange: () => void;
}

const METHODOLOGY_BADGE: Record<Methodology, { label: string; cls: string }> = {
  custom: { label: "Custom", cls: "bg-gray-100 text-gray-700" },
  gallup_q12: { label: "Q12", cls: "bg-purple-100 text-purple-700" },
  pulse: { label: "Pulse", cls: "bg-blue-100 text-blue-700" },
  trust_index: { label: "Trust Index", cls: "bg-amber-100 text-amber-700" },
  enps: { label: "eNPS", cls: "bg-green-100 text-green-700" },
};

export function TemplatesTab({ templates, onChange }: TemplatesTabProps) {
  const [busyId, setBusyId] = useState<number | null>(null);

  async function clone(t: EngagementTemplate) {
    setBusyId(t.id);
    try {
      await engagementApi.cloneTemplate(t.id, {});
      onChange();
    } catch (err) {
      console.error("Clone failed", err);
    } finally {
      setBusyId(null);
    }
  }

  if (templates.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-12 text-center text-sm text-[var(--color-gray-500)]">
        Library templates will appear here once you load the page.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {templates.map((t) => {
        const sections = parseSections(t.sections);
        const qCount = sections.reduce(
          (sum, s) => sum + (s.questions?.length || 0),
          0,
        );
        const badge =
          METHODOLOGY_BADGE[t.methodology] ?? METHODOLOGY_BADGE.custom;
        return (
          <div
            key={t.id}
            className="rounded-xl border border-[var(--color-gray-200)] bg-white p-5 flex flex-col"
          >
            <div className="flex items-start justify-between gap-3 mb-2">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-[var(--color-gray-400)]" />
                <span
                  className={`inline-block text-xs font-semibold px-2 py-0.5 rounded ${badge.cls}`}
                >
                  {badge.label}
                </span>
              </div>
              <button
                onClick={() => clone(t)}
                disabled={busyId === t.id}
                className="text-xs font-medium text-[var(--color-gray-500)] hover:text-rose-600 inline-flex items-center gap-1 disabled:opacity-50"
                aria-label={`Clone ${t.name}`}
              >
                {busyId === t.id ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
                Clone
              </button>
            </div>
            <h3 className="font-semibold text-[var(--color-gray-900)] mb-1">
              {t.name}
            </h3>
            {t.description && (
              <p className="text-sm text-[var(--color-gray-600)] mb-3 line-clamp-3">
                {t.description}
              </p>
            )}
            <div className="mt-auto pt-3 border-t border-[var(--color-gray-100)] flex items-center justify-between">
              <span className="text-xs text-[var(--color-gray-500)]">
                {qCount} question{qCount === 1 ? "" : "s"} · {sections.length}{" "}
                section{sections.length === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
