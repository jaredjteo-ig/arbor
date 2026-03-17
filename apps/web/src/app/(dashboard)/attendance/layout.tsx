"use client";
import type { ReactNode } from "react";
import { Clock } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "attendance", title: "Attendance & Time", tagline: "Clock in/out, overtime tracking, timesheet approval",
  icon: Clock, color: "text-violet-600", bgColor: "bg-violet-50",
  description: "Track when employees arrive, leave, and how many hours they work. GPS-verified clock-in, automatic overtime calculation, and timesheet approval — all synced to payroll.",
  usps: [
    "Mobile clock in/out with GPS and photo verification",
    "Automatic overtime calculation (Part IV EA employees)",
    "Timesheet approval workflow — manager signs off monthly",
    "Real-time sync with payroll — OT hours auto-included",
    "Lateness detection with configurable grace period",
    "Multi-location support — track across offices/sites",
  ],
  features: [
    { title: "Clock In/Out", description: "Web and mobile check-in. GPS coordinates and optional photo proof captured automatically." },
    { title: "Overtime Tracking", description: "Hours beyond standard work hours flagged as OT. Rate: 1.5x hourly basic (EA s37). Max 72 hours/month." },
    { title: "Timesheet Approval", description: "Monthly timesheets generated from daily records. Manager reviews and approves before payroll." },
    { title: "Attendance Summary", description: "Per-employee summary: present days, absent, late, half-day, total hours. Colour-coded status." },
    { title: "Lateness Tracking", description: "Clock-in vs scheduled start time. Grace period configurable. Late arrivals flagged." },
    { title: "Payroll Sync", description: "Approved timesheets feed OT hours directly into payroll calculation. Zero manual entry." },
  ],
};

export default function AttendanceLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
