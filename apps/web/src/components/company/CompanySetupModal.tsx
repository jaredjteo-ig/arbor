"use client";

import { useState } from "react";
import { Building2, ArrowRight, Sparkles, CheckCircle2, X } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { clientsApi } from "@/services/api";

const SECTORS = [
  { value: "technology", label: "Technology & IT" },
  { value: "fnb", label: "Food & Beverage" },
  { value: "retail", label: "Retail & E-commerce" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "construction", label: "Construction" },
  { value: "services", label: "Professional Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "education", label: "Education" },
  { value: "logistics", label: "Logistics & Transport" },
  { value: "other", label: "Other" },
];

const HEADCOUNT_RANGES = [
  { value: "1-5", label: "1 - 5 employees" },
  { value: "6-25", label: "6 - 25 employees" },
  { value: "26-50", label: "26 - 50 employees" },
  { value: "51-100", label: "51 - 100 employees" },
  { value: "101-200", label: "101 - 200 employees" },
];

interface CompanySetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onComplete?: () => void;
}

export function CompanySetupModal({
  isOpen,
  onClose,
  onComplete,
}: CompanySetupModalProps) {
  const { refreshUser } = useAuth();
  const [step, setStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: "",
    uen: "",
    sector: "",
    headcount: "",
  });

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      await clientsApi.create({
        name: form.name,
        uen: form.uen || undefined,
        sector: form.sector,
        estimated_headcount: parseInt(form.headcount.split("-")[0]) || 5,
      } as any);

      await refreshUser?.();
      setStep(2);
      setTimeout(() => {
        onComplete?.();
        onClose();
        window.location.reload();
      }, 1500);
    } catch (err: any) {
      const message =
        err?.detail ||
        err?.message ||
        "Something went wrong. Please try again.";
      alert(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-in">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-full hover:bg-gray-100 transition-colors z-10"
          aria-label="Close"
        >
          <X className="w-5 h-5 text-gray-400" />
        </button>

        {step === 0 && (
          /* Welcome step */
          <div className="p-8 text-center">
            <div className="mx-auto w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mb-6">
              <Building2 className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              Welcome to Central
            </h2>
            <p className="text-gray-600 mb-2">
              Set up your company to unlock the full HR management suite —
              payroll, leave, claims, attendance, shifts, and more.
            </p>
            <p className="text-sm text-gray-500 mb-8">
              It takes less than a minute. You can always update these details
              later.
            </p>
            <button
              onClick={() => setStep(1)}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all shadow-lg shadow-blue-500/25"
            >
              Get Started
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 1 && (
          /* Form step */
          <div className="p-8">
            <div className="flex items-center gap-3 mb-6">
              <Sparkles className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900">
                Company Details
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Company Name *
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Acme Pte Ltd"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  UEN *
                </label>
                <input
                  type="text"
                  value={form.uen}
                  onChange={(e) => setForm({ ...form, uen: e.target.value })}
                  placeholder="e.g. 201234567K"
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Your Unique Entity Number from ACRA
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Industry Sector *
                </label>
                <select
                  value={form.sector}
                  onChange={(e) => setForm({ ...form, sector: e.target.value })}
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                >
                  <option value="">Select your industry</option>
                  {SECTORS.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Number of Employees *
                </label>
                <select
                  value={form.headcount}
                  onChange={(e) =>
                    setForm({ ...form, headcount: e.target.value })
                  }
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                >
                  <option value="">Select range</option>
                  {HEADCOUNT_RANGES.map((h) => (
                    <option key={h.value} value={h.value}>
                      {h.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-8 flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors font-medium"
              >
                I'll do this later
              </button>
              <button
                onClick={handleSubmit}
                disabled={
                  !form.name ||
                  !form.uen ||
                  !form.sector ||
                  !form.headcount ||
                  isSubmitting
                }
                className="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all font-medium disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/25"
              >
                {isSubmitting ? "Setting up..." : "Create Company"}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          /* Success step */
          <div className="p-8 text-center">
            <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-6">
              <CheckCircle2 className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              You're all set!
            </h2>
            <p className="text-gray-600">
              Your company is ready. The full HR management suite is now
              unlocked.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
