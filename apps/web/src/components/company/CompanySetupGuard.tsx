"use client";

import type { ReactNode } from "react";
import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { CompanySetupModal } from "@/components/company/CompanySetupModal";

interface CompanySetupGuardProps {
  children: ReactNode;
  /** Module-specific feature info shown when no company */
  module: {
    id: string;
    title: string;
    tagline: string;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bgColor: string;
    features: { title: string; description: string }[];
    usps: string[];
    screenshots?: string[];
  };
}

/**
 * Wraps management pages that require a company.
 * Shows a MODULE-SPECIFIC feature page (not generic) when no company exists.
 */
export function CompanySetupGuard({
  children,
  module,
}: CompanySetupGuardProps) {
  const { user, isLoading } = useAuth();
  const [showSetup, setShowSetup] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user?.company_id) {
    const Icon = module.icon;
    return (
      <div className="p-6 max-w-5xl mx-auto">
        {/* Module header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div
              className={`w-12 h-12 rounded-xl ${module.bgColor} flex items-center justify-center`}
            >
              <Icon className={`w-6 h-6 ${module.color}`} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                {module.title}
              </h1>
              <p className="text-sm text-gray-500">{module.tagline}</p>
            </div>
          </div>
          <p className="text-gray-600 leading-relaxed max-w-2xl">
            {module.description}
          </p>
        </div>

        {/* USPs */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
          {module.usps.map((usp) => (
            <div
              key={usp}
              className="flex items-start gap-2 p-3 rounded-lg bg-white border border-gray-100"
            >
              <svg
                className={`w-5 h-5 mt-0.5 shrink-0 ${module.color}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-sm text-gray-700">{usp}</span>
            </div>
          ))}
        </div>

        {/* Feature details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {module.features.map((feat) => (
            <div
              key={feat.title}
              className="p-4 rounded-xl bg-white border border-gray-200 hover:border-gray-300 transition-colors"
            >
              <h3 className="font-semibold text-gray-900 text-sm mb-1">
                {feat.title}
              </h3>
              <p className="text-xs text-gray-500 leading-relaxed">
                {feat.description}
              </p>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div
          className={`rounded-xl p-6 ${module.bgColor} border border-gray-200`}
        >
          <h3 className="font-semibold text-gray-900 mb-2">
            Start using {module.title}
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            Set up your company to unlock {module.title.toLowerCase()} and all
            other HR management features. It takes less than a minute.
          </p>
          <button
            onClick={() => setShowSetup(true)}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 transition-colors text-sm"
          >
            Set Up Company to Get Started
          </button>
        </div>

        <CompanySetupModal
          isOpen={showSetup}
          onClose={() => setShowSetup(false)}
        />
      </div>
    );
  }

  return <>{children}</>;
}
