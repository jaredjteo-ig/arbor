"use client";

import { AppButton, AppCard, AppInput } from "@/components/design-system";
import { X } from "lucide-react";

/**
 * Inline form for creating a new regulatory update in draft status.
 * Renders inside the Regulatory Updates tab when "Create Update" is clicked.
 */
export function CreateUpdateForm({ onClose }: { onClose: () => void }) {
  return (
    <AppCard
      variant="elevated"
      header={
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
            Create Regulatory Update
          </h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close form"
            className="p-1 rounded hover:bg-[var(--color-gray-100)] transition-colors"
          >
            <X className="h-4 w-4 text-[var(--color-gray-500)]" />
          </button>
        </div>
      }
    >
      <form
        className="grid grid-cols-1 md:grid-cols-2 gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          onClose();
        }}
      >
        <AppInput label="Title" placeholder="Regulatory update title" />
        <AppInput label="Source" placeholder="e.g., Ministry of Manpower" />
        <AppInput
          label="Urgency"
          variant="select"
          options={[
            { value: "low", label: "Low" },
            { value: "medium", label: "Medium" },
            { value: "high", label: "High" },
            { value: "critical", label: "Critical" },
          ]}
        />
        <AppInput label="Effective Date" variant="date" />
        <div className="md:col-span-2">
          <AppInput
            label="Description"
            variant="textarea"
            placeholder="Describe the regulatory change and its impact..."
          />
        </div>
        <div className="md:col-span-2">
          <AppInput
            label="Affected Domains"
            placeholder="e.g., Employment Act, CPF"
            helperText="Comma-separated list of affected regulatory domains"
          />
        </div>
        <div className="md:col-span-2 flex justify-end gap-3">
          <AppButton variant="text" type="button" onClick={onClose}>
            Cancel
          </AppButton>
          <AppButton variant="primary" type="submit">
            Create Draft
          </AppButton>
        </div>
      </form>
    </AppCard>
  );
}
