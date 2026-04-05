"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  FileText,
  ArrowLeft,
  Shield,
  Download,
  Copy,
  Check,
} from "lucide-react";
import { AppCard, AppButton, SourceCitation } from "@/components/design-system";
import { documentsApi } from "@/services/api/documents";
import type { DocumentTemplate, DocumentGenerateResponse } from "@/types/api";

export default function DocumentGeneratePage() {
  const params = useParams();
  const templateId = Number(params.id);
  const [template, setTemplate] = useState<DocumentTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<DocumentGenerateResponse | null>(null);
  const [copied, setCopied] = useState(false);

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
        // Initialize field state
        const initial: Record<string, string> = {};
        for (const f of t.required_fields) initial[f] = "";
        for (const f of t.optional_fields) initial[f] = "";
        setFields(initial);
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

  const updateField = useCallback((name: string, value: string) => {
    setFields((prev) => ({ ...prev, [name]: value }));
  }, []);

  const handleGenerate = async () => {
    if (!template) return;

    // Validate required fields
    const missing = template.required_fields.filter((f) => !fields[f]?.trim());
    if (missing.length > 0) {
      setError(
        `Please fill in: ${missing.map((f) => f.replace(/_/g, " ")).join(", ")}`,
      );
      return;
    }

    setError(null);
    setGenerating(true);

    try {
      const response = await documentsApi.generate({
        template_id: templateId,
        fields,
      });
      setResult(response);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail || "Failed to generate document");
    } finally {
      setGenerating(false);
    }
  };

  const handleCopy = () => {
    if (!result?.document?.content) return;
    navigator.clipboard.writeText(result.document.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!result?.document?.content) return;
    const blob = new Blob([result.document.content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${result.document.title.replace(/\s+/g, "_")}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center">
        <p className="text-[var(--color-gray-500)]">Loading template...</p>
      </div>
    );
  }

  if (!template) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Link
          href="/documents"
          className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
        >
          <ArrowLeft className="h-4 w-4" /> Back to templates
        </Link>
        <AppCard variant="standard">
          <p className="text-[var(--color-gray-600)]">Template not found.</p>
        </AppCard>
      </div>
    );
  }

  const fieldLabel = (name: string) =>
    name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href={`/documents/${templateId}/preview`}
        className="inline-flex items-center gap-1 text-sm text-[var(--color-primary)] hover:underline"
      >
        <ArrowLeft className="h-4 w-4" /> Back to preview
      </Link>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-[var(--color-primary-bg)] shrink-0 mt-0.5">
          <FileText className="h-6 w-6 text-[var(--color-primary)]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[var(--color-gray-900)]">
            Generate: {template.name}
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-1">
            Fill in the fields below to generate a customised document.
          </p>
        </div>
      </div>

      {/* Compliance reminder */}
      {template.compliance_notes.length > 0 && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-[var(--color-primary-bg)]">
          <Shield className="h-4 w-4 text-[var(--color-primary)] mt-0.5 shrink-0" />
          <p className="text-xs text-[var(--color-gray-600)]">
            {template.compliance_notes[0]}
          </p>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Form */}
      {!result && (
        <AppCard variant="standard">
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
              Required Fields
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {template.required_fields.map((name) => (
                <div key={name}>
                  <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1">
                    {fieldLabel(name)} <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={fields[name] || ""}
                    onChange={(e) => updateField(name, e.target.value)}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-900)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
                    placeholder={`Enter ${fieldLabel(name).toLowerCase()}`}
                  />
                </div>
              ))}
            </div>

            {template.optional_fields.length > 0 && (
              <>
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)] pt-2">
                  Optional Fields
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {template.optional_fields.map((name) => (
                    <div key={name}>
                      <label className="block text-sm font-medium text-[var(--color-gray-500)] mb-1">
                        {fieldLabel(name)}
                      </label>
                      <input
                        type="text"
                        value={fields[name] || ""}
                        onChange={(e) => updateField(name, e.target.value)}
                        className="w-full px-3 py-2 text-sm rounded-lg border border-[var(--color-gray-200)] bg-white text-[var(--color-gray-900)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] focus:border-transparent"
                        placeholder={`Enter ${fieldLabel(name).toLowerCase()}`}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}

            <div className="pt-2">
              <AppButton onClick={handleGenerate} disabled={generating}>
                {generating ? "Generating..." : "Generate Document"}
              </AppButton>
            </div>
          </div>
        </AppCard>
      )}

      {/* Generated result */}
      {result && (
        <div className="space-y-4">
          <AppCard variant="elevated">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                {result.document.title}
              </h3>
              <div className="flex gap-2">
                <AppButton variant="text" size="sm" onClick={handleCopy}>
                  {copied ? (
                    <>
                      <Check className="h-4 w-4 mr-1" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="h-4 w-4 mr-1" /> Copy
                    </>
                  )}
                </AppButton>
                <AppButton variant="text" size="sm" onClick={handleDownload}>
                  <Download className="h-4 w-4 mr-1" /> Download
                </AppButton>
              </div>
            </div>
            <pre className="text-xs text-[var(--color-gray-700)] whitespace-pre-wrap font-mono bg-[var(--color-gray-50)] p-4 rounded-lg border border-[var(--color-gray-200)] max-h-[600px] overflow-y-auto leading-relaxed">
              {result.document.content}
            </pre>
          </AppCard>

          {/* Provisions applied */}
          {result.provisions_applied.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-[var(--color-gray-700)] mb-2">
                Provisions Applied
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.provisions_applied.map((p) => (
                  <SourceCitation key={p} label={p} authority="statutory" />
                ))}
              </div>
            </div>
          )}

          {/* Compliance notes */}
          {result.compliance_notes.length > 0 && (
            <AppCard variant="standard">
              <div className="flex items-start gap-2">
                <Shield className="h-4 w-4 text-[var(--color-primary)] mt-0.5 shrink-0" />
                <div className="space-y-1">
                  {result.compliance_notes.map((note, i) => (
                    <p key={i} className="text-xs text-[var(--color-gray-600)]">
                      {note}
                    </p>
                  ))}
                </div>
              </div>
            </AppCard>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <AppButton
              variant="text"
              onClick={() => {
                setResult(null);
                setError(null);
              }}
            >
              Generate Another
            </AppButton>
            <Link href="/documents">
              <AppButton variant="text">Back to Templates</AppButton>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
