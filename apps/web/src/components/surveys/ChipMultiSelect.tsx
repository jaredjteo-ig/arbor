"use client";

/**
 * Multi-select chip group — used for theme tagging in surveys.
 */

interface ChipMultiSelectProps {
  options: { value: string; label: string }[];
  selected: string[];
  onToggle: (value: string) => void;
  label?: string;
  disabled?: boolean;
  questionId?: string;
}

export function ChipMultiSelect({
  options,
  selected,
  onToggle,
  label,
  disabled = false,
  questionId,
}: ChipMultiSelectProps) {
  return (
    <fieldset className="border-0 p-0 m-0">
      {label && (
        <legend className="text-sm font-medium text-[var(--color-gray-900)] mb-3">
          {label}
        </legend>
      )}
      <div className="flex flex-wrap gap-2">
        {options.map(({ value, label: l }) => {
          const isSelected = selected.includes(value);
          return (
            <button
              key={value}
              type="button"
              onClick={() => !disabled && onToggle(value)}
              disabled={disabled}
              aria-pressed={isSelected}
              className={`
                px-4 py-2 rounded-full text-sm font-medium border-2 transition-colors
                min-h-[40px] min-w-[44px]
                ${
                  isSelected
                    ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-white"
                    : "border-[var(--color-gray-200)] bg-white text-[var(--color-gray-700)] hover:bg-[var(--color-gray-50)]"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : ""}
              `}
            >
              {l}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
