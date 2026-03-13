"use client";

/* ── ResultPanel ─────────────────────────────────────────── */
/* Wrapper for calculator results: heading, body, citations,  */
/* and a link to ask the advisory about the result.           */

import type { ReactNode } from "react";
import { AppCard, SourceCitation } from "@/components/design-system";
import { MessageSquare } from "lucide-react";
import Link from "next/link";

interface Citation {
  label: string;
  authority: "statutory" | "guideline" | "best-practice";
}

interface ResultPanelProps {
  title?: string;
  citations?: Citation[];
  advisoryQuery?: string;
  notes?: string[];
  children: ReactNode;
}

export function ResultPanel({
  title = "Results",
  citations = [],
  advisoryQuery,
  notes = [],
  children,
}: ResultPanelProps) {
  return (
    <AppCard variant="elevated">
      <div className="space-y-4">
        <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
          {title}
        </h3>

        <div className="divide-y divide-[var(--color-gray-200)]">
          {children}
        </div>

        {notes.length > 0 && (
          <div className="pt-2 space-y-1">
            {notes.map((note, i) => (
              <p
                key={i}
                className="text-xs text-[var(--color-gray-500)] leading-relaxed"
              >
                {note}
              </p>
            ))}
          </div>
        )}

        {citations.length > 0 && (
          <div className="pt-2 flex flex-wrap gap-2">
            {citations.map((c, i) => (
              <SourceCitation key={i} label={c.label} authority={c.authority} />
            ))}
          </div>
        )}

        {advisoryQuery && (
          <div className="pt-2 border-t border-[var(--color-gray-200)]">
            <Link
              href={`/advisory?query=${encodeURIComponent(advisoryQuery)}`}
              className="inline-flex items-center gap-2 text-sm text-[var(--color-primary)] hover:underline"
            >
              <MessageSquare className="h-4 w-4" />
              Ask a question about this
            </Link>
          </div>
        )}
      </div>
    </AppCard>
  );
}
