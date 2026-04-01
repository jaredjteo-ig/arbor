"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { AppButton, AppInput } from "@/components/design-system";
import { useAuth } from "@/contexts/AuthContext";
import {
  authApi,
  AuthError,
  type RegisterEmployeeData,
} from "@/services/api/auth";
import {
  validateInvite,
  type InviteValidation,
} from "@/services/api/employees";

/* ── Validation schemas ────────────────────────────────────── */

const signupSchema = z
  .object({
    name: z.string().min(1, "auth.name_required"),
    email: z.string().min(1, "auth.invalid_email").email("auth.invalid_email"),
    password: z.string().min(8, "auth.password_requirements"),
    confirmPassword: z.string().min(1, "auth.passwords_must_match"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "auth.passwords_must_match",
    path: ["confirmPassword"],
  });

type SignupFormValues = z.infer<typeof signupSchema>;

const inviteSchema = z.object({
  name: z.string().min(1, "auth.name_required"),
  email: z.string().email("auth.invalid_email"),
  password: z.string().min(8, "auth.password_requirements"),
});

type InviteFormValues = z.infer<typeof inviteSchema>;

/* ── Invite token states ───────────────────────────────────── */

type InviteState =
  | { status: "idle" }
  | { status: "validating" }
  | { status: "valid"; data: InviteValidation }
  | { status: "invalid"; message: string }
  | { status: "expired"; message: string }
  | { status: "already_used"; message: string }
  | { status: "network_error"; message: string };

/* ── Logo block (shared) ───────────────────────────────────── */

function Logo() {
  return (
    <div className="flex justify-center mb-6">
      <div className="flex items-center gap-2">
        <div className="flex items-center justify-center rounded-lg bg-[var(--color-primary)] text-white font-bold w-10 h-10 text-lg">
          C
        </div>
        <span className="text-xl font-bold text-[var(--color-primary)]">
          Central
        </span>
      </div>
    </div>
  );
}

/* ── Invite banner ─────────────────────────────────────────── */

function InviteBanner({
  companyName,
  role,
}: {
  companyName: string;
  role: string;
}) {
  const { t } = useTranslation();

  return (
    <div className="mb-6 rounded-[10px] bg-gradient-to-r from-indigo-600 to-blue-600 px-5 py-4 text-white shadow-md">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/20">
          <svg
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
            />
          </svg>
        </div>
        <div>
          <p className="text-sm font-semibold leading-snug">
            {t("auth.invite_banner", { company: companyName, role })}
          </p>
          <p className="mt-1 text-xs text-white/80">
            {t("auth.invite_form_note")}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Invite error state ────────────────────────────────────── */

function InviteError({ inviteState }: { inviteState: InviteState }) {
  const { t } = useTranslation();

  let message: string;
  let showLoginLink = false;

  switch (inviteState.status) {
    case "expired":
      message = t("auth.invite_expired");
      break;
    case "already_used":
      message = t("auth.invite_already_used");
      showLoginLink = true;
      break;
    case "network_error":
      message = t("auth.invite_network_error");
      break;
    case "invalid":
    default:
      message = t("auth.invite_invalid");
      break;
  }

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      <Logo />

      <div className="mb-6 rounded-[10px] border-l-4 border-[var(--color-error)] bg-[var(--color-error-bg)] px-5 py-4">
        <p className="text-sm font-medium text-[var(--color-error)]">
          {message}
        </p>
      </div>

      <div className="flex flex-col gap-3">
        {showLoginLink && (
          <Link href="/login">
            <AppButton
              variant="outlined"
              size="lg"
              className="w-full"
              type="button"
            >
              {t("auth.invite_go_to_login")}
            </AppButton>
          </Link>
        )}
        <Link href="/signup">
          <AppButton
            variant={showLoginLink ? "text" : "outlined"}
            size="lg"
            className="w-full"
            type="button"
          >
            {t("auth.invite_signup_instead")}
          </AppButton>
        </Link>
      </div>
    </div>
  );
}

/* ── Invite loading skeleton ───────────────────────────────── */

function InviteLoading() {
  const { t } = useTranslation();

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      <Logo />
      <div className="flex flex-col items-center gap-4 py-8">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-gray-200)] border-t-[var(--color-primary)]" />
        <p className="text-sm text-[var(--color-gray-500)]">
          {t("auth.invite_validating")}
        </p>
      </div>
    </div>
  );
}

/* ── Invite acceptance form ────────────────────────────────── */

function InviteForm({
  invitation,
  token,
}: {
  invitation: InviteValidation;
  token: string;
}) {
  const { t } = useTranslation();
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      name: "",
      email: invitation.email,
      password: "",
    },
  });

  async function onSubmit(data: InviteFormValues) {
    setServerError(null);
    try {
      const payload: RegisterEmployeeData = {
        name: data.name,
        email: data.email,
        password: data.password,
        invitation_token: token,
      };
      const response = await authApi.registerEmployee(payload);
      // Store tokens
      localStorage.setItem("access_token", response.access_token);
      localStorage.setItem("refresh_token", response.refresh_token);
      // Redirect to employee dashboard
      router.push("/my-dashboard");
    } catch (error) {
      if (error instanceof AuthError) {
        setServerError(error.message);
      } else {
        setServerError(t("auth.registration_failed"));
      }
    }
  }

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      <Logo />

      {/* Heading */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          {t("auth.invite_heading")}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-gray-500)]">
          {t("auth.invite_subheading")}
        </p>
      </div>

      {/* Invite banner */}
      <InviteBanner
        companyName={invitation.company_name}
        role={invitation.role}
      />

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
          label={t("auth.name")}
          placeholder="Jane Doe"
          autoComplete="name"
          error={errors.name ? t(errors.name.message as string) : undefined}
          {...register("name")}
        />

        <AppInput
          variant="email"
          label={t("auth.email")}
          autoComplete="email"
          readOnly
          value={invitation.email}
          className="bg-[var(--color-gray-50)] cursor-not-allowed opacity-70"
          {...register("email")}
        />

        <AppInput
          variant="password"
          label={t("auth.password")}
          placeholder="••••••••"
          autoComplete="new-password"
          helperText={t("auth.password_requirements")}
          error={
            errors.password ? t(errors.password.message as string) : undefined
          }
          {...register("password")}
        />

        <AppButton
          type="submit"
          size="lg"
          loading={isSubmitting}
          className="w-full"
        >
          {t("auth.invite_accept")}
        </AppButton>
      </form>

      {/* Sign in link */}
      <p className="mt-6 text-center text-sm text-[var(--color-gray-500)]">
        {t("auth.have_account")}{" "}
        <Link
          href="/login"
          className="font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
        >
          {t("auth.login")}
        </Link>
      </p>
    </div>
  );
}

/* ── Standard signup form (no invite) ──────────────────────── */

function StandardSignupForm() {
  const { t } = useTranslation();
  const { register: registerUser } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
  });

  async function onSubmit(data: SignupFormValues) {
    setServerError(null);
    try {
      await registerUser({
        name: data.name,
        email: data.email,
        password: data.password,
      });
    } catch (error) {
      if (error instanceof AuthError) {
        setServerError(error.message);
      } else {
        setServerError(t("auth.registration_failed"));
      }
    }
  }

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      <Logo />

      {/* Heading */}
      <div className="text-center mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          {t("auth.signup_heading")}
        </h1>
        <p className="mt-1 text-sm text-[var(--color-gray-500)]">
          {t("auth.signup_subheading")}
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
          label={t("auth.name")}
          placeholder="Jane Doe"
          autoComplete="name"
          error={errors.name ? t(errors.name.message as string) : undefined}
          {...register("name")}
        />

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
          autoComplete="new-password"
          helperText={t("auth.password_requirements")}
          error={
            errors.password ? t(errors.password.message as string) : undefined
          }
          {...register("password")}
        />

        <AppInput
          variant="password"
          label={t("auth.confirm_password")}
          placeholder="••••••••"
          autoComplete="new-password"
          error={
            errors.confirmPassword
              ? t(errors.confirmPassword.message as string)
              : undefined
          }
          {...register("confirmPassword")}
        />

        <AppButton
          type="submit"
          size="lg"
          loading={isSubmitting}
          className="w-full"
        >
          {t("auth.create_account")}
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

      {/* Google sign-up */}
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
        {t("auth.google_signup")}
      </AppButton>

      {/* Sign in link */}
      <p className="mt-6 text-center text-sm text-[var(--color-gray-500)]">
        {t("auth.have_account")}{" "}
        <Link
          href="/login"
          className="font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-light)] transition-colors"
        >
          {t("auth.login")}
        </Link>
      </p>
    </div>
  );
}

/* ── Main signup page (reads search params) ────────────────── */

function SignupContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [inviteState, setInviteState] = useState<InviteState>(
    token ? { status: "validating" } : { status: "idle" },
  );

  useEffect(() => {
    if (!token) {
      setInviteState({ status: "idle" });
      return;
    }

    let cancelled = false;

    async function validate() {
      try {
        const data = await validateInvite(token as string);
        if (!cancelled) {
          setInviteState({ status: "valid", data });
        }
      } catch (error: unknown) {
        if (cancelled) return;

        const err = error as { status?: number; message?: string };
        const msg = err.message ?? "";
        const msgLower = msg.toLowerCase();

        if (msgLower.includes("expired")) {
          setInviteState({ status: "expired", message: msg });
        } else if (
          msgLower.includes("already been used") ||
          msgLower.includes("already accepted")
        ) {
          setInviteState({ status: "already_used", message: msg });
        } else if (err.status === 404 || err.status === 400) {
          setInviteState({ status: "invalid", message: msg });
        } else {
          setInviteState({ status: "network_error", message: msg });
        }
      }
    }

    validate();

    return () => {
      cancelled = true;
    };
  }, [token]);

  /* No token present -- standard signup */
  if (inviteState.status === "idle") {
    return <StandardSignupForm />;
  }

  /* Validating token */
  if (inviteState.status === "validating") {
    return <InviteLoading />;
  }

  /* Token valid -- show invite acceptance form */
  if (inviteState.status === "valid") {
    return <InviteForm invitation={inviteState.data} token={token as string} />;
  }

  /* Token error states */
  return <InviteError inviteState={inviteState} />;
}

/* ── Page export (wrapped in Suspense for useSearchParams) ── */

export default function SignupPage() {
  return (
    <Suspense fallback={<InviteLoading />}>
      <SignupContent />
    </Suspense>
  );
}
