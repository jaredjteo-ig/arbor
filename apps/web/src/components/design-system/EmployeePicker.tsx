"use client";

import { useState, useEffect, useRef } from "react";
import { employeesApi } from "@/services/api/employees";
import { Search, X, User } from "lucide-react";

interface Employee {
  id: number;
  name: string;
  email: string;
  department?: string;
  designation?: string;
}

interface EmployeePickerProps {
  label?: string;
  value: number | null;
  onChange: (employeeId: number | null, employee?: Employee) => void;
  placeholder?: string;
  disabled?: boolean;
  excludeIds?: number[];
}

export function EmployeePicker({
  label,
  value,
  onChange,
  placeholder = "Search employees...",
  disabled,
  excludeIds = [],
}: EmployeePickerProps) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [search, setSearch] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selected, setSelected] = useState<Employee | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Fetch employees once
  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    employeesApi
      .list()
      .then((data) => {
        if (!cancelled) {
          setEmployees(data.employees || []);
          // If we have a value, find the matching employee
          if (value) {
            const match = (data.employees || []).find(
              (e: Employee) => e.id === value,
            );
            if (match) setSelected(match);
          }
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [value]);

  // Click outside to close
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filtered = employees.filter((emp) => {
    if (excludeIds.includes(emp.id)) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      emp.name.toLowerCase().includes(q) ||
      emp.email.toLowerCase().includes(q) ||
      (emp.department || "").toLowerCase().includes(q)
    );
  });

  function handleSelect(emp: Employee) {
    setSelected(emp);
    onChange(emp.id, emp);
    setSearch("");
    setIsOpen(false);
  }

  function handleClear() {
    setSelected(null);
    onChange(null);
    setSearch("");
  }

  return (
    <div ref={wrapperRef} className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium text-[var(--color-gray-700)]">
          {label}
        </label>
      )}
      <div className="relative">
        {selected ? (
          <div className="flex items-center gap-2 rounded-[8px] border px-3 py-2 min-h-[44px] bg-[var(--color-surface-input)] border-[var(--color-surface-input-border)]">
            <User className="h-4 w-4 text-[var(--color-gray-400)]" />
            <div className="flex-1 min-w-0">
              <span className="text-sm text-[var(--foreground)]">
                {selected.name}
              </span>
              {selected.department && (
                <span className="text-xs text-[var(--color-gray-500)] ml-2">
                  {selected.department}
                </span>
              )}
            </div>
            {!disabled && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded hover:bg-[var(--color-gray-100)]"
              >
                <X className="h-3.5 w-3.5 text-[var(--color-gray-400)]" />
              </button>
            )}
          </div>
        ) : (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-gray-400)]" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setIsOpen(true);
              }}
              onFocus={() => setIsOpen(true)}
              placeholder={isLoading ? "Loading employees..." : placeholder}
              disabled={disabled || isLoading}
              className="w-full rounded-[8px] border px-3 py-2 pl-9 text-sm min-h-[44px] bg-[var(--color-surface-input)] text-[var(--foreground)] border-[var(--color-surface-input-border)] focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)] disabled:opacity-50"
            />
          </div>
        )}

        {isOpen && !selected && (
          <div className="absolute z-50 mt-1 w-full bg-white rounded-[8px] border border-[var(--color-gray-200)] shadow-lg max-h-60 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-3 py-2 text-sm text-[var(--color-gray-500)]">
                No employees found
              </p>
            ) : (
              filtered.slice(0, 20).map((emp) => (
                <button
                  key={emp.id}
                  type="button"
                  onClick={() => handleSelect(emp)}
                  className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[var(--color-gray-50)] text-left"
                >
                  <User className="h-4 w-4 text-[var(--color-gray-400)] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-[var(--foreground)] truncate">
                      {emp.name}
                    </p>
                    <p className="text-xs text-[var(--color-gray-500)] truncate">
                      {emp.email}
                      {emp.department ? ` · ${emp.department}` : ""}
                    </p>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}
