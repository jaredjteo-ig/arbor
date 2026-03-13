"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { ClientCompany } from "@/types/api";

/* ── Types ────────────────────────────────────────────────── */

interface ClientContextValue {
  /** Currently selected client (null = no client selected / personal view) */
  activeClient: ClientCompany | null;
  /** Switch to a different client company */
  switchClient: (client: ClientCompany | null) => void;
  /** Whether a client is currently selected */
  hasActiveClient: boolean;
}

/* ── Context ──────────────────────────────────────────────── */

const ClientContext = createContext<ClientContextValue | null>(null);

/* ── Provider ─────────────────────────────────────────────── */

export function ClientProvider({ children }: { children: ReactNode }) {
  const [activeClient, setActiveClient] = useState<ClientCompany | null>(null);

  const switchClient = useCallback((client: ClientCompany | null) => {
    setActiveClient(client);
    // Persist selection across page navigations within session
    if (client) {
      sessionStorage.setItem("active_client_id", String(client.id));
    } else {
      sessionStorage.removeItem("active_client_id");
    }
  }, []);

  return (
    <ClientContext.Provider
      value={{
        activeClient,
        switchClient,
        hasActiveClient: activeClient !== null,
      }}
    >
      {children}
    </ClientContext.Provider>
  );
}

/* ── Hook ─────────────────────────────────────────────────── */

export function useClient(): ClientContextValue {
  const context = useContext(ClientContext);
  if (!context) {
    throw new Error("useClient must be used within a ClientProvider");
  }
  return context;
}
