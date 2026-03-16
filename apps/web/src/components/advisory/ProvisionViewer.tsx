"use client";

import { useEffect, useCallback, useState } from "react";
import { X, ExternalLink, BookOpen, Scale, Lightbulb } from "lucide-react";
import type { AuthorityLevel } from "@/components/design-system/SourceCitation";
import type { ProvisionDetail } from "@/types/api";
import { kbApi } from "@/services/api/kb";

/* ── Authority helpers ──────────────────────────────────────── */

const authorityStyles: Record<AuthorityLevel, string> = {
  statutory:
    "bg-[var(--color-authority-statutory-bg)] text-[var(--color-authority-statutory)] border-[var(--color-authority-statutory)]",
  guideline:
    "bg-[var(--color-authority-guideline-bg)] text-[var(--color-authority-guideline)] border-[var(--color-authority-guideline)]",
  "best-practice":
    "bg-[var(--color-authority-best-practice-bg)] text-[var(--color-authority-best-practice)] border-[var(--color-authority-best-practice)]",
};

const authorityLabels: Record<AuthorityLevel, string> = {
  statutory: "Statutory",
  guideline: "Guideline",
  "best-practice": "Best Practice",
};

function toAuthorityLevel(
  raw: string | undefined,
  fallbackId: string,
): AuthorityLevel {
  if (raw === "statutory" || raw === "guideline" || raw === "best-practice") {
    return raw;
  }
  return deriveAuthorityFromId(fallbackId);
}

/**
 * Derive authority level from provision ID prefix when no explicit
 * authority_level field is available.
 */
function deriveAuthorityFromId(provisionId: string): AuthorityLevel {
  const id = provisionId.toUpperCase();
  if (id.startsWith("EA-")) return "statutory";
  if (id.startsWith("CPF")) return "statutory";
  if (id.startsWith("EFMA-")) return "statutory";
  if (id.startsWith("WSH")) return "statutory";
  if (id.startsWith("WSHA-")) return "statutory";
  if (id.startsWith("WICA-")) return "statutory";
  if (id.startsWith("IRAS-")) return "statutory";
  if (id.startsWith("TGFEP-") || id.startsWith("TAFEP-")) return "guideline";
  if (id.startsWith("WFA-")) return "statutory";
  return "guideline";
}

/* ── Props ──────────────────────────────────────────────────── */

interface ProvisionViewerProps {
  /** The string provision reference, e.g. "EA-S95-KETs". */
  provisionId: string;
  /** Display title from the citation pill. */
  title: string;
  /** Pre-known authority level from the advisory response. */
  authorityLevel?: string;
  /** Called when the viewer should close. */
  onClose: () => void;
}

/* ── Component ──────────────────────────────────────────────── */

export function ProvisionViewer({
  provisionId,
  title,
  authorityLevel,
  onClose,
}: ProvisionViewerProps) {
  const [provision, setProvision] = useState<ProvisionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /* Close on Escape key */
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  /* Prevent body scroll while modal is open */
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  /* Fetch provision details */
  useEffect(() => {
    let cancelled = false;

    async function fetchProvision() {
      setLoading(true);
      setError(null);

      try {
        const data = await kbApi.provisionByRef(provisionId);
        if (!cancelled) {
          setProvision(data);
        }
      } catch {
        if (!cancelled) {
          setError(
            "Unable to load this provision right now. Please try again later.",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchProvision();
    return () => {
      cancelled = true;
    };
  }, [provisionId]);

  /* Resolve authority level: explicit prop > fetched from API > derived from ID prefix */
  const resolvedAuthority = toAuthorityLevel(
    authorityLevel ?? provision?.authority_level ?? undefined,
    provisionId,
  );

  return (
    /* Overlay */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Provision: ${title}`}
    >
      {/* Modal panel — stop propagation so clicking inside doesn't close */}
      <div
        className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl bg-[var(--color-surface-card,#fff)] shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-start justify-between gap-3 rounded-t-xl border-b border-[var(--color-gray-200)] bg-[var(--color-surface-card,#fff)] px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-base font-semibold text-[var(--color-gray-900)] leading-snug">
              {title}
            </h2>
            <p className="mt-1 text-xs text-[var(--color-gray-500)] font-mono">
              {provisionId}
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Authority badge */}
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${authorityStyles[resolvedAuthority]}`}
            >
              {authorityLabels[resolvedAuthority]}
            </span>

            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="rounded-md p-1 text-[var(--color-gray-400)] hover:text-[var(--color-gray-600)] hover:bg-[var(--color-gray-100)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
              aria-label="Close provision viewer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-5">
          {loading && <ProvisionSkeleton />}

          {error && (
            <div className="rounded-lg bg-[var(--color-risk-red)]/5 border border-[var(--color-risk-red)]/20 px-4 py-3 text-sm text-[var(--color-risk-red)]">
              {error}
            </div>
          )}

          {!loading && !error && provision && (
            <>
              {/* Formal text */}
              {provision.formal_text && (
                <section>
                  <SectionHeading icon={Scale} label="Formal Text" />
                  <p className="text-sm leading-relaxed text-[var(--color-gray-700)] whitespace-pre-wrap">
                    {provision.formal_text}
                  </p>
                </section>
              )}

              {/* Plain summary */}
              {provision.plain_summary && (
                <section>
                  <SectionHeading
                    icon={BookOpen}
                    label="Plain Language Summary"
                  />
                  <p className="text-sm leading-relaxed text-[var(--color-gray-700)] whitespace-pre-wrap">
                    {provision.plain_summary}
                  </p>
                </section>
              )}

              {/* Practical examples */}
              {provision.practical_examples.length > 0 && (
                <section>
                  <SectionHeading icon={Lightbulb} label="Practical Examples" />
                  <div className="space-y-3">
                    {provision.practical_examples.map((ex) => (
                      <div
                        key={ex.id}
                        className="rounded-lg border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-3 text-sm"
                      >
                        <p className="font-medium text-[var(--color-gray-800)]">
                          {ex.scenario}
                        </p>
                        {ex.outcome && (
                          <p className="mt-1 text-[var(--color-gray-600)]">
                            <span className="font-medium">Outcome:</span>{" "}
                            {ex.outcome}
                          </p>
                        )}
                        {ex.explanation && (
                          <p className="mt-1 text-[var(--color-gray-500)]">
                            {ex.explanation}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Cross-references */}
              {provision.cross_references.length > 0 && (
                <section>
                  <SectionHeading icon={BookOpen} label="Related Provisions" />
                  <ul className="space-y-1.5 text-sm text-[var(--color-gray-600)]">
                    {provision.cross_references.map((xref) => (
                      <li key={xref.id} className="flex items-start gap-2">
                        <span className="mt-1 block h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-gray-400)]" />
                        <span>
                          {xref.description}
                          {xref.relationship_type && (
                            <span className="ml-1 text-xs text-[var(--color-gray-400)]">
                              ({xref.relationship_type})
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}

          {/* Fallback when API returned no content */}
          {!loading && !error && !provision && (
            <p className="text-sm text-[var(--color-gray-500)]">
              No detailed information is available for this provision.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 flex items-center justify-between gap-3 rounded-b-xl border-t border-[var(--color-gray-200)] bg-[var(--color-surface-card,#fff)] px-5 py-3">
          {provision?.source_url ? (
            <a
              href={provision.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-[var(--color-primary)] hover:underline"
            >
              <ExternalLink className="h-4 w-4" />
              View official source
            </a>
          ) : (
            <span />
          )}

          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-[var(--color-gray-300)] bg-[var(--color-surface-card,#fff)] px-4 py-2 text-sm font-medium text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ─────────────────────────────────────────── */

function SectionHeading({
  icon: Icon,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <h3 className="flex items-center gap-1.5 text-sm font-semibold text-[var(--color-gray-800)] mb-2">
      <Icon className="h-4 w-4 text-[var(--color-gray-500)]" />
      {label}
    </h3>
  );
}

function ProvisionSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="space-y-2">
        <div className="h-4 w-28 rounded bg-[var(--color-gray-200)]" />
        <div className="h-3 w-full rounded bg-[var(--color-gray-200)]" />
        <div className="h-3 w-5/6 rounded bg-[var(--color-gray-200)]" />
        <div className="h-3 w-4/6 rounded bg-[var(--color-gray-200)]" />
      </div>
      <div className="space-y-2">
        <div className="h-4 w-36 rounded bg-[var(--color-gray-200)]" />
        <div className="h-3 w-full rounded bg-[var(--color-gray-200)]" />
        <div className="h-3 w-3/4 rounded bg-[var(--color-gray-200)]" />
      </div>
    </div>
  );
}
