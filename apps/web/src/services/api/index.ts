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
export { humanizeError } from "./errors";
