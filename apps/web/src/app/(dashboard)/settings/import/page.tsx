"use client";

import { useState, useCallback, useRef } from "react";
import {
  Upload,
  Database,
  FileSpreadsheet,
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import {
  AppCard,
  AppButton,
  StepIndicator,
  LoadingState,
  AlertBanner,
  toast,
} from "@/components/design-system";
import { useImportPreview, useImportConfirm } from "@/hooks/api";
import type {
  ImportSource,
  ImportPreviewResponse,
  FieldMapping,
} from "@/services/api/integrations";

/* ── Constants ───────────────────────────────────────────── */

const WIZARD_STEPS = [
  "Select Source",
  "Configure",
  "Preview",
  "Confirm",
  "Complete",
];

const SOURCES: {
  id: ImportSource;
  name: string;
  description: string;
  icon: typeof Database;
}[] = [
  {
    id: "talenox",
    name: "Talenox",
    description:
      "Import employee data directly from your Talenox account via API",
    icon: Database,
  },
  {
    id: "hreasily",
    name: "HReasily",
    description:
      "Import employee and payroll data from your HReasily account via API",
    icon: Database,
  },
  {
    id: "csv",
    name: "CSV Upload",
    description: "Upload a CSV file with employee data",
    icon: FileSpreadsheet,
  },
];

/* ── Step 1: Select Source ───────────────────────────────── */

function SelectSourceStep({
  selected,
  onSelect,
}: {
  selected: ImportSource | null;
  onSelect: (source: ImportSource) => void;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-gray-600)]">
        Choose where to import your employee data from.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {SOURCES.map((source) => {
          const Icon = source.icon;
          const isSelected = selected === source.id;
          return (
            <button
              key={source.id}
              type="button"
              onClick={() => onSelect(source.id)}
              className={`
                flex flex-col items-center gap-3 p-6 rounded-[12px] border-2 transition-colors cursor-pointer text-center
                focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                ${
                  isSelected
                    ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                    : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                }
              `}
            >
              <Icon
                className={`h-8 w-8 ${isSelected ? "text-[var(--color-primary)]" : "text-[var(--color-gray-400)]"}`}
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-semibold text-[var(--color-gray-900)]">
                  {source.name}
                </p>
                <p className="text-xs text-[var(--color-gray-500)] mt-1">
                  {source.description}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

/* ── Step 2: Configure ───────────────────────────────────── */

function ConfigureStep({
  source,
  onFileSelect,
  file,
}: {
  source: ImportSource;
  onFileSelect: (file: File | null) => void;
  file: File | null;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (source === "csv") {
    return (
      <div className="space-y-4">
        <p className="text-sm text-[var(--color-gray-600)]">
          Upload your CSV file. The file should contain employee records with
          headers in the first row.
        </p>
        <div
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-[var(--color-gray-300)] rounded-[12px] p-8 text-center cursor-pointer
            hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)] transition-colors"
        >
          <Upload
            className="h-10 w-10 text-[var(--color-gray-400)] mx-auto mb-3"
            aria-hidden="true"
          />
          {file ? (
            <p className="text-sm font-medium text-[var(--color-gray-900)]">
              {file.name}{" "}
              <span className="text-[var(--color-gray-500)]">
                ({(file.size / 1024).toFixed(1)} KB)
              </span>
            </p>
          ) : (
            <>
              <p className="text-sm font-medium text-[var(--color-gray-900)]">
                Click to select a CSV file
              </p>
              <p className="text-xs text-[var(--color-gray-500)] mt-1">
                Accepted formats: .csv (max 10MB)
              </p>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={(e) => onFileSelect(e.target.files?.[0] ?? null)}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--color-gray-600)]">
        We will connect to your {source === "talenox" ? "Talenox" : "HReasily"}{" "}
        account and pull employee records. Make sure you have already connected
        the integration in Settings.
      </p>
      <AlertBanner
        variant="info"
        title="API connection required"
        description={`Ensure your ${source === "talenox" ? "Talenox" : "HReasily"} integration is connected in Settings > Integrations before proceeding.`}
      />
    </div>
  );
}

/* ── Step 3: Preview ─────────────────────────────────────── */

function PreviewStep({ preview }: { preview: ImportPreviewResponse }) {
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg bg-[var(--color-gray-50)] p-3 text-center">
          <p className="text-xs text-[var(--color-gray-500)]">Total Records</p>
          <p className="text-lg font-semibold text-[var(--color-gray-900)]">
            {preview.total_records}
          </p>
        </div>
        <div className="rounded-lg bg-[var(--color-success-bg)] p-3 text-center">
          <p className="text-xs text-[var(--color-gray-500)]">Valid</p>
          <p className="text-lg font-semibold text-[var(--color-success)]">
            {preview.valid_records}
          </p>
        </div>
        <div
          className={`rounded-lg p-3 text-center ${preview.validation_errors.length > 0 ? "bg-[var(--color-error-bg)]" : "bg-[var(--color-gray-50)]"}`}
        >
          <p className="text-xs text-[var(--color-gray-500)]">Errors</p>
          <p
            className={`text-lg font-semibold ${preview.validation_errors.length > 0 ? "text-[var(--color-error)]" : "text-[var(--color-gray-900)]"}`}
          >
            {preview.validation_errors.length}
          </p>
        </div>
        <div
          className={`rounded-lg p-3 text-center ${preview.duplicate_count > 0 ? "bg-[var(--color-warning-bg)]" : "bg-[var(--color-gray-50)]"}`}
        >
          <p className="text-xs text-[var(--color-gray-500)]">Duplicates</p>
          <p
            className={`text-lg font-semibold ${preview.duplicate_count > 0 ? "text-[var(--color-warning)]" : "text-[var(--color-gray-900)]"}`}
          >
            {preview.duplicate_count}
          </p>
        </div>
      </div>

      {/* Field Mappings */}
      <div>
        <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
          Field Mapping
        </h3>
        <div className="rounded-[8px] border border-[var(--color-gray-200)] overflow-x-auto">
          <table className="w-full min-w-[500px]">
            <thead>
              <tr className="bg-[var(--color-gray-50)]">
                <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                  Source Field
                </th>
                <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                  Maps To
                </th>
                <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                  Sample
                </th>
                <th className="text-center py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {preview.field_mappings.map((mapping, i) => (
                <tr key={i} className="border-t border-[var(--color-gray-100)]">
                  <td className="py-2 px-4 text-sm text-[var(--color-gray-700)]">
                    {mapping.source_field}
                  </td>
                  <td className="py-2 px-4 text-sm text-[var(--color-gray-900)] font-medium">
                    {mapping.target_field}
                  </td>
                  <td className="py-2 px-4 text-xs font-mono text-[var(--color-gray-500)]">
                    {mapping.sample_value ?? "-"}
                  </td>
                  <td className="py-2 px-4 text-center">
                    {mapping.is_mapped ? (
                      <CheckCircle className="h-4 w-4 text-[var(--color-success)] mx-auto" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-[var(--color-warning)] mx-auto" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Validation Errors */}
      {preview.validation_errors.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-error)] mb-3">
            Validation Errors ({preview.validation_errors.length})
          </h3>
          <div className="rounded-[8px] border border-[var(--color-error)] overflow-x-auto max-h-48 overflow-y-auto">
            <table className="w-full min-w-[400px]">
              <thead>
                <tr className="bg-[var(--color-error-bg)]">
                  <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                    Row
                  </th>
                  <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                    Field
                  </th>
                  <th className="text-left py-2 px-4 text-xs font-semibold text-[var(--color-gray-500)] uppercase">
                    Error
                  </th>
                </tr>
              </thead>
              <tbody>
                {preview.validation_errors.slice(0, 20).map((err, i) => (
                  <tr
                    key={i}
                    className="border-t border-[var(--color-gray-100)]"
                  >
                    <td className="py-2 px-4 text-sm text-[var(--color-gray-700)]">
                      {err.row}
                    </td>
                    <td className="py-2 px-4 text-sm text-[var(--color-gray-700)]">
                      {err.field}
                    </td>
                    <td className="py-2 px-4 text-sm text-[var(--color-error)]">
                      {err.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {preview.validation_errors.length > 20 && (
            <p className="text-xs text-[var(--color-gray-500)] mt-2">
              Showing first 20 errors of {preview.validation_errors.length}
            </p>
          )}
        </div>
      )}

      {/* Preview rows */}
      {preview.preview_rows.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)] mb-3">
            Data Preview (first {preview.preview_rows.length} rows)
          </h3>
          <div className="rounded-[8px] border border-[var(--color-gray-200)] overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-[var(--color-gray-50)]">
                  {Object.keys(preview.preview_rows[0]).map((key) => (
                    <th
                      key={key}
                      className="text-left py-2 px-3 font-semibold text-[var(--color-gray-500)] uppercase whitespace-nowrap"
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.preview_rows.map((row, i) => (
                  <tr
                    key={i}
                    className="border-t border-[var(--color-gray-100)]"
                  >
                    {Object.values(row).map((val, j) => (
                      <td
                        key={j}
                        className="py-2 px-3 text-[var(--color-gray-700)] whitespace-nowrap"
                      >
                        {val}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Step 4: Confirm ─────────────────────────────────────── */

function ConfirmStep({ preview }: { preview: ImportPreviewResponse }) {
  return (
    <div className="space-y-4 text-center py-6">
      <AlertTriangle
        className="h-12 w-12 text-[var(--color-warning)] mx-auto"
        aria-hidden="true"
      />
      <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
        Ready to import?
      </h3>
      <p className="text-sm text-[var(--color-gray-600)] max-w-md mx-auto">
        This will import {preview.valid_records} employee records into the
        system. {preview.duplicate_count} duplicates will be skipped.{" "}
        {preview.validation_errors.length > 0 &&
          `${preview.validation_errors.length} rows with errors will be skipped.`}
      </p>
      <AlertBanner
        variant="warning"
        title="This action cannot be easily undone"
        description="Make sure you have reviewed the field mapping and data preview before confirming."
      />
    </div>
  );
}

/* ── Step 5: Complete ────────────────────────────────────── */

function CompleteStep({
  result,
}: {
  result: { imported: number; skipped: number; errors: number };
}) {
  return (
    <div className="space-y-4 text-center py-8">
      <CheckCircle
        className="h-16 w-16 text-[var(--color-success)] mx-auto"
        aria-hidden="true"
      />
      <h3 className="text-lg font-semibold text-[var(--color-gray-900)]">
        Import Complete
      </h3>
      <div className="grid grid-cols-3 gap-4 max-w-sm mx-auto">
        <div className="rounded-lg bg-[var(--color-success-bg)] p-3 text-center">
          <p className="text-2xl font-bold text-[var(--color-success)]">
            {result.imported}
          </p>
          <p className="text-xs text-[var(--color-gray-500)]">Imported</p>
        </div>
        <div className="rounded-lg bg-[var(--color-warning-bg)] p-3 text-center">
          <p className="text-2xl font-bold text-[var(--color-warning)]">
            {result.skipped}
          </p>
          <p className="text-xs text-[var(--color-gray-500)]">Skipped</p>
        </div>
        <div className="rounded-lg bg-[var(--color-error-bg)] p-3 text-center">
          <p className="text-2xl font-bold text-[var(--color-error)]">
            {result.errors}
          </p>
          <p className="text-xs text-[var(--color-gray-500)]">Errors</p>
        </div>
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function MigrationWizardPage() {
  const [step, setStep] = useState(0);
  const [source, setSource] = useState<ImportSource | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [importResult, setImportResult] = useState<{
    imported: number;
    skipped: number;
    errors: number;
  } | null>(null);

  const importPreview = useImportPreview();
  const importConfirm = useImportConfirm();

  const handleNext = useCallback(async () => {
    if (step === 0 && !source) {
      toast.error("Please select a data source.");
      return;
    }

    // Step 1 -> 2: Trigger preview
    if (step === 1) {
      try {
        let formData: FormData | undefined;
        if (source === "csv" && file) {
          formData = new FormData();
          formData.append("file", file);
          formData.append("source", source!);
        }
        const result = await importPreview.mutateAsync({
          source: source!,
          data: formData,
        });
        setPreview(result);
        setStep(2);
        return;
      } catch {
        toast.error("Could not preview import data. Please try again.");
        return;
      }
    }

    // Step 3 -> 4: Execute import
    if (step === 3) {
      try {
        const result = await importConfirm.mutateAsync({
          source: source!,
          field_mappings: preview?.field_mappings ?? [],
        });
        setImportResult({
          imported: result.imported,
          skipped: result.skipped,
          errors: result.errors,
        });
        setStep(4);
        toast.success(result.message);
        return;
      } catch {
        toast.error("Import failed. Please try again.");
        return;
      }
    }

    setStep((s) => Math.min(s + 1, 4));
  }, [step, source, file, preview, importPreview, importConfirm]);

  const handleBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleReset = () => {
    setStep(0);
    setSource(null);
    setFile(null);
    setPreview(null);
    setImportResult(null);
  };

  const canProceed = () => {
    if (step === 0) return !!source;
    if (step === 1) {
      if (source === "csv") return !!file;
      return true;
    }
    return true;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Upload
          className="h-7 w-7 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
            Import Data
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mt-0.5">
            Migrate employee data from another HR system or CSV file.
          </p>
        </div>
      </div>

      {/* Stepper */}
      <StepIndicator steps={WIZARD_STEPS} currentStep={step} />

      {/* Step Content */}
      <AppCard variant="standard">
        {step === 0 && (
          <SelectSourceStep selected={source} onSelect={setSource} />
        )}
        {step === 1 && source && (
          <ConfigureStep source={source} onFileSelect={setFile} file={file} />
        )}
        {step === 2 && preview && <PreviewStep preview={preview} />}
        {step === 3 && preview && <ConfirmStep preview={preview} />}
        {step === 4 && importResult && <CompleteStep result={importResult} />}

        {/* Loading during preview/import */}
        {(importPreview.isPending || importConfirm.isPending) && (
          <div className="flex flex-col items-center gap-3 py-8">
            <Loader2
              className="h-8 w-8 text-[var(--color-primary)] animate-spin"
              aria-hidden="true"
            />
            <p className="text-sm text-[var(--color-gray-500)]">
              {importPreview.isPending
                ? "Analyzing your data..."
                : "Importing records..."}
            </p>
          </div>
        )}
      </AppCard>

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between">
        <div>
          {step > 0 && step < 4 && (
            <AppButton variant="outlined" size="md" onClick={handleBack}>
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Back
            </AppButton>
          )}
        </div>
        <div>
          {step < 4 ? (
            <AppButton
              variant="primary"
              size="md"
              onClick={handleNext}
              disabled={!canProceed()}
              loading={importPreview.isPending || importConfirm.isPending}
            >
              {step === 3 ? "Confirm Import" : "Next"}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </AppButton>
          ) : (
            <AppButton variant="primary" size="md" onClick={handleReset}>
              Start New Import
            </AppButton>
          )}
        </div>
      </div>
    </div>
  );
}
