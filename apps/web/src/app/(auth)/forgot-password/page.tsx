"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { ArrowLeft, CheckCircle } from "lucide-react";
import { AppButton, AppInput } from "@/components/design-system";
import { authApi } from "@/services/api/auth";

/* ── Validation ──────────────────────────────────────────── */

const forgotPasswordSchema = z.object({
  email: z.string().min(1, "auth.invalid_email").email("auth.invalid_email"),
});

type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

/* ── Page ─────────────────────────────────────────────────── */

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit(data: ForgotPasswordFormValues) {
    setServerError(null);
    try {
      await authApi.requestPasswordReset(data.email);
      setSubmitted(true);
    } catch {
      /* Always show success to prevent email enumeration */
      setSubmitted(true);
    }
  }

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      {/* Logo */}
      <div className="flex justify-center mb-6">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center rounded-lg bg-[var(--color-primary)] text-white font-bold w-10 h-10 text-lg">
            A
          </div>
          <span className="text-xl font-bold text-[var(--color-primary)]">
            Arbor
          </span>
        </div>
      </div>

      {submitted ? (
        /* ── Success state ─────────────────────────────────── */
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <div className="flex items-center justify-center w-12 h-12 rounded-full bg-[var(--color-success-bg)]">
              <CheckCircle
                className="h-6 w-6 text-[var(--color-success)]"
                aria-hidden="true"
              />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-gray-900)] mb-2">
            {t("auth.reset_link_sent")}
          </h1>
          <p className="text-sm text-[var(--color-gray-500)] mb-6">
            {t("auth.reset_link_sent_description")}
          </p>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            {t("auth.back_to_login")}
          </Link>
        </div>
      ) : (
        /* ── Form state ────────────────────────────────────── */
        <>
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
              {t("auth.forgot_password_heading")}
            </h1>
            <p className="mt-1 text-sm text-[var(--color-gray-500)]">
              {t("auth.forgot_password_subheading")}
            </p>
          </div>

          {serverError && (
            <div
              role="alert"
              className="mb-4 rounded-[8px] border-l-4 border-[var(--color-error)] bg-[var(--color-error-bg)] px-4 py-3"
            >
              <p className="text-sm text-[var(--color-error)]">{serverError}</p>
            </div>
          )}

          <form
            onSubmit={handleSubmit(onSubmit)}
            className="space-y-4"
            noValidate
          >
            <AppInput
              variant="email"
              label={t("auth.email")}
              placeholder="you@company.com"
              autoComplete="email"
              error={
                errors.email ? t(errors.email.message as string) : undefined
              }
              {...register("email")}
            />

            <AppButton
              type="submit"
              size="lg"
              loading={isSubmitting}
              className="w-full"
            >
              {t("auth.send_reset_link")}
            </AppButton>
          </form>

          <p className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center gap-2 text-sm font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              {t("auth.back_to_login")}
            </Link>
          </p>
        </>
      )}
    </div>
  );
}
