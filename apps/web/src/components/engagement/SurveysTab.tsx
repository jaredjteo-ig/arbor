"use client";

import Link from "next/link";
import { ChevronRight, Plus } from "lucide-react";
import type { EngagementSurvey } from "@/services/api/engagement";
import { formatAnonymityTierLabel } from "@/services/api/engagement";

interface SurveysTabProps {
  surveys: EngagementSurvey[];
  onLaunchClick: () => void;
}

export function SurveysTab({ surveys, onLaunchClick }: SurveysTabProps) {
  if (surveys.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-[var(--color-gray-200)] bg-white p-12 text-center">
        <p className="text-[var(--color-gray-700)] font-medium mb-2">
          No surveys launched yet
        </p>
        <p className="text-sm text-[var(--color-gray-500)] mb-4">
          Launch your first pulse to start collecting engagement signals.
        </p>
        <button
          onClick={onLaunchClick}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-rose-600 hover:bg-rose-700 text-white text-sm font-medium"
        >
          <Plus className="h-4 w-4" />
          Launch your first survey
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-[var(--color-gray-200)] overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-[var(--color-gray-50)] text-[var(--color-gray-500)] uppercase text-xs">
          <tr>
            <th className="text-left px-4 py-3 font-medium">Survey</th>
            <th className="text-left px-4 py-3 font-medium">Anonymity</th>
            <th className="text-left px-4 py-3 font-medium">Launched</th>
            <th className="text-left px-4 py-3 font-medium">Closes</th>
            <th className="text-right px-4 py-3 font-medium">Responses</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-gray-100)]">
          {surveys.map((s) => {
            const target = s.target_count || 0;
            const got = s.response_count ?? 0;
            const pct = target ? Math.round((got / target) * 100) : 0;
            return (
              <tr key={s.id} className="hover:bg-[var(--color-gray-50)]">
                <td className="px-4 py-3">
                  <Link
                    href={`/engagement/surveys/${s.id}`}
                    className="font-medium text-[var(--color-gray-900)] hover:text-rose-600"
                  >
                    {s.name}
                  </Link>
                  <div className="text-xs text-[var(--color-gray-500)] mt-0.5">
                    {s.closed_at ? "Closed" : "Open"}
                  </div>
                </td>
                <td className="px-4 py-3 text-[var(--color-gray-600)]">
                  {formatAnonymityTierLabel(s.anonymity_tier)}
                </td>
                <td className="px-4 py-3 text-[var(--color-gray-600)]">
                  {s.launched_at?.slice(0, 10) ?? "—"}
                </td>
                <td className="px-4 py-3 text-[var(--color-gray-600)]">
                  {s.closes_at?.slice(0, 10) ?? "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="font-semibold text-[var(--color-gray-900)]">
                    {got}
                  </span>
                  <span className="text-[var(--color-gray-500)]">
                    /{target} ({pct}%)
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/engagement/surveys/${s.id}`}
                    className="inline-flex items-center text-rose-600 hover:text-rose-700"
                    aria-label={`Open ${s.name}`}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Link>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
