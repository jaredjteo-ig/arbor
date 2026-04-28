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
import { useAuth } from "@/contexts/AuthContext";
import { companyApi } from "@/services/api/company";

const STEPS = ["Welcome", "Company", "Snapshot", "Ask"];

/** Settings key for the T223 chat-onboarding (beta) toggle. Default: off. */
const CHAT_ONBOARDING_FLAG = "arbor.chat-onboarding";

export default function OnboardingPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const isLoggedIn = !!user;

  const [currentStep, setCurrentStep] = useState(0);
  const [profileData, setProfileData] = useState<CompanyProfileData | null>(
    null,
  );

  /* T223: read the chat-onboarding (beta) preference from localStorage.
     We start with `null` so the form path stays the default during SSR. */
  const [useChat, setUseChat] = useState<boolean | null>(null);
  useEffect(() => {
    try {
      const flag = window.localStorage.getItem(CHAT_ONBOARDING_FLAG);
      setUseChat(flag === "true");
    } catch {
      setUseChat(false);
    }
  }, []);

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
