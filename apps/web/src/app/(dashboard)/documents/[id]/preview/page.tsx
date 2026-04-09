"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FileText, ArrowLeft, Shield, BookOpen, Download } from "lucide-react";
import { AppCard, AppButton, SourceCitation } from "@/components/design-system";
import { documentsApi } from "@/services/api/documents";
import type { DocumentTemplate } from "@/types/api";

export default function TemplatePreviewPage() {
  const params = useParams();
  const templateId = Number(params.id);
  const [template, setTemplate] = useState<DocumentTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!templateId || isNaN(templateId)) {
      setError("Invalid template ID");
      setLoading(false);
      return;
    }

    documentsApi
      .getTemplate(templateId)
      .then((t) => {
        setTemplate(t);
        setLoading(false);
      })
      .catch((err) => {
        setError(
          err instanceof Error
            ? err.message
            : String((err as any)?.detail ?? "Failed to load template"),
        );
        setLoading(false);
      });
  }, [templateId]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <p className="text-[var(--color-gray-500)]">Loading template...</p>
      </div>
    );
  }

  if (error || !template) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Link
          href="/documents"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to templates
        </Link>
        <AppCard variant="standard">
          <p className="text-[var(--color-gray-600)]">
            {error || "Template not found."}
          </p>
        </AppCard>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/documents"
        className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Back to templates
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0 mt-0.5">
            <FileText className="h-6 w-6 text-[var(--color-primary)]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[var(--color-gray-900)]">
              {template.name}
            </h1>
            <p className="text-sm text-[var(--color-gray-500)] mt-1">
              {template.description}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--color-gray-100)] text-[var(--color-gray-600)]">
                {template.category}
              </span>
              <span className="text-xs text-[var(--color-gray-400)]">
                Version {template.version ?? 1}
              </span>
            </div>
          </div>
        </div>
        <Link href={`/documents/${templateId}/generate`}>
          <AppButton>Generate Document</AppButton>
        </Link>
      </div>

      {/* Compliance notes */}
      {template.compliance_notes.length > 0 && (
        <AppCard variant="standard">
          <div className="flex items-start gap-3">
            <Shield className="h-5 w-5 text-[var(--color-primary)] mt-0.5 shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
                Compliance Notes
              </h3>
              <ul className="space-y-1.5">
                {template.compliance_notes.map((note, i) => (
                  <li
                    key={i}
                    className="text-sm text-[var(--color-gray-600)] flex items-start gap-2"
                  >
                    <span className="text-[var(--color-primary)] mt-1.5 shrink-0 block w-1.5 h-1.5 rounded-full bg-[var(--color-primary)]" />
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </AppCard>
      )}

      {/* Linked provisions */}
      {template.linked_provisions && template.linked_provisions.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-[var(--color-gray-700)] mb-2 flex items-center gap-1.5">
            <BookOpen className="h-4 w-4" /> Linked Legal Provisions
          </h3>
          <div className="flex flex-wrap gap-2">
            {template.linked_provisions.map((p) => (
              <SourceCitation key={p} label={p} authority="statutory" />
            ))}
          </div>
        </div>
      )}

      {/* Required fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <AppCard variant="standard">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
            Required Fields ({template.required_fields.length})
          </h3>
          <div className="space-y-1">
            {template.required_fields.map((f) => (
              <p key={f} className="text-sm text-[var(--color-gray-600)]">
                {f.replace(/_/g, " ")}
              </p>
            ))}
          </div>
        </AppCard>
        {template.optional_fields.length > 0 && (
          <AppCard variant="standard">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-2">
              Optional Fields ({template.optional_fields.length})
            </h3>
            <div className="space-y-1">
              {template.optional_fields.map((f) => (
                <p key={f} className="text-sm text-[var(--color-gray-500)]">
                  {f.replace(/_/g, " ")}
                </p>
              ))}
            </div>
          </AppCard>
        )}
      </div>

      {/* Template content preview */}
      {template.content && (
        <AppCard variant="elevated">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Template Preview
            </h3>
            <span className="text-xs text-[var(--color-gray-400)]">
              Fields shown as {"{{field_name}}"} placeholders
            </span>
          </div>
          <div className="bg-white p-6 rounded-lg border border-[var(--color-gray-200)] max-h-[600px] overflow-y-auto">
            {template.content.split("\n").map((line, i) => {
              const trimmed = line.trim();
              // Divider lines
              if (trimmed && /^[-=]{5,}$/.test(trimmed)) {
                return (
                  <hr
                    key={i}
                    className="my-3 border-t border-[var(--color-gray-200)]"
                  />
                );
              }
              // Blank lines
              if (!trimmed) return <div key={i} className="h-2" />;
              // Section headings: all-caps lines or numbered headings
              const isHeading =
                (trimmed === trimmed.toUpperCase() &&
                  trimmed.length > 5 &&
                  /[A-Z]{3,}/.test(trimmed)) ||
                /^\d+\.\s+[A-Z]/.test(trimmed) ||
                /^SECTION\s+[A-Z]:/.test(trimmed);
              if (isHeading) {
                return (
                  <p
                    key={i}
                    className="text-sm font-semibold text-[var(--color-gray-900)] mt-4 mb-1"
                  >
                    {trimmed}
                  </p>
                );
              }
              // Signature / underscore lines
              if (/___/.test(trimmed)) {
                return (
                  <p
                    key={i}
                    className="text-sm text-[var(--color-gray-500)] mt-3 mb-1 font-mono"
                  >
                    {trimmed}
                  </p>
                );
              }
              // Sub-items
              if (
                trimmed.startsWith("- ") ||
                trimmed.startsWith("[ ]") ||
                /^\d+\.\d+\s/.test(trimmed)
              ) {
                return (
                  <p
                    key={i}
                    className="text-sm text-[var(--color-gray-700)] pl-4 my-0.5"
                  >
                    {trimmed}
                  </p>
                );
              }
              // Highlight placeholders
              const parts = trimmed.split(/(\{\{[^}]+\}\})/g);
              return (
                <p
                  key={i}
                  className="text-sm text-[var(--color-gray-700)] my-0.5"
                >
                  {parts.map((part, j) =>
                    /^\{\{[^}]+\}\}$/.test(part) ? (
                      <span
                        key={j}
                        className="bg-[var(--color-primary-bg)] text-[var(--color-primary)] px-1 rounded text-xs font-medium"
                      >
                        {part}
                      </span>
                    ) : (
                      <span key={j}>{part}</span>
                    ),
                  )}
                </p>
              );
            })}
          </div>
        </AppCard>
      )}
    </div>
  );
}
