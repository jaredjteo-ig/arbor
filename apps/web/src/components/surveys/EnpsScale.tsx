"use client";

/**
 * eNPS 0-10 scale (Net Promoter Score for employees).
 *
 * 0-6 = detractor (red), 7-8 = passive (yellow), 9-10 = promoter (green).
 */

interface EnpsScaleProps {
  value: number | null | undefined;
  onChange: (value: number) => void;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  questionId?: string;
}

export function EnpsScale({
  value,
  onChange,
  label = "How likely are you to recommend this company as a place to work?",
  required = false,
  disabled = false,
  questionId,
}: EnpsScaleProps) {
  const groupId = questionId ? `enps-${questionId}` : undefined;
  return (
    <fieldset
      role="radiogroup"
      aria-label="Net promoter score 0 to 10"
      aria-required={required}
      aria-labelledby={groupId ? `${groupId}-label` : undefined}
      className="border-0 p-0 m-0"
    >
      <legend
        id={groupId ? `${groupId}-label` : undefined}
        className="text-sm font-medium text-[var(--color-gray-900)] mb-3"
      >
        {label}
        {required && <span className="text-[var(--color-error)] ml-1">*</span>}
      </legend>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: 11 }, (_, i) => i).map((v) => {
          const isSelected = value === v;
          const tier = v >= 9 ? "promoter" : v >= 7 ? "passive" : "detractor";
          const baseColor =
            tier === "promoter"
              ? "bg-[var(--color-success)]/10 border-[var(--color-success)] text-[var(--color-success)]"
              : tier === "passive"
                ? "bg-[var(--color-warning)]/10 border-[var(--color-warning)] text-[var(--color-warning)]"
                : "bg-[var(--color-error)]/10 border-[var(--color-error)] text-[var(--color-error)]";
          return (
            <label
              key={v}
              className={`
                flex items-center justify-center
                min-w-[44px] min-h-[44px] rounded-lg cursor-pointer
                border-2 font-semibold transition-all
                ${
                  isSelected
                    ? baseColor + " ring-2 ring-offset-2 ring-current"
                    : "border-[var(--color-gray-200)] bg-white text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
            >
              <input
                type="radio"
                name={questionId || "enps"}
                value={v}
                checked={isSelected}
                disabled={disabled}
                onChange={() => onChange(v)}
                className="sr-only"
              />
              {v}
            </label>
          );
        })}
      </div>
      <div className="flex justify-between mt-2 text-xs text-[var(--color-gray-500)]">
        <span>Not at all likely</span>
        <span>Extremely likely</span>
      </div>
    </fieldset>
  );
}
