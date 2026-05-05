"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { StepIndicator } from "@/components/design-system/StepIndicator";
import {
  WelcomeStep,
  CompanyProfileStep,
  ComplianceSnapshotStep,
  FirstQuestionStep,
  ChatOnboarding,
} from "@/components/onboarding";
import type { CompanyProfileData } from "@/components/onboarding";
import { useAuth, useFeatureFlag } from "@/contexts/AuthContext";
import { companyApi } from "@/services/api/company";

const STEPS = ["Welcome", "Company", "Snapshot", "Ask"];

export default function OnboardingPage() {
  const router = useRouter();
  const { user, refreshUser, featureFlagsLoaded } = useAuth();
  const isLoggedIn = !!user;
  const chatFlagEnabled = useFeatureFlag("chat-onboarding");

  const [currentStep, setCurrentStep] = useState(0);
  const [profileData, setProfileData] = useState<CompanyProfileData | null>(
    null,
  );

  // Already-onboarded users (have a company_id) hitting this URL belong
  // on the admin Employees ▸ Onboarding tab, not the new-user signup wizard.
  // Exception: existing users who opted into the chat-onboarding beta flag
  // are intentionally routed through ChatOnboarding below.
  useEffect(() => {
    if (user?.company_id != null && featureFlagsLoaded && !chatFlagEnabled) {
      router.replace("/employees?tab=onboarding");
    }
  }, [user?.company_id, featureFlagsLoaded, chatFlagEnabled, router]);

  /* Round-13 S1-T4 (CRIT-D4): chat onboarding now defaults ON for new
     signups (anyone whose JWT has no `company_id` yet). Existing companies
     keep the form unless their owner explicitly enables chat onboarding
     in Settings. The toggle truth lives in the company's `feature_flags`
     map on the backend — never in localStorage.

     Resolution rules:
       - No company yet      -> chat (fresh signup default)
       - Has company + flag  -> chat
       - Has company, no flag-> form (existing behaviour preserved)
       - Flags still loading -> form (safe fallback; SSR-friendly)
  */
  let useChat: boolean | null = null;
  if (!user) {
    // Not authenticated yet — wait for auth to resolve before deciding.
    useChat = null;
  } else if (user.company_id == null) {
    // Fresh signup — default to chat regardless of any flag.
    useChat = true;
  } else if (featureFlagsLoaded) {
    useChat = chatFlagEnabled;
  } else {
    useChat = null;
  }

  const goNext = useCallback(() => {
    setCurrentStep((s) => Math.min(s + 1, STEPS.length - 1));
  }, []);

  const goBack = useCallback(() => {
    setCurrentStep((s) => Math.max(s - 1, 0));
  }, []);

  const handleProfileComplete = useCallback(
    async (data: CompanyProfileData) => {
      setProfileData(data);
      try {
        await companyApi.create({
          name: data.companyName,
          sector: data.sector,
          estimated_headcount: data.totalHeadcount || 5,
        } as any);
        await refreshUser?.();
      } catch (err: any) {
        // Company may already exist — continue with onboarding
        console.warn("Company creation during onboarding:", err?.message);
      }
      goNext();
    },
    [goNext, refreshUser],
  );

  const handleQuestion = useCallback(
    (question: string) => {
      // Navigate to advisory with the question pre-filled
      const params = new URLSearchParams({ q: question });
      router.push(`/advisory?${params.toString()}`);
    },
    [router],
  );

  const handleSkip = useCallback(() => {
    router.push("/my-dashboard");
  }, [router]);

  /* T223: when chat onboarding (beta) is enabled, swap the entire
     form-based flow for the conversational ChatOnboarding surface.
     This keeps CompanySetupModal untouched and leaves the form path
     intact for users who haven't opted in. */
  if (useChat === true) {
    return (
      <div className="min-h-screen bg-[var(--color-surface-page)] flex flex-col">
        <header className="border-b border-[var(--color-gray-200)] bg-white">
          <div className="max-w-2xl mx-auto px-4 py-4 flex items-center justify-between">
            <h1 className="text-base font-semibold text-[var(--color-gray-900)]">
              Welcome to Central
            </h1>
            <span className="text-xs text-[var(--color-gray-500)]">
              Beta — chat onboarding
            </span>
          </div>
        </header>
        <main className="flex-1 flex items-start justify-center px-4 py-8 sm:py-12">
          <ChatOnboarding
            onComplete={() => {
              router.push("/my-dashboard");
            }}
            onSkip={handleSkip}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-surface-page)] flex flex-col">
      {/* Header with step indicator */}
      <header className="border-b border-[var(--color-gray-200)] bg-white">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <StepIndicator steps={STEPS} currentStep={currentStep} />
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 flex items-start justify-center px-4 py-8 sm:py-12">
        <div className="w-full max-w-2xl">
          {currentStep === 0 && (
            <WelcomeStep onNext={goNext} isLoggedIn={isLoggedIn} />
          )}

          {currentStep === 1 && (
            <CompanyProfileStep
              onNext={handleProfileComplete}
              onBack={goBack}
              initialData={profileData ?? undefined}
            />
          )}

          {currentStep === 2 && profileData && (
            <ComplianceSnapshotStep
              profileData={profileData}
              onNext={goNext}
              onBack={goBack}
            />
          )}

          {currentStep === 3 && profileData && (
            <FirstQuestionStep
              profileData={profileData}
              onSubmitQuestion={handleQuestion}
              onSkip={handleSkip}
              onBack={goBack}
            />
          )}
        </div>
      </main>
    </div>
  );
}
