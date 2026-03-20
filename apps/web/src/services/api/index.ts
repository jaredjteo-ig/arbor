/* ── API Services Barrel Export ───────────────────────────── */

export { apiClient, ApiRequestError } from "./client";
export { createSSEStream, type SSECallbacks } from "./sse";

export { adminApi } from "./admin";
export { authApi } from "./auth";
export { advisoryApi } from "./advisory";
export { calculatorsApi } from "./calculators";
export { complianceApi } from "./compliance";
export { documentsApi } from "./documents";
export { profileApi } from "./profile";
export { kbApi } from "./kb";
export { searchApi } from "./search";
export { alertsApi } from "./alerts";
export { clientsApi } from "./clients";
export { emergencyApi } from "./emergency";
export { helpApi } from "./help";
export { settingsApi } from "./settings";
export { learningApi } from "./learning";
export { qaApi } from "./qa";
export { employeesApi } from "./employees";
export { leaveApi } from "./leave";
export { claimsApi } from "./claims";
export { attendanceApi } from "./attendance";
export { humanizeError } from "./errors";
export { integrationsApi } from "./integrations";
export { appraisalsApi } from "./appraisals";
export { projectsApi } from "./projects";
export { inventoryApi } from "./inventory";
export { recruitmentApi } from "./recruitment";
export { reportsApi } from "./reports";
export { shadowApi } from "./shadow";
export type {
  ShadowResponse,
  ShadowAction,
  BriefingResponse,
  BriefingItem,
  Nudge,
  NudgesResponse,
  PaceStep,
} from "./shadow";
