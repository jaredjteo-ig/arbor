"use client";

import type { ReactNode } from "react";
import { Package } from "lucide-react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

const MODULE = {
  id: "inventory",
  title: "Inventory Management",
  tagline: "Track company assets and equipment",
  icon: Package,
  color: "text-orange-600",
  bgColor: "bg-orange-50",
  description:
    "Manage company equipment, IT assets, and supplies. Track item locations, assignments, and lifecycle from procurement to retirement. Employee self-service for item requests and acknowledgements.",
  usps: [
    "Multi-location inventory with category organisation",
    "Item lifecycle: purchase, issue, return, maintenance, retire",
    "Employee assignment tracking with acknowledgement",
    "Self-service item requests with approval workflow",
    "Movement history and audit trail",
    "Asset valuation and depreciation tracking",
  ],
  features: [
    {
      title: "Locations & Categories",
      description:
        "Organise inventory by physical locations and logical categories. Hierarchical categories for detailed classification.",
    },
    {
      title: "Item Management",
      description:
        "Track individual items with serial numbers, purchase dates, costs, and current status. Bulk import and barcode support.",
    },
    {
      title: "Issue & Return",
      description:
        "Issue items to employees with acknowledgement. Track returns, transfers between locations, and maintenance schedules.",
    },
    {
      title: "Self-Service Requests",
      description:
        "Employees request items by category or specific SKU. Manager approval workflow with automated fulfilment tracking.",
    },
  ],
};

export default function InventoryLayout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard module={MODULE}>{children}</CompanySetupGuard>;
}
