/* ── Shadow Agent API Service ─────────────────────────────── */
/* T469: API client for the Shadow Agent execution engine,     */
/* briefing service, and nudge service.                        */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export interface PaceStep {
  description: string;
  status: "pending" | "executing" | "done" | "failed" | "cancelled";
  result?: Record<string, unknown>;
}

export interface ShadowResponse {
  /** Response routing type — determines how the frontend handles it. */
  type:
    | "result"
    | "preview"
    | "navigation"
    | "advisory"
    | "attachment_required"
    | "out_of_scope"
    | "blocked"
    | "cancelled"
    | "double_confirm_required"
    | "undo_expired"
    | "info"
    | "undo_guidance"
    | "undo_not_supported"
    | "error";
  /** Human-readable message with "Arbor: " prefix. */
  message: string;
  /** Structured data payload (varies by response type). */
  data?: Record<string, unknown>;
  /** PACE session ID (present for preview/confirm/cancel flows). */
  session_id?: string;
  /** PACE session details including steps (present for preview type). */
  session?: {
    id: string;
    status: string;
    confirmation_message: string;
    trust_level: string;
    steps: PaceStep[];
    results?: Array<Record<string, unknown>>;
    confirmed_count?: number;
    requires_double_confirm?: boolean;
    is_undoable?: boolean;
  };
  /** Whether this response requires user confirmation before execution. */
  requires_confirmation?: boolean;
  /** Whether this action requires two-step confirmation (government/financial). */
  requires_double_confirm?: boolean;
  /** Number of confirmations received so far (for double_confirm flow). */
  confirmed_count?: number;
  /** Whether the action succeeded (present for result type). */
  success?: boolean;
  /** Error message (present when success is false). */
  error?: string;
  /** Classified intent details. */
  intent?: {
    module: string;
    action: string;
    trust_level: string;
    entities: Record<string, string>;
  };
  /** Navigation route (present for navigation type). */
  route?: string;
  /** Advisory routing target (present for advisory type). */
  route_to?: string;
  /** Original query routed to advisory (present for advisory type). */
  query?: string;
  /** Alternative guidance for out-of-scope queries. */
  alternative_guidance?: string;
  /** Attachment intent for file upload prompts. */
  attachment_intent?: string;
  /** ISO timestamp. */
  timestamp?: string;
}

export interface ShadowAction {
  session_id: string | null;
  module: string;
  action: string;
  trust_level: string;
  success: boolean;
  timestamp: string;
  message: string;
}

export interface ShadowHistoryResponse {
  actions: ShadowAction[];
  total: number;
  showing: number;
  timestamp: string;
}

/** Briefing section item (pending action, deadline, or attention item). */
export interface BriefingItem {
  id: string;
  category: string;
  title: string;
  description?: string;
  count?: number;
  days_remaining?: number;
  due_date?: string;
  action_type: "navigate" | "execute";
  route: string;
  priority: "high" | "medium" | "low";
}

export interface BriefingResponse {
  pending_actions: BriefingItem[];
  upcoming_deadlines: BriefingItem[];
  attention_needed: BriefingItem[];
  quick_stats: {
    active_employees: number | null;
    pending_leave_requests: number | null;
    payroll_status: string | null;
  };
  total_action_items: number;
  generated_date: string;
  company_id: number;
  timestamp: string;
}

/** A contextual nudge for the current page. */
export interface Nudge {
  id: string;
  type: "deadline" | "anomaly" | "completion" | "regulatory";
  message: string;
  action_type: "navigate" | "execute";
  route: string;
  dismissible: boolean;
  priority: number;
}

export interface NudgesResponse {
  nudges: Nudge[];
  page: string;
  company_id: number;
  timestamp: string;
}

/* ── API Methods ──────────────────────────────────────────── */

export const shadowApi = {
  /**
   * Execute a shadow agent command.
   * Routes through intent classification, guardrails, and the PACE loop.
   */
  execute(
    message: string,
    pageContext: string,
    conversationId?: number,
  ): Promise<ShadowResponse> {
    return apiClient.post<ShadowResponse>("/shadow/execute", {
      message,
      page_context: pageContext,
      ...(conversationId !== undefined && { conversation_id: conversationId }),
    });
  },

  /**
   * Confirm a pending PACE session and execute the planned action.
   */
  confirm(sessionId: string): Promise<ShadowResponse> {
    return apiClient.post<ShadowResponse>("/shadow/confirm", {
      session_id: sessionId,
    });
  },

  /**
   * Cancel a pending PACE session without executing.
   */
  cancel(sessionId: string): Promise<ShadowResponse> {
    return apiClient.post<ShadowResponse>("/shadow/cancel", {
      session_id: sessionId,
    });
  },

  /**
   * Undo a recently completed action (if supported).
   */
  undo(sessionId?: string): Promise<ShadowResponse> {
    return apiClient.post<ShadowResponse>("/shadow/undo", {
      ...(sessionId && { session_id: sessionId }),
    });
  },

  /**
   * Retrieve the user's recent shadow action history.
   */
  history(limit?: number): Promise<ShadowHistoryResponse> {
    const params: Record<string, string> = {};
    if (limit !== undefined) {
      params.limit = String(limit);
    }
    return apiClient.get<ShadowHistoryResponse>("/shadow/history", params);
  },

  /**
   * Get the morning briefing for the dashboard.
   * Returns categorized items: pending actions, deadlines, attention items, stats.
   */
  briefing(): Promise<BriefingResponse> {
    return apiClient.get<BriefingResponse>("/shadow/briefing");
  },

  /**
   * Get contextual nudges for the current page.
   * Returns up to 3 nudges sorted by urgency.
   */
  nudges(page: string): Promise<NudgesResponse> {
    return apiClient.get<NudgesResponse>("/shadow/nudges", { page });
  },
};
