"use client";

/**
 * 5-point Likert scale (Strongly disagree → Strongly agree).
 *
 * Built for engagement-survey M0 T02 (deferred to M4). Used by both
 * exit-survey public form and engagement in-app form. Round-2 Z18:
 * radiogroup ARIA + 44pt tap targets for accessibility.
 */

const LABELS = [
  { value: 1, label: "Strongly disagree" },
  { value: 2, label: "Disagree" },
  { value: 3, label: "Neutral" },
  { value: 4, label: "Agree" },
  { value: 5, label: "Strongly agree" },
];

interface Likert5Props {
  value: number | null | undefined;
  onChange: (value: number) => void;
  label: string;
  required?: boolean;
  disabled?: boolean;
  questionId?: string;
}

export function Likert5({
  value,
  onChange,
  label,
  required = false,
  disabled = false,
  questionId,
}: Likert5Props) {
  const groupId = questionId ? `likert-${questionId}` : undefined;
  return (
    <fieldset
      role="radiogroup"
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
      <div className="grid grid-cols-5 gap-2">
        {LABELS.map(({ value: v, label: l }) => {
          const isSelected = value === v;
          return (
            <label
              key={v}
              className={`
                flex flex-col items-center justify-center
                min-h-[56px] px-2 py-3 rounded-lg cursor-pointer
                border transition-colors
                ${
                  isSelected
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-primary)]"
                    : "border-[var(--color-gray-200)] bg-white hover:bg-[var(--color-gray-50)] text-[var(--color-gray-700)]"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
            >
              <input
                type="radio"
                name={questionId || "likert"}
                value={v}
                checked={isSelected}
                disabled={disabled}
                onChange={() => onChange(v)}
                className="sr-only"
              />
              <span className="text-lg font-semibold">{v}</span>
              <span className="text-[10px] mt-1 text-center leading-tight">
                {l}
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
