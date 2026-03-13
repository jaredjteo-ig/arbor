"use client";

import { useState } from "react";
import { Mic, Send, ArrowRight } from "lucide-react";
import { AppButton } from "@/components/design-system/AppButton";
import { AppCard } from "@/components/design-system/AppCard";
import type { CompanyProfileData } from "./CompanyProfileStep";

interface FirstQuestionStepProps {
  profileData: CompanyProfileData;
  onSubmitQuestion: (question: string) => void;
  onSkip: () => void;
  onBack: () => void;
}

const GENERIC_SUGGESTIONS = [
  "What are the minimum leave entitlements for my employees?",
  "How do I calculate CPF contributions?",
  "What notice period do I need to give for termination?",
  "What are the key employment terms I must provide?",
];

const SECTOR_SUGGESTIONS: Record<string, string[]> = {
  services: [
    "What is the foreign worker quota limit for the services sector?",
    "How much levy do I pay for each S Pass and WP holder?",
    "What Part IV protections apply to my retail/F&B employees?",
  ],
  manufacturing: [
    "What is the DRC limit for manufacturing?",
    "How do I manage overtime for production workers?",
    "What workplace safety requirements apply to my factory?",
  ],
  construction: [
    "What is the DRC limit for construction?",
    "What bizSAFE level do I need?",
    "What are the housing requirements for foreign workers?",
  ],
  tech: [
    "Do I need to advertise on MyCareersFuture before hiring an EP holder?",
    "What are the COMPASS scoring criteria for EP applications?",
    "How do stock options affect CPF contributions?",
  ],
  finance: [
    "What are the higher salary thresholds for financial services EP?",
    "How do I handle bonuses for CPF calculation?",
    "What TAFEP guidelines apply to our recruitment process?",
  ],
};

export function FirstQuestionStep({
  profileData,
  onSubmitQuestion,
  onSkip,
  onBack,
}: FirstQuestionStepProps) {
  const [question, setQuestion] = useState("");

  const sectorSpecific = SECTOR_SUGGESTIONS[profileData.sector] ?? [];
  const suggestions = [...sectorSpecific, ...GENERIC_SUGGESTIONS].slice(0, 5);

  function handleSubmit() {
    if (question.trim()) {
      onSubmitQuestion(question.trim());
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="max-w-lg mx-auto">
      <h2 className="text-xl font-bold text-[var(--color-gray-900)] mb-1">
        Ask Your First Question
      </h2>
      <p className="text-sm text-[var(--color-gray-500)] mb-6">
        Type any HR question in plain English (Singlish works too!), or pick one
        of the suggestions below.
      </p>

      {/* Question input */}
      <div className="relative mb-6">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. My staff resign already, need pay notice period or not?"
          rows={3}
          className={[
            "w-full rounded-xl border px-4 py-3 pr-24 text-base resize-none",
            "bg-[var(--color-surface-input)] text-[var(--foreground)]",
            "border-[var(--color-surface-input-border)]",
            "placeholder:text-[var(--color-gray-400)]",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]",
            "focus:border-[var(--color-surface-input-focus)]",
          ].join(" ")}
          autoComplete="off"
          spellCheck={false}
        />
        <div className="absolute bottom-3 right-3 flex items-center gap-2">
          <button
            type="button"
            className="p-2 rounded-lg text-[var(--color-gray-400)] hover:text-[var(--color-primary)] hover:bg-[var(--color-gray-100)] transition-colors"
            title="Voice input"
            aria-label="Voice input"
          >
            <Mic className="w-5 h-5" />
          </button>
          <AppButton
            size="sm"
            onClick={handleSubmit}
            disabled={!question.trim()}
            className="rounded-lg"
          >
            <Send className="w-4 h-4" />
          </AppButton>
        </div>
      </div>

      {/* Suggested questions */}
      <div>
        <p className="text-xs font-medium text-[var(--color-gray-500)] uppercase tracking-wide mb-3">
          Suggested questions
          {sectorSpecific.length > 0 && ` for ${profileData.sector} sector`}
        </p>
        <div className="space-y-2">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => onSubmitQuestion(suggestion)}
              className={[
                "w-full text-left px-4 py-3 rounded-lg border text-sm",
                "border-[var(--color-gray-200)] bg-[var(--color-surface-card)]",
                "hover:border-[var(--color-primary)] hover:bg-[var(--color-primary-bg)]",
                "transition-colors group flex items-center justify-between",
              ].join(" ")}
            >
              <span className="text-[var(--color-gray-700)] group-hover:text-[var(--color-primary)]">
                {suggestion}
              </span>
              <ArrowRight className="w-4 h-4 text-[var(--color-gray-300)] group-hover:text-[var(--color-primary)] shrink-0 ml-2" />
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-3 mt-8">
        <AppButton variant="outlined" onClick={onBack}>
          Back
        </AppButton>
        <AppButton variant="text" onClick={onSkip} className="flex-1">
          Skip — Go to Dashboard
        </AppButton>
      </div>
    </div>
  );
}
