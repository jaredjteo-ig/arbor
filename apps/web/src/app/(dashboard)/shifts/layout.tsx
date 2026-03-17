"use client";
import type { ReactNode } from "react";
import { CalendarClock } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "shifts", title: "Shift Scheduling", tagline: "Visual shift allocation with compliance checking",
  icon: CalendarClock, color: "text-pink-600", bgColor: "bg-pink-50",
  description: "Plan your workforce schedule with visual drag-and-drop allocation. The system checks availability, integrates with leave, and ensures you stay within the 44-hour weekly limit.",
  usps: [
    "Weekly shift grid — visual, drag-and-drop scheduling",
    "Leave-integrated availability — blocked employees shown",
    "44-hour weekly limit compliance check (Employment Act)",
    "Schedule publishing with employee notifications",
    "Hours tracking per employee per week",
    "Mobile schedule access — employees see their shifts",
  ],
  features: [
    { title: "Shift Templates", description: "Create reusable shift templates with start/end times, break duration. Morning, afternoon, night shifts." },
    { title: "Shift Assignment", description: "Assign employees to shifts on a weekly grid. Check availability before assigning." },
    { title: "Availability Check", description: "Cross-references approved leave and existing assignments. Prevents double-booking." },
    { title: "Schedule Publishing", description: "Publish the week's schedule. Employees notified of their assignments." },
    { title: "Hours Tracking", description: "Total hours per employee per week. Flag employees exceeding 44-hour EA limit." },
    { title: "Payroll Integration", description: "Shift hours feed into timesheet → payroll OT calculation pipeline." },
  ],
};

export default function ShiftsLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
