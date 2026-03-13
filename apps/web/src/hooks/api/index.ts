/* ── API Hooks Barrel Export ──────────────────────────────── */

export {
  adminKeys,
  useAdminMetrics,
  useRegulatoryUpdates,
  useStalenessSummary,
  useAdminFeedbackSummary,
  useAdminKbGaps,
  useAdminRecommendations,
  useCreateUpdate,
  useSubmitForReview,
  useApproveUpdate,
  useRejectUpdate,
  usePublishUpdate,
} from "./useAdmin";

export {
  advisoryKeys,
  useAdvisoryQuery,
  useAdvisoryHistory,
} from "./useAdvisory";

export {
  useCpfCalculation,
  useLeaveCalculation,
  useSalaryCalculation,
} from "./useCalculators";

export {
  complianceKeys,
  useComplianceStatus,
  useComplianceCheck,
  useComplianceGapAnalysis,
} from "./useCompliance";

export {
  documentKeys,
  useDocumentTemplates,
  useDocumentTemplate,
  useDocumentGenerate,
} from "./useDocuments";

export {
  profileKeys,
  useCompanyProfile,
  useWorkforceBreakdown,
  useCreateProfile,
  useUpdateProfile,
} from "./useProfile";

export { kbKeys, useActs, useDomains, useProvision, useKbQuery } from "./useKb";

export { useSemanticSearch, useFulltextSearch } from "./useSearch";

export {
  alertKeys,
  useAlerts,
  useUnreadAlertCount,
  useMarkAlertRead,
  useDismissAlert,
} from "./useAlerts";

export {
  emergencyKeys,
  useEmergencyScenarios,
  useEmergencyEscalate,
} from "./useEmergency";

export { helpKeys, useHelpArticles, useGettingStarted } from "./useHelp";

export {
  qaKeys,
  useQaSessions,
  useQaSession,
  useQaSessionConversations,
  useCreateQaSession,
  useQaEvaluations,
  useSubmitEvaluation,
  useQaPatches,
  useApprovePatch,
  useRejectPatch,
} from "./useQa";
