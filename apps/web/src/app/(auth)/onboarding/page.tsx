"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { StepIndicator } from "@/components/design-system/StepIndicator";
import {
  WelcomeStep,
  CompanyProfileStep,
  ComplianceSnapshotStep,
  FirstQuestionStep,
} from "@/components/onboarding";
import type { CompanyProfileData } from "@/components/onboarding";
import { useAuth } from "@/contexts/AuthContext";
import { clientsApi } from "@/services/api/clients";

const STEPS = ["Welcome", "Company", "Snapshot", "Ask"];

export default function OnboardingPage() {
  const router = useRouter();
  const { user, refreshUser } = useAuth();
  const isLoggedIn = !!user;

  const [currentStep, setCurrentStep] = useState(0);
  const [profileData, setProfileData] = useState<CompanyProfileData | null>(
    null,
  );

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
        await clientsApi.create({
          name: data.companyName,
          sector: data.sector,
          estimated_headcount: data.totalEmployees || 5,
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
