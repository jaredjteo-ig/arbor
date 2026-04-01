"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import clsx from "clsx";
import {
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  X,
} from "lucide-react";

/* ── Types ─────────────────────────────────────────────────── */

export interface DatePickerProps {
  /** Field label above the input */
  label?: string;
  /** ISO date string (YYYY-MM-DD) */
  value: string;
  /** Callback with ISO date string */
  onChange: (value: string) => void;
  /** Validation error message */
  error?: string;
  /** Helper text below the field */
  helperText?: string;
  /** Placeholder text when empty */
  placeholder?: string;
  /** Minimum selectable date (YYYY-MM-DD) */
  min?: string;
  /** Maximum selectable date (YYYY-MM-DD) */
  max?: string;
  /** Disable interaction */
  disabled?: boolean;
  /** Make the field required */
  required?: boolean;
  /** Additional CSS classes on the wrapper */
  className?: string;
}

/* ── Constants ────────────────────────────────────────────── */

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const DAY_LABELS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

/* ── Helpers ──────────────────────────────────────────────── */

function parseDate(s: string): Date | null {
  if (!s) return null;
  const parts = s.split("-");
  if (parts.length !== 3) return null;
  const d = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2]));
  return isNaN(d.getTime()) ? null : d;
}

function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatDisplay(s: string): string {
  const d = parseDate(s);
  if (!d) return "";
  return d.toLocaleDateString("en-SG", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function startDayOfWeek(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

/* ── Component ────────────────────────────────────────────── */

export function DatePicker({
  label,
  value,
  onChange,
  error,
  helperText,
  placeholder = "Select date",
  min,
  max,
  disabled,
  required,
  className,
}: DatePickerProps) {
  const autoId = useId();
  const fieldId = autoId;
  const errorId = error ? `${fieldId}-error` : undefined;
  const helperId = helperText && !error ? `${fieldId}-helper` : undefined;
  const describedBy = errorId ?? helperId;

  const wrapperRef = useRef<HTMLDivElement>(null);
  const calendarRef = useRef<HTMLDivElement>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Calendar view state
  const parsedValue = parseDate(value);
  const initialYear = parsedValue?.getFullYear() ?? new Date().getFullYear();
  const initialMonth = parsedValue?.getMonth() ?? new Date().getMonth();
  const [viewYear, setViewYear] = useState(initialYear);
  const [viewMonth, setViewMonth] = useState(initialMonth);

  // Sync view when value changes externally
  useEffect(() => {
    const d = parseDate(value);
    if (d) {
      setViewYear(d.getFullYear());
      setViewMonth(d.getMonth());
    }
  }, [value]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node;
      const inWrapper = wrapperRef.current?.contains(target);
      const inCalendar = calendarRef.current?.contains(target);
      if (!inWrapper && !inCalendar) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") setIsOpen(false);
    }
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
    }
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen]);

  const minDate = parseDate(min ?? "");
  const maxDate = parseDate(max ?? "");

  const isDateDisabled = useCallback(
    (d: Date): boolean => {
      if (minDate && d < minDate) return true;
      if (maxDate && d > maxDate) return true;
      return false;
    },
    [minDate, maxDate],
  );

  function prevMonth() {
    if (viewMonth === 0) {
      setViewMonth(11);
      setViewYear(viewYear - 1);
    } else {
      setViewMonth(viewMonth - 1);
    }
  }

  function nextMonth() {
    if (viewMonth === 11) {
      setViewMonth(0);
      setViewYear(viewYear + 1);
    } else {
      setViewMonth(viewMonth + 1);
    }
  }

  function selectDate(day: number) {
    const d = new Date(viewYear, viewMonth, day);
    if (isDateDisabled(d)) return;
    onChange(toIso(d));
    setIsOpen(false);
  }

  function handleClear(e: React.MouseEvent) {
    e.stopPropagation();
    onChange("");
  }

  // Build calendar grid
  const totalDays = daysInMonth(viewYear, viewMonth);
  const firstDow = startDayOfWeek(viewYear, viewMonth);
  const calendarCells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) calendarCells.push(null);
  for (let d = 1; d <= totalDays; d++) calendarCells.push(d);
  // Pad to fill last row
  while (calendarCells.length % 7 !== 0) calendarCells.push(null);

  const today = new Date();
  const todayIso = toIso(today);

  return (
    <div ref={wrapperRef} className={clsx("flex flex-col gap-1.5", className)}>
      {label && (
        <label
          htmlFor={fieldId}
          className="text-sm font-medium text-[var(--color-gray-700)]"
        >
          {label}
          {required && (
            <span className="text-[var(--color-error)] ml-0.5">*</span>
          )}
        </label>
      )}

      {/* Trigger */}
      <button
        type="button"
        id={fieldId}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-invalid={!!error}
        aria-describedby={describedBy}
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          "w-full flex items-center gap-2 rounded-[8px] border px-3 py-2 text-base min-h-[44px] text-left",
          "bg-[var(--color-surface-input)] border-[var(--color-surface-input-border)]",
          "transition-colors",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          error &&
            "border-[var(--color-error)] focus-visible:outline-[var(--color-error)]",
          isOpen && "border-[var(--color-surface-input-focus)]",
        )}
      >
        <CalendarIcon className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
        <span
          className={clsx(
            "flex-1 text-sm",
            value ? "text-[var(--foreground)]" : "text-[var(--color-gray-400)]",
          )}
        >
          {value ? formatDisplay(value) : placeholder}
        </span>
        {value && !disabled && (
          <span
            role="button"
            tabIndex={-1}
            onClick={handleClear}
            className="p-0.5 rounded hover:bg-[var(--color-gray-100)]"
          >
            <X className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
          </span>
        )}
      </button>

      {/* Calendar popover — rendered via portal to escape overflow clipping */}
      {isOpen &&
        createPortal(
          <div
            ref={calendarRef}
            style={{
              position: "fixed",
              zIndex: 9999,
              top:
                (wrapperRef.current?.getBoundingClientRect().bottom ?? 0) + 4,
              left: wrapperRef.current?.getBoundingClientRect().left ?? 0,
            }}
          >
            <div className="w-[280px] bg-white rounded-[12px] border border-[var(--color-gray-200)] shadow-lg p-3">
              {/* Month/year navigation */}
              <div className="flex items-center justify-between mb-2">
                <button
                  type="button"
                  onClick={prevMonth}
                  className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
                  aria-label="Previous month"
                >
                  <ChevronLeft className="h-4 w-4 text-[var(--color-gray-600)]" />
                </button>
                <div className="flex items-center gap-1">
                  <select
                    value={viewMonth}
                    onChange={(e) => setViewMonth(Number(e.target.value))}
                    className="text-sm font-semibold text-[var(--color-gray-900)] bg-transparent border-none cursor-pointer focus:outline-none pr-0"
                  >
                    {MONTH_NAMES.map((name, idx) => (
                      <option key={idx} value={idx}>
                        {name}
                      </option>
                    ))}
                  </select>
                  <select
                    value={viewYear}
                    onChange={(e) => setViewYear(Number(e.target.value))}
                    className="text-sm font-semibold text-[var(--color-gray-900)] bg-transparent border-none cursor-pointer focus:outline-none"
                  >
                    {Array.from(
                      { length: 30 },
                      (_, i) => viewYear - 15 + i,
                    ).map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  onClick={nextMonth}
                  className="p-1.5 rounded-lg hover:bg-[var(--color-gray-100)] transition-colors"
                  aria-label="Next month"
                >
                  <ChevronRight className="h-4 w-4 text-[var(--color-gray-600)]" />
                </button>
              </div>

              {/* Day-of-week headers */}
              <div className="grid grid-cols-7 mb-1">
                {DAY_LABELS.map((d) => (
                  <div
                    key={d}
                    className="text-center text-[10px] font-medium text-[var(--color-gray-500)] uppercase tracking-wider py-1"
                  >
                    {d}
                  </div>
                ))}
              </div>

              {/* Day grid */}
              <div className="grid grid-cols-7">
                {calendarCells.map((day, idx) => {
                  if (day === null) {
                    return <div key={`empty-${idx}`} className="h-8" />;
                  }
                  const cellDate = new Date(viewYear, viewMonth, day);
                  const cellIso = toIso(cellDate);
                  const isSelected = cellIso === value;
                  const isToday = cellIso === todayIso;
                  const isDisabled = isDateDisabled(cellDate);

                  return (
                    <button
                      key={day}
                      type="button"
                      disabled={isDisabled}
                      onClick={() => selectDate(day)}
                      className={clsx(
                        "h-8 w-full rounded-lg text-sm transition-colors",
                        "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--color-primary)]",
                        isSelected
                          ? "bg-[var(--color-primary)] text-white font-semibold"
                          : isToday
                            ? "bg-[var(--color-primary-bg)] text-[var(--color-primary)] font-medium"
                            : "text-[var(--color-gray-700)] hover:bg-[var(--color-gray-100)]",
                        isDisabled &&
                          "opacity-30 cursor-not-allowed hover:bg-transparent",
                      )}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>

              {/* Today shortcut */}
              <div className="mt-2 pt-2 border-t border-[var(--color-gray-100)]">
                <button
                  type="button"
                  onClick={() => {
                    if (!isDateDisabled(today)) {
                      onChange(todayIso);
                      setIsOpen(false);
                    }
                  }}
                  disabled={isDateDisabled(today)}
                  className="w-full text-xs text-center text-[var(--color-primary)] hover:underline disabled:opacity-50 disabled:no-underline py-1"
                >
                  Today
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}

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
}
