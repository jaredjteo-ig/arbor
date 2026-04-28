"use client";

/**
 * DocumentUploadStep — file picker + upload via POST /onboarding/steps/{id}/upload.
 *
 * Backend enforces 10 MB max, allowed extensions (PDF/JPG/JPEG/PNG/DOCX),
 * mime-type and magic-byte checks. Client mirrors the size limit so users
 * get fast feedback before a wasted round-trip.
 */

import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, RefreshCw } from "lucide-react";
import { toast } from "@/components/design-system";
import {
  onboardingApi,
  type StepProgressWithStep,
} from "@/services/api/onboarding";

export interface DocumentUploadStepProps {
  sp: StepProgressWithStep;
  onStepCompleted: () => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB — matches backend MAX_FILE_SIZE.

export function DocumentUploadStep({
  sp,
  onStepCompleted,
}: DocumentUploadStepProps) {
  const { t } = useTranslation();
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const isCompleted = sp.status === "completed";

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      toast.error(
        t("onboarding.step.upload.too_large", {
          defaultValue: "File must be 10 MB or smaller.",
        }),
      );
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await onboardingApi.uploadStepDocument(sp.id, formData);
      toast.success(
        t("onboarding.step.upload.uploaded", {
          defaultValue: "Document uploaded",
        }),
      );
      onStepCompleted();
    } catch {
      toast.error(
        t("onboarding.step.upload.failed", {
          defaultValue: "Failed to upload document. Please try again.",
        }),
      );
    } finally {
      setSubmitting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  return (
    <div className="mt-2 space-y-2">
      {isCompleted && sp.document_url ? (
        <div className="flex items-center gap-2 text-sm text-emerald-600">
          <CheckCircle2 className="h-4 w-4" />
          <span>
            {t("onboarding.step.upload.uploaded_label", {
              defaultValue: "Uploaded",
            })}
            : {sp.document_url.split("/").pop() ?? "document"}
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png,.docx"
            onChange={handleUpload}
            disabled={submitting}
            aria-label={t("onboarding.step.upload.choose_file", {
              defaultValue: "Choose a document to upload",
            })}
            className="text-sm text-[var(--color-gray-600)] file:mr-3 file:rounded-[8px] file:border-0 file:bg-[var(--color-primary)] file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white file:cursor-pointer hover:file:bg-[var(--color-primary-light)] disabled:opacity-50"
          />
          {submitting && (
            <RefreshCw className="h-4 w-4 text-[var(--color-gray-400)] animate-spin" />
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentUploadStep;
