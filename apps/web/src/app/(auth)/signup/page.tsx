"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { AppButton, AppInput } from "@/components/design-system";
import {
  authApi,
  AuthError,
  type RegisterEmployeeData,
} from "@/services/api/auth";
import {
  validateInvite,
  type InviteValidation,
} from "@/services/api/employees";
import { useAuth } from "@/contexts/AuthContext";

/* ── Validation schemas ────────────────────────────────────── */

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
        <Link href="/login">
          <AppButton
            variant={showLoginLink ? "text" : "outlined"}
            size="lg"
            className="w-full"
            type="button"
          >
            {t("auth.back_to_login")}
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
  const { loginWithTokens } = useAuth();
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
      // Store tokens AND update auth context state so sidebar/name render correctly
      loginWithTokens(
        response.access_token,
        response.refresh_token,
        response.user,
      );
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

/* ── Invitation-only notice (no self-service signup) ─────── */

function InvitationOnlyNotice() {
  const { t } = useTranslation();

  return (
    <div className="rounded-[12px] bg-[var(--color-surface-card)] shadow-[var(--shadow-raised)] p-8">
      <Logo />

      {/* Heading */}
      <div className="text-center mb-6">
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          Registration by Invitation Only
        </h1>
        <p className="mt-2 text-sm text-[var(--color-gray-500)] leading-relaxed">
          New accounts are created through employer invitations. If you have
          received an invitation email, please use the link provided. Otherwise,
          contact your administrator for access.
        </p>
      </div>

      {/* Login link */}
      <Link href="/login">
        <AppButton variant="primary" size="lg" className="w-full" type="button">
          {t("auth.login")}
        </AppButton>
      </Link>

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

  /* No token present -- show invitation-only notice */
  if (inviteState.status === "idle") {
    return <InvitationOnlyNotice />;
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
