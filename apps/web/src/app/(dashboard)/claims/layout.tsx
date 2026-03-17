import type { ReactNode } from "react";
import { CompanySetupGuard } from "@/components/company/CompanySetupGuard";

export default function Layout({ children }: { children: ReactNode }) {
  return <CompanySetupGuard>{children}</CompanySetupGuard>;
}
