"use client";

import { Building2, ShieldCheck, Calculator, FileText } from "lucide-react";
import { AppButton } from "@/components/design-system/AppButton";
import { AppCard } from "@/components/design-system/AppCard";

interface WelcomeStepProps {
  onNext: () => void;
  isLoggedIn: boolean;
}

const features = [
  {
    icon: ShieldCheck,
    title: "Compliance Guidance",
    description:
      "Get instant answers to HR questions with citations from Singapore employment law.",
  },
  {
    icon: Calculator,
    title: "Accurate Calculators",
    description:
      "Calculate CPF contributions, leave entitlements, and foreign worker quotas instantly.",
  },
  {
    icon: FileText,
    title: "Ready-Made Templates",
    description:
      "Download employment contracts, leave policies, and other HR documents.",
  },
  {
    icon: Building2,
    title: "Company-Specific Advice",
    description:
      "Set up your company profile and get tailored compliance recommendations.",
  },
];

export function WelcomeStep({ onNext, isLoggedIn }: WelcomeStepProps) {
  return (
    <div className="flex flex-col items-center text-center max-w-xl mx-auto">
      <div className="mb-6">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[var(--color-primary)] text-white mb-4">
          <Building2 className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)] mb-2">
          Welcome to Central
        </h1>
        <p className="text-[var(--color-gray-600)] text-base">
          Your AI-powered HR advisory platform.
          {!isLoggedIn &&
            " Log in to get started, or continue to set up your company profile."}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full mb-8">
        {features.map((feature) => (
          <AppCard key={feature.title} variant="flat" className="text-left">
            <div className="flex items-start gap-3">
              <div className="shrink-0 w-10 h-10 rounded-lg bg-[var(--color-primary-bg)] flex items-center justify-center">
                <feature.icon className="w-5 h-5 text-[var(--color-primary)]" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[var(--color-gray-900)]">
                  {feature.title}
                </h3>
                <p className="text-xs text-[var(--color-gray-500)] mt-0.5">
                  {feature.description}
                </p>
              </div>
            </div>
          </AppCard>
        ))}
      </div>

      <AppButton size="lg" onClick={onNext} className="w-full sm:w-auto px-12">
        {isLoggedIn ? "Set Up Company Profile" : "Get Started"}
      </AppButton>
    </div>
  );
}
