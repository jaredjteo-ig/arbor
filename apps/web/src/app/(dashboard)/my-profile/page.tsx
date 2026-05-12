"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { AppCard } from "@/components/design-system";
import { apiClient } from "@/services/api/client";
import {
  User,
  Phone,
  MapPin,
  Landmark,
  Shield,
  Heart,
  Save,
  CheckCircle,
  AlertTriangle,
  Loader2,
} from "lucide-react";

/* ── Types ─────────────────────────────────────────────────── */

interface ProfileData {
  id: number;
  name: string;
  email: string;
  alias: string;
  date_of_birth: string;
  gender: string;
  race: string;
  nationality: string;
  religion: string;
  marital_status: string;
  phone: string;
  photo_url: string;
  nric_fin: string;
  nric_fin_last4: string;
  residential_address: string;
  postal_code: string;
  address_block: string;
  address_street: string;
  address_unit: string;
  address_building: string;
  address_postal_code: string;
  bank_name: string;
  bank_account_number: string;
  bank_account_last4: string;
  bank_code: string;
  branch_code: string;
  department: string;
  designation: string;
  start_date: string;
  employment_type: string;
}

/* ── Field config ──────────────────────────────────────────── */

const GENDER_OPTIONS = ["male", "female"];
const RACE_OPTIONS = ["chinese", "malay", "indian", "eurasian", "other"];
const RELIGION_OPTIONS = [
  "buddhist",
  "christian",
  "hindu",
  "islam",
  "sikh",
  "taoist",
  "none",
  "other",
];
const MARITAL_OPTIONS = ["single", "married", "divorced", "widowed"];
const BANK_OPTIONS = [
  "DBS/POSB",
  "OCBC",
  "UOB",
  "Maybank",
  "CIMB",
  "HSBC",
  "Standard Chartered",
  "Citibank",
  "Bank of China",
  "Other",
];

/* ── Section component ─────────────────────────────────────── */

function Section({
  icon: Icon,
  title,
  children,
  onSave,
  saving,
  saved,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  children: React.ReactNode;
  onSave: () => void;
  saving: boolean;
  saved: boolean;
}) {
  return (
    <AppCard variant="flat">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Icon className="w-5 h-5 text-[var(--color-primary)]" />
          <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
            {title}
          </h3>
        </div>
        <button
          onClick={onSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-[var(--color-primary)] text-white hover:bg-[var(--color-primary-dark)] disabled:opacity-50 transition-colors"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <CheckCircle className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {saving ? "Saving..." : saved ? "Saved" : "Save"}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>
    </AppCard>
  );
}

/* ── Field component ───────────────────────────────────────── */

function Field({
  label,
  value,
  onChange,
  onFocus,
  type = "text",
  options,
  placeholder,
  readOnly,
  required,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  onFocus?: () => void;
  type?: "text" | "date" | "select" | "tel";
  options?: string[];
  placeholder?: string;
  readOnly?: boolean;
  required?: boolean;
}) {
  const id = label.toLowerCase().replace(/\s+/g, "-");
  const baseClasses =
    "w-full px-3 py-2 text-sm border border-[var(--color-gray-300)] rounded-md bg-white focus:ring-2 focus:ring-[var(--color-primary)]/20 focus:border-[var(--color-primary)] transition-colors";
  const readOnlyClasses = readOnly
    ? "bg-[var(--color-gray-50)] cursor-not-allowed text-[var(--color-gray-500)]"
    : "";

  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-medium text-[var(--color-gray-600)] mb-1"
      >
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {type === "select" && options ? (
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={readOnly}
          className={`${baseClasses} ${readOnlyClasses}`}
        >
          <option value="">Select...</option>
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt.charAt(0).toUpperCase() + opt.slice(1)}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={onFocus}
          readOnly={readOnly}
          placeholder={placeholder}
          className={`${baseClasses} ${readOnlyClasses}`}
        />
      )}
    </div>
  );
}

/* ── Main page ─────────────────────────────────────────────── */

export default function MyProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingSection, setSavingSection] = useState<string | null>(null);
  const [savedSection, setSavedSection] = useState<string | null>(null);
  const [nricEditing, setNricEditing] = useState(false);
  const [bankEditing, setBankEditing] = useState(false);

  // Track which fields are required for payroll
  const payrollRequired = [
    "date_of_birth",
    "nric_fin",
    "bank_name",
    "bank_account_number",
  ];

  const fetchProfile = useCallback(async () => {
    try {
      const data = await apiClient.get<ProfileData>("/employees/me");
      setProfile(data);
    } catch (err) {
      setError("Unable to load your profile. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const updateField = (field: keyof ProfileData, value: string) => {
    setProfile((prev) => (prev ? { ...prev, [field]: value } : prev));
    setSavedSection(null);
  };

  const saveSection = async (section: string, fields: Partial<ProfileData>) => {
    setSavingSection(section);
    try {
      await apiClient.put("/employees/me", fields);
      setSavedSection(section);
      setTimeout(() => setSavedSection(null), 2000);
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSavingSection(null);
    }
  };

  // Calculate completion percentage
  const completionFields = [
    "name",
    "date_of_birth",
    "gender",
    "race",
    "phone",
    "nric_fin",
    "residential_address",
    "bank_name",
    "bank_account_number",
  ];
  const filledCount = profile
    ? completionFields.filter((f) => profile[f as keyof ProfileData]).length
    : 0;
  const completionPct = Math.round(
    (filledCount / completionFields.length) * 100,
  );

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {[1, 2, 3].map((i) => (
          <AppCard key={i} variant="flat">
            <div className="animate-pulse space-y-3">
              <div className="h-4 w-32 bg-[var(--color-gray-200)] rounded" />
              <div className="h-8 w-full bg-[var(--color-gray-100)] rounded" />
              <div className="h-8 w-full bg-[var(--color-gray-100)] rounded" />
            </div>
          </AppCard>
        ))}
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="max-w-3xl mx-auto p-6">
        <AppCard variant="flat">
          <div className="flex items-center gap-2 text-red-600">
            <AlertTriangle className="w-5 h-5" />
            <p>{error}</p>
          </div>
        </AppCard>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-gray-900)]">
          My Profile
        </h1>
        <p className="text-sm text-[var(--color-gray-500)] mt-1">
          Manage your personal information. Your data is encrypted and accessed
          only for HR and payroll purposes.
        </p>
      </div>

      {/* Completion bar */}
      {completionPct < 100 && (
        <AppCard variant="flat">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-[var(--color-gray-700)]">
                Profile {completionPct}% complete
              </p>
              <p className="text-xs text-[var(--color-gray-500)]">
                Complete your profile so payroll can be processed for you.
              </p>
              <div className="mt-2 h-2 w-full bg-[var(--color-gray-100)] rounded-full">
                <div
                  className="h-2 bg-[var(--color-primary)] rounded-full transition-all"
                  style={{ width: `${completionPct}%` }}
                />
              </div>
            </div>
          </div>
        </AppCard>
      )}

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-md text-sm">
          {error}
        </div>
      )}

      {/* Section 1: Personal Information */}
      <Section
        icon={User}
        title="Personal Information"
        onSave={() =>
          saveSection("personal", {
            name: profile.name,
            alias: profile.alias,
            date_of_birth: profile.date_of_birth,
            gender: profile.gender,
            race: profile.race,
            nationality: profile.nationality,
            religion: profile.religion,
            marital_status: profile.marital_status,
          })
        }
        saving={savingSection === "personal"}
        saved={savedSection === "personal"}
      >
        <Field
          label="Full Name"
          value={profile.name}
          onChange={(v) => updateField("name", v)}
          required
        />
        <Field
          label="Alias / Display Name"
          value={profile.alias || ""}
          onChange={(v) => updateField("alias", v)}
          placeholder="Optional"
        />
        <Field
          label="Date of Birth"
          value={profile.date_of_birth}
          onChange={(v) => updateField("date_of_birth", v)}
          type="date"
          required
        />
        <Field
          label="Gender"
          value={profile.gender}
          onChange={(v) => updateField("gender", v)}
          type="select"
          options={GENDER_OPTIONS}
        />
        <Field
          label="Race"
          value={profile.race}
          onChange={(v) => updateField("race", v)}
          type="select"
          options={RACE_OPTIONS}
        />
        <Field
          label="Nationality"
          value={profile.nationality || ""}
          onChange={(v) => updateField("nationality", v)}
        />
        <Field
          label="Religion"
          value={profile.religion || ""}
          onChange={(v) => updateField("religion", v)}
          type="select"
          options={RELIGION_OPTIONS}
        />
        <Field
          label="Marital Status"
          value={profile.marital_status}
          onChange={(v) => updateField("marital_status", v)}
          type="select"
          options={MARITAL_OPTIONS}
        />
      </Section>

      {/* Section 2: Contact */}
      <Section
        icon={Phone}
        title="Contact"
        onSave={() =>
          saveSection("contact", { phone: profile.phone, email: profile.email })
        }
        saving={savingSection === "contact"}
        saved={savedSection === "contact"}
      >
        <Field
          label="Phone"
          value={profile.phone || ""}
          onChange={(v) => updateField("phone", v)}
          type="tel"
          placeholder="+65 XXXX XXXX"
        />
        <Field
          label="Email"
          value={profile.email}
          onChange={() => {}}
          readOnly
        />
      </Section>

      {/* Section 3: Identity */}
      <Section
        icon={Shield}
        title="Identity Document"
        onSave={() => {
          // Only send NRIC if user actually entered a new value (not the mask)
          const val = profile.nric_fin || "";
          if (val && !val.includes("*")) {
            saveSection("identity", { nric_fin: val });
          } else {
            setSavedSection("identity");
            setTimeout(() => setSavedSection(null), 2000);
          }
        }}
        saving={savingSection === "identity"}
        saved={savedSection === "identity"}
      >
        <Field
          label="NRIC / FIN"
          /*
           * Display the server-masked value verbatim. The backend's
           * `mask_nric` helper already returns the SG-correct shape:
           * first character preserved (S/T/F/G citizenship band),
           * middle 4 characters hidden, last 4 visible — e.g.
           * `S****567A` (9 chars). Reconstructing `****{last4}` here
           * (the old behaviour) dropped the leading char and produced
           * an 8-char string, which read as a malformed NRIC.
           * See audit P4-QW-5.
           */
          value={
            profile.nric_fin && !nricEditing
              ? profile.nric_fin
              : profile.nric_fin || ""
          }
          onChange={(v) => {
            setNricEditing(true);
            updateField("nric_fin", v);
          }}
          onFocus={() => {
            // Clear masked value on focus so user can type fresh
            if (profile.nric_fin?.includes("*")) {
              updateField("nric_fin", "");
            }
            setNricEditing(true);
          }}
          placeholder="S1234567A"
          required
        />
        <div className="text-xs text-[var(--color-gray-500)] md:col-span-2 flex items-start gap-1.5">
          <Shield className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>
            Your NRIC/FIN is encrypted at rest and accessed only for CPF, tax
            filing, and statutory purposes under PDPA compliance.
          </span>
        </div>
      </Section>

      {/* Section 4: Address */}
      <Section
        icon={MapPin}
        title="Address"
        onSave={() =>
          saveSection("address", {
            address_block: profile.address_block,
            address_street: profile.address_street,
            address_unit: profile.address_unit,
            address_building: profile.address_building,
            address_postal_code: profile.address_postal_code,
          })
        }
        saving={savingSection === "address"}
        saved={savedSection === "address"}
      >
        <Field
          label="Block / House No."
          value={profile.address_block || ""}
          onChange={(v) => updateField("address_block", v)}
          placeholder="123"
        />
        <Field
          label="Street Name"
          value={profile.address_street || ""}
          onChange={(v) => updateField("address_street", v)}
          placeholder="Orchard Road"
        />
        <Field
          label="Unit No."
          value={profile.address_unit || ""}
          onChange={(v) => updateField("address_unit", v)}
          placeholder="#05-123"
        />
        <Field
          label="Building Name"
          value={profile.address_building || ""}
          onChange={(v) => updateField("address_building", v)}
          placeholder="Optional"
        />
        <Field
          label="Postal Code"
          value={profile.address_postal_code || ""}
          onChange={(v) => updateField("address_postal_code", v)}
          placeholder="123456"
        />
      </Section>

      {/* Section 5: Banking */}
      <Section
        icon={Landmark}
        title="Bank Account"
        onSave={() => {
          // Only send bank account if user actually entered a new value
          const acct = profile.bank_account_number || "";
          const bankFields: Partial<ProfileData> = {
            bank_name: profile.bank_name,
            bank_code: profile.bank_code,
            branch_code: profile.branch_code,
          };
          if (acct && !acct.includes("*")) {
            bankFields.bank_account_number = acct;
          }
          saveSection("banking", bankFields);
        }}
        saving={savingSection === "banking"}
        saved={savedSection === "banking"}
      >
        <Field
          label="Bank Name"
          value={profile.bank_name || ""}
          onChange={(v) => updateField("bank_name", v)}
          type="select"
          options={BANK_OPTIONS}
          required
        />
        <Field
          label="Account Number"
          value={
            profile.bank_account_number && !bankEditing
              ? profile.bank_account_last4
                ? `****${profile.bank_account_last4}`
                : profile.bank_account_number
              : profile.bank_account_number || ""
          }
          onChange={(v) => {
            setBankEditing(true);
            updateField("bank_account_number", v);
          }}
          onFocus={() => {
            if (profile.bank_account_number?.includes("*")) {
              updateField("bank_account_number", "");
            }
            setBankEditing(true);
          }}
          required
        />
        <Field
          label="Bank Code"
          value={profile.bank_code || ""}
          onChange={(v) => updateField("bank_code", v)}
          placeholder="7171"
        />
        <Field
          label="Branch Code"
          value={profile.branch_code || ""}
          onChange={(v) => updateField("branch_code", v)}
          placeholder="001"
        />
        <div className="text-xs text-[var(--color-gray-500)] md:col-span-2 flex items-start gap-1.5">
          <Shield className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
          <span>
            Bank details are encrypted at rest and used only for salary payment
            processing.
          </span>
        </div>
      </Section>

      {/* Section 6: Emergency Contact */}
      <AppCard variant="flat">
        <div className="flex items-center gap-2 mb-3">
          <Heart className="w-5 h-5 text-[var(--color-gray-400)]" />
          <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
            Emergency Contact
          </h3>
        </div>
        <p className="text-sm text-[var(--color-gray-500)]">
          Your HR administrator manages emergency contacts. Please contact HR to
          update this information.
        </p>
      </AppCard>

      {/* Employment info (read-only) */}
      <AppCard variant="flat">
        <div className="flex items-center gap-2 mb-4">
          <User className="w-5 h-5 text-[var(--color-gray-400)]" />
          <h3 className="text-base font-semibold text-[var(--color-gray-900)]">
            Employment Details
          </h3>
          <span className="text-xs text-[var(--color-gray-400)] ml-auto">
            Managed by HR
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Field
            label="Department"
            value={profile.department || "—"}
            onChange={() => {}}
            readOnly
          />
          <Field
            label="Designation"
            value={profile.designation || "—"}
            onChange={() => {}}
            readOnly
          />
          <Field
            label="Employment Type"
            value={
              profile.employment_type
                ? profile.employment_type
                    .split("_")
                    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                    .join("-")
                : "—"
            }
            onChange={() => {}}
            readOnly
          />
          <Field
            label="Start Date"
            value={
              profile.start_date
                ? new Date(profile.start_date).toLocaleDateString("en-SG", {
                    day: "2-digit",
                    month: "short",
                    year: "numeric",
                  })
                : "—"
            }
            onChange={() => {}}
            readOnly
          />
        </div>
      </AppCard>
    </div>
  );
}
