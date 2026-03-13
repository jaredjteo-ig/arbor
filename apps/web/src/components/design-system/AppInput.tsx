"use client";

import {
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  forwardRef,
  useId,
} from "react";
import clsx from "clsx";

/* ── Shared props ─────────────────────────────────────────── */

interface BaseFieldProps {
  label?: string;
  error?: string;
  helperText?: string;
}

/* ── Text / Number input ──────────────────────────────────── */

interface TextInputProps
  extends BaseFieldProps, Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  variant?: "text" | "number" | "email" | "password";
}

/* ── Select (dropdown) ────────────────────────────────────── */

interface SelectInputProps
  extends BaseFieldProps, SelectHTMLAttributes<HTMLSelectElement> {
  variant: "select";
  options: { value: string; label: string }[];
  placeholder?: string;
}

/* ── Textarea ─────────────────────────────────────────────── */

interface TextareaInputProps
  extends BaseFieldProps, TextareaHTMLAttributes<HTMLTextAreaElement> {
  variant: "textarea";
}

export type AppInputProps =
  | TextInputProps
  | SelectInputProps
  | TextareaInputProps;

/* ── Styles ───────────────────────────────────────────────── */

const baseFieldClasses = clsx(
  "w-full rounded-[8px] border px-3 py-2 text-base min-h-[44px]",
  "bg-[var(--color-surface-input)] text-[var(--foreground)]",
  "border-[var(--color-surface-input-border)]",
  "placeholder:text-[var(--color-gray-400)]",
  "transition-colors",
  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
  "focus:border-[var(--color-surface-input-focus)]",
  "disabled:opacity-50 disabled:cursor-not-allowed",
);

const errorFieldClasses =
  "border-[var(--color-error)] focus:border-[var(--color-error)] focus-visible:outline-[var(--color-error)]";

/* ── Component ────────────────────────────────────────────── */

export const AppInput = forwardRef<
  HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement,
  AppInputProps
>((props, ref) => {
  const autoId = useId();
  const {
    label,
    error,
    helperText,
    className,
    variant = "text",
    ...rest
  } = props;

  const fieldId = props.id ?? autoId;
  const errorId = error ? `${fieldId}-error` : undefined;
  const helperId = helperText && !error ? `${fieldId}-helper` : undefined;
  const describedBy = errorId ?? helperId;

  const fieldClasses = clsx(
    baseFieldClasses,
    error && errorFieldClasses,
    className,
  );

  /* ── Render the correct element ──────────────────────────── */

  let field: React.ReactNode;

  if (variant === "select") {
    const { options, placeholder, ...selectRest } = rest as Omit<
      SelectInputProps,
      "label" | "error" | "helperText" | "variant" | "className"
    >;
    field = (
      <select
        ref={ref as React.Ref<HTMLSelectElement>}
        id={fieldId}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        className={fieldClasses}
        {...selectRest}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  } else if (variant === "textarea") {
    const textareaRest = rest as Omit<
      TextareaInputProps,
      "label" | "error" | "helperText" | "variant" | "className"
    >;
    field = (
      <textarea
        ref={ref as React.Ref<HTMLTextAreaElement>}
        id={fieldId}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        className={clsx(fieldClasses, "min-h-[100px] resize-y")}
        {...textareaRest}
      />
    );
  } else {
    const inputRest = rest as Omit<
      TextInputProps,
      "label" | "error" | "helperText" | "variant" | "className"
    >;
    field = (
      <input
        ref={ref as React.Ref<HTMLInputElement>}
        id={fieldId}
        type={
          variant === "number"
            ? "number"
            : variant === "email"
              ? "email"
              : variant === "password"
                ? "password"
                : "text"
        }
        aria-invalid={!!error}
        aria-describedby={describedBy}
        className={fieldClasses}
        {...inputRest}
      />
    );
  }

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={fieldId}
          className="text-sm font-medium text-[var(--color-gray-700)]"
        >
          {label}
        </label>
      )}

      {field}

      {error && (
        <p
          id={errorId}
          role="alert"
          className="text-sm text-[var(--color-error)]"
        >
          {error}
        </p>
      )}

      {helperText && !error && (
        <p id={helperId} className="text-sm text-[var(--color-gray-500)]">
          {helperText}
        </p>
      )}
    </div>
  );
});

AppInput.displayName = "AppInput";
