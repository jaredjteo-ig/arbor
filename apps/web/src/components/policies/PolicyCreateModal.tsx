"use client";

import { useState, useRef, useEffect } from "react";
import {
  AppButton,
  AppInput,
  DatePicker,
  toast,
} from "@/components/design-system";
import {
  X,
  FileText,
  Upload,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Edit,
  Trash2,
} from "lucide-react";
import {
  policiesApi,
  type PolicyRecord,
  type StatutoryFloorWarning,
} from "@/services/api/policies";

/* -- Constants --------------------------------------------------- */

const CATEGORIES = [
  { value: "employment_terms", label: "Employment Terms" },
  { value: "leave_absence", label: "Leave & Absence" },
  { value: "compensation_benefits", label: "Compensation & Benefits" },
  { value: "workplace_safety", label: "Workplace Safety" },
  { value: "fair_employment", label: "Fair Employment" },
  { value: "foreign_worker", label: "Foreign Workers" },
  { value: "tax_filing", label: "Tax & Filing" },
  { value: "general_hr", label: "General HR" },
  { value: "code_of_conduct", label: "Code of Conduct" },
] as const;

const ACCEPTED_FILE_TYPES = ".pdf,.doc,.docx,.txt";
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

/* -- Types ------------------------------------------------------- */

type ModalTab = "write" | "upload";

/** Initial prefill for the modal — red-team P5-VL-2. When the
 *  compliance Action Item deep-links via /policies?template=<slug>,
 *  the policies page fetches the prefill via
 *  documentsApi.getTemplatePrefillBySlug and passes it here so the
 *  modal opens already populated.
 */
export interface PolicyDraftPrefill {
  title?: string;
  category?: string;
  content?: string;
  /** Optional human label for the prefill source (e.g. "FWA Policy"). */
  source?: string;
}

interface PolicyCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  /** Prefill applied when the modal opens. Cleared on close so the
   *  next open starts blank — same lifecycle as the existing form
   *  fields.
   */
  initialDraft?: PolicyDraftPrefill | null;
}

/* -- Extraction status badge ------------------------------------- */

function ExtractionStatusBadge({ status }: { status: string }) {
  const s = (status || "").toLowerCase();
  if (
    s === "completed" ||
    s === "complete" ||
    s === "success" ||
    s === "good"
  ) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="h-3 w-3" />
        Extracted
      </span>
    );
  }
  if (s === "processing" || s === "pending") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
        <Loader2 className="h-3 w-3 animate-spin" />
        Processing
      </span>
    );
  }
  if (s === "failed" || s === "timeout") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
        <AlertCircle className="h-3 w-3" />
        {s === "timeout" ? "Timeout" : "Failed"}
      </span>
    );
  }
  // Default for empty/unknown — treat as success (manual text entry has no extraction)
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
      <CheckCircle2 className="h-3 w-3" />
      {s ? s.charAt(0).toUpperCase() + s.slice(1) : "Complete"}
    </span>
  );
}

/* -- Component --------------------------------------------------- */

export function PolicyCreateModal({
  isOpen,
  onClose,
  onSuccess,
  initialDraft,
}: PolicyCreateModalProps) {
  const [activeTab, setActiveTab] = useState<ModalTab>("write");

  /* Write tab state */
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [customCategory, setCustomCategory] = useState("");
  const [content, setContent] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [requiresAck, setRequiresAck] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  /* Red-team P5-VL-2: apply prefill when the modal opens. The
   * `isOpen + initialDraft` dependency means a fresh deep-link
   * (compliance → policies?template=fwa) re-applies the prefill
   * each time. Closing the modal lets `resetState` blank the
   * fields so the next manual "Add Policy" click starts empty. */
  useEffect(() => {
    if (!isOpen || !initialDraft) return;
    if (initialDraft.title) setTitle(initialDraft.title);
    if (initialDraft.category) setCategory(initialDraft.category);
    if (initialDraft.content) setContent(initialDraft.content);
    // Always switch to the Write tab on prefill — uploaded
    // document prefill is not yet supported.
    setActiveTab("write");
  }, [isOpen, initialDraft]);

  /* Upload tab state */
  const [file, setFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadCategory, setUploadCategory] = useState("");
  const [uploadCustomCategory, setUploadCustomCategory] = useState("");
  const [uploadDate, setUploadDate] = useState("");
  const [uploadRequiresAck, setUploadRequiresAck] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedPolicy, setUploadedPolicy] = useState<PolicyRecord | null>(
    null,
  );
  const [warnings, setWarnings] = useState<StatutoryFloorWarning[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  if (!isOpen) return null;

  function resetState() {
    setActiveTab("write");
    setTitle("");
    setCategory("");
    setCustomCategory("");
    setContent("");
    setEffectiveDate("");
    setRequiresAck(false);
    setFile(null);
    setUploadTitle("");
    setUploadCategory("");
    setUploadCustomCategory("");
    setUploadDate("");
    setUploadRequiresAck(false);
    setUploadedPolicy(null);
    setWarnings([]);
  }

  function handleClose() {
    resetState();
    onClose();
  }

  function resolveCategory(cat: string, custom: string): string {
    return cat === "Other" ? custom.trim() || "Other" : cat;
  }

  /* -- Write handlers ------------------------------------------- */

  async function handleSaveDraft() {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    if (!category) {
      toast.error("Please select a category");
      return;
    }

    setIsSaving(true);
    try {
      const result = await policiesApi.create({
        title: title.trim(),
        category: resolveCategory(category, customCategory),
        content,
        effective_date: effectiveDate || undefined,
        requires_acknowledgment: requiresAck,
        status: "draft",
      });
      const belowMinimum = (result.statutory_floor_warnings ?? []).filter(
        (w) => w.status === "below_minimum",
      );
      if (belowMinimum.length > 0) {
        setWarnings(belowMinimum);
        setUploadedPolicy(result.policy);
      } else {
        resetState();
        onSuccess();
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to save draft";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  async function handlePublish() {
    if (!title.trim()) {
      toast.error("Title is required");
      return;
    }
    if (!category) {
      toast.error("Please select a category");
      return;
    }
    if (!content.trim()) {
      toast.error("Policy content is required to publish");
      return;
    }

    setIsSaving(true);
    try {
      const result = await policiesApi.create({
        title: title.trim(),
        category: resolveCategory(category, customCategory),
        content,
        effective_date: effectiveDate || undefined,
        requires_acknowledgment: requiresAck,
        status: "active",
      });
      const belowMinimum = (result.statutory_floor_warnings ?? []).filter(
        (w) => w.status === "below_minimum",
      );
      if (belowMinimum.length > 0) {
        setWarnings(belowMinimum);
        setUploadedPolicy(result.policy);
      } else {
        resetState();
        onSuccess();
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to publish policy";
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  }

  /* -- Upload handlers ------------------------------------------ */

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0];
    if (!selected) return;

    if (selected.size > MAX_FILE_SIZE_BYTES) {
      toast.error("File is too large. Maximum size is 10 MB.");
      return;
    }

    setFile(selected);
    /* Auto-fill title from filename (without extension) */
    if (!uploadTitle) {
      const nameWithoutExt = selected.name.replace(/\.[^.]+$/, "");
      setUploadTitle(
        nameWithoutExt
          .replace(/[-_]/g, " ")
          .replace(/\b\w/g, (c) => c.toUpperCase()),
      );
    }
  }

  async function handleUpload() {
    if (!file) {
      toast.error("Please select a file");
      return;
    }
    if (!uploadTitle.trim()) {
      toast.error("Title is required");
      return;
    }
    if (!uploadCategory) {
      toast.error("Please select a category");
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", uploadTitle.trim());
      formData.append(
        "category",
        resolveCategory(uploadCategory, uploadCustomCategory),
      );
      if (uploadDate) formData.append("effective_date", uploadDate);
      formData.append("requires_acknowledgment", String(uploadRequiresAck));

      const result = await policiesApi.upload(formData);
      setUploadedPolicy(result.policy);
      const belowMinimum = (result.statutory_floor_warnings ?? []).filter(
        (w) => w.status === "below_minimum",
      );
      if (belowMinimum.length > 0) {
        setWarnings(belowMinimum);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to upload document";
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  function handleUploadDone() {
    resetState();
    onSuccess();
  }

  /* -- Render --------------------------------------------------- */

  const showUploadPreview = uploadedPolicy !== null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative w-full max-w-lg mx-4 max-h-[90vh] rounded-[12px] border border-[var(--color-gray-200)] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] flex flex-col">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-[var(--color-gray-200)]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-[var(--color-primary)]" />
              <h2 className="text-lg font-semibold text-[var(--color-gray-900)]">
                {/* Red-team P5-VL-2: surface the prefill source in the
                    modal title so the buyer knows the form was wired
                    by the compliance Action Item, not a blank slate. */}
                {initialDraft?.source
                  ? `Publish ${initialDraft.source}`
                  : "Add Policy"}
              </h2>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="p-1 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
            >
              <X className="h-5 w-5 text-[var(--color-gray-500)]" />
            </button>
          </div>

          {/* Tabs */}
          {!showUploadPreview && (
            <div className="flex gap-1">
              <button
                type="button"
                onClick={() => setActiveTab("write")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === "write"
                    ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)]"
                    : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
                }`}
              >
                <FileText className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
                Write Policy
              </button>
              <button
                type="button"
                onClick={() => setActiveTab("upload")}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
                  activeTab === "upload"
                    ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)]"
                    : "text-[var(--color-gray-500)] hover:text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
                }`}
              >
                <Upload className="h-4 w-4 inline-block mr-1.5 -mt-0.5" />
                Upload Document
              </button>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-4 overflow-y-auto flex-1">
          {/* -- Write Tab -- */}
          {activeTab === "write" && !showUploadPreview && (
            <div className="space-y-4">
              <AppInput
                label="Policy Title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Annual Leave Policy"
                required
              />

              <AppInput
                variant="select"
                label="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                options={CATEGORIES.map((c) => ({
                  value: c.value,
                  label: c.label,
                }))}
                placeholder="Select a category"
                required
              />

              {category === "Other" && (
                <AppInput
                  label="Custom Category"
                  value={customCategory}
                  onChange={(e) => setCustomCategory(e.target.value)}
                  placeholder="Enter category name"
                />
              )}

              <AppInput
                variant="textarea"
                label="Policy Content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write your policy content here..."
                rows={8}
              />

              <DatePicker
                label="Effective Date"
                value={effectiveDate}
                onChange={setEffectiveDate}
                placeholder="Select effective date"
              />

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requiresAck}
                  onChange={(e) => setRequiresAck(e.target.checked)}
                  className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                />
                <span className="text-sm text-[var(--color-gray-700)]">
                  Require employee acknowledgment
                </span>
              </label>
            </div>
          )}

          {/* -- Upload Tab -- */}
          {activeTab === "upload" && !showUploadPreview && (
            <div className="space-y-4">
              {/* File input */}
              <div>
                <label className="block text-sm font-medium text-[var(--color-gray-700)] mb-1.5">
                  Document File
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="
                    flex flex-col items-center justify-center gap-2
                    rounded-[8px] border-2 border-dashed border-[var(--color-gray-300)]
                    bg-[var(--color-gray-50)] px-6 py-8 cursor-pointer
                    hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)]
                    transition-colors
                  "
                >
                  <Upload className="h-8 w-8 text-[var(--color-gray-400)]" />
                  {file ? (
                    <div className="text-center">
                      <p className="text-sm font-medium text-[var(--color-gray-900)]">
                        {file.name}
                      </p>
                      <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div className="text-center">
                      <p className="text-sm text-[var(--color-gray-600)]">
                        Click to select a file
                      </p>
                      <p className="text-xs text-[var(--color-gray-400)] mt-0.5">
                        PDF, DOCX, or TXT (max 10 MB)
                      </p>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_FILE_TYPES}
                  onChange={handleFileChange}
                  className="hidden"
                />
              </div>

              <AppInput
                label="Policy Title"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="Auto-filled from filename"
                required
              />

              <AppInput
                variant="select"
                label="Category"
                value={uploadCategory}
                onChange={(e) => setUploadCategory(e.target.value)}
                options={CATEGORIES.map((c) => ({
                  value: c.value,
                  label: c.label,
                }))}
                placeholder="Select a category"
                required
              />

              {uploadCategory === "Other" && (
                <AppInput
                  label="Custom Category"
                  value={uploadCustomCategory}
                  onChange={(e) => setUploadCustomCategory(e.target.value)}
                  placeholder="Enter category name"
                />
              )}

              <DatePicker
                label="Effective Date"
                value={uploadDate}
                onChange={setUploadDate}
                placeholder="Select effective date"
              />

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={uploadRequiresAck}
                  onChange={(e) => setUploadRequiresAck(e.target.checked)}
                  className="h-4 w-4 rounded border-[var(--color-gray-300)] text-[var(--color-primary)] focus:ring-[var(--color-primary)]"
                />
                <span className="text-sm text-[var(--color-gray-700)]">
                  Require employee acknowledgment
                </span>
              </label>
            </div>
          )}

          {/* -- Upload Preview -- */}
          {showUploadPreview && uploadedPolicy && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                  Upload Complete
                </h3>
                <ExtractionStatusBadge
                  status={uploadedPolicy.extraction_status}
                />
              </div>

              {/* Statutory floor warnings */}
              {warnings.length > 0 && (
                <div className="flex items-start gap-2 rounded-[8px] border border-amber-200 bg-amber-50 px-4 py-3">
                  <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      Compliance Warnings
                    </p>
                    <ul className="mt-1 space-y-1">
                      {warnings.map((w, idx) => (
                        <li key={idx} className="text-xs text-amber-700">
                          {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-[var(--color-gray-50)] p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[var(--color-gray-500)]">
                    Title
                  </span>
                  <span className="text-sm text-[var(--color-gray-900)]">
                    {uploadedPolicy.title}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-[var(--color-gray-500)]">
                    Category
                  </span>
                  <span className="text-sm text-[var(--color-gray-900)]">
                    {CATEGORIES.find((c) => c.value === uploadedPolicy.category)
                      ?.label || uploadedPolicy.category}
                  </span>
                </div>
                {uploadedPolicy.file_name && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-[var(--color-gray-500)]">
                      File
                    </span>
                    <span className="text-sm text-[var(--color-gray-900)]">
                      {uploadedPolicy.file_name}
                    </span>
                  </div>
                )}
              </div>

              {/* Content preview */}
              {uploadedPolicy.content ? (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-[var(--color-gray-500)]">
                      Extracted Content Preview
                    </span>
                    <AppButton
                      variant="text"
                      size="sm"
                      onClick={() => {
                        /* Navigate to the detail page for editing */
                        handleUploadDone();
                        window.location.href = `/policies/${uploadedPolicy.id}`;
                      }}
                    >
                      <Edit className="h-3.5 w-3.5 mr-1" />
                      Edit
                    </AppButton>
                  </div>
                  <div className="rounded-[8px] border border-[var(--color-gray-200)] bg-white p-4 max-h-48 overflow-y-auto">
                    <p className="text-sm text-[var(--color-gray-700)] whitespace-pre-wrap leading-relaxed">
                      {uploadedPolicy.content.slice(0, 1000)}
                      {uploadedPolicy.content.length > 1000 && "..."}
                    </p>
                  </div>
                </div>
              ) : uploadedPolicy.extraction_status === "failed" ? (
                <div className="flex items-start gap-2 rounded-[8px] border border-red-200 bg-red-50 px-4 py-3">
                  <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-red-800">
                      Content extraction failed
                    </p>
                    <p className="text-xs text-red-600 mt-0.5">
                      The document could not be processed. You can manually add
                      the policy content from the detail page.
                    </p>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--color-gray-200)] flex gap-3 justify-end">
          {activeTab === "write" && !showUploadPreview && (
            <>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={handleSaveDraft}
                loading={isSaving}
                disabled={isSaving}
              >
                Save Draft
              </AppButton>
              <AppButton
                variant="primary"
                size="sm"
                onClick={handlePublish}
                loading={isSaving}
                disabled={isSaving}
              >
                Publish
              </AppButton>
            </>
          )}

          {activeTab === "upload" && !showUploadPreview && (
            <>
              <AppButton variant="outlined" size="sm" onClick={handleClose}>
                Cancel
              </AppButton>
              <AppButton
                variant="primary"
                size="sm"
                onClick={handleUpload}
                loading={isUploading}
                disabled={isUploading || !file}
              >
                <Upload className="h-4 w-4 mr-1" />
                Upload
              </AppButton>
            </>
          )}

          {showUploadPreview && uploadedPolicy && (
            <>
              <AppButton
                variant="danger"
                size="sm"
                onClick={async () => {
                  try {
                    await policiesApi.archive(uploadedPolicy.id);
                    toast.success("Policy deleted");
                    resetState();
                    onClose();
                  } catch {
                    toast.error("Failed to delete policy");
                  }
                }}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1" />
                Delete
              </AppButton>
              <AppButton
                variant="outlined"
                size="sm"
                onClick={() => {
                  handleUploadDone();
                  window.location.href = `/policies/${uploadedPolicy.id}`;
                }}
              >
                <Edit className="h-3.5 w-3.5 mr-1" />
                Edit
              </AppButton>
              <AppButton variant="primary" size="sm" onClick={handleUploadDone}>
                Done
              </AppButton>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
