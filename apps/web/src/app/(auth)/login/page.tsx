"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { AppButton, AppInput } from "@/components/design-system";
import { useAuth } from "@/contexts/AuthContext";
import { authApi, AuthError } from "@/services/api/auth";

/* ── Validation ──────────────────────────────────────────── */

const loginSchema = z.object({
  email: z.string().min(1, "auth.invalid_email").email("auth.invalid_email"),
  password: z.string().min(1, "auth.password_requirements"),
});

type LoginFormValues = z.infer<typeof loginSchema>;

/* ── Page ─────────────────────────────────────────────────── */

export default function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data: LoginFormValues) {
    setServerError(null);
    try {
      await login(data);
    } catch (error) {
      if (error instanceof AuthError && error.status === 401) {
        setServerError(t("auth.invalid_credentials"));
      } else {
        setServerError(t("auth.generic_error"));
      }
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
            AITE
          </span>
        </div>
      </div>

      {/* Heading */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          {t("auth.login_heading")}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-gray-500)]">
          {t("auth.login_subheading")}
        </p>
      </div>

      {/* Server error */}
      {serverError && (
        <div
          role="alert"
          className="mb-4 rounded-[8px] border-l-4 border-[var(--color-error)] bg-[var(--color-error-bg)] px-4 py-3"
        >
          <p className="text-sm text-[var(--color-error)]">{serverError}</p>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <AppInput
          variant="email"
          label={t("auth.email")}
          placeholder="you@company.com"
          autoComplete="email"
          error={errors.email ? t(errors.email.message as string) : undefined}
          {...register("email")}
        />

        <AppInput
          variant="password"
          label={t("auth.password")}
          placeholder="••••••••"
          autoComplete="current-password"
          error={
            errors.password ? t(errors.password.message as string) : undefined
          }
          {...register("password")}
        />

        <div className="flex justify-end">
          <Link
            href="/forgot-password"
            className="text-sm text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
          >
            {t("auth.forgot_password")}
          </Link>
        </div>

        <AppButton
          type="submit"
          size="lg"
          loading={isSubmitting}
          className="w-full"
        >
          {t("auth.login")}
        </AppButton>
      </form>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-[var(--color-gray-200)]" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-[var(--color-surface-card)] px-3 text-[var(--color-gray-400)]">
            {t("auth.or_continue_with")}
          </span>
        </div>
      </div>

      {/* Google sign-in */}
      <AppButton
        variant="outlined"
        size="lg"
        className="w-full"
        type="button"
        onClick={() => {
          authApi.googleLogin();
        }}
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
            fill="#4285F4"
          />
          <path
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            fill="#34A853"
          />
          <path
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            fill="#FBBC05"
          />
          <path
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            fill="#EA4335"
          />
        </svg>
        {t("auth.google")}
      </AppButton>

      {/* Sign up link */}
      <p className="mt-6 text-center text-sm text-[var(--color-gray-500)]">
        {t("auth.no_account")}{" "}
        <Link
          href="/signup"
          className="font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
        >
          {t("auth.signup")}
        </Link>
      </p>
    </div>
  );
}
