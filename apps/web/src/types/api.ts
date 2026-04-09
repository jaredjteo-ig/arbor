/* ── Centralized API Type Definitions ──────────────────────── */
/* All request/response shapes for the Arbor Nexus backend.    */

/* ── Common ──────────────────────────────────────────────────── */

export interface ApiError {
  detail: string;
  status: number;
}

/* ── Advisory ────────────────────────────────────────────────── */

export interface AdvisoryQueryRequest {
  query: string;
  company_id?: number;
  conversation_id?: number;
}

export interface ProvisionCited {
  provision_id: string;
  title: string;
  relevance: number;
  /** Authority level from the backend citation validator (statutory/guideline/best-practice/company-policy). */
  authority_level?: string;
  /** Company policy ID when source_type is "company_policy". */
  policy_id?: number;
  /** Version of the company policy cited. */
  policy_version?: number;
  /** Distinguishes statutory provisions from company policy provisions. */
  source_type?: "statutory" | "company_policy";
}

export interface AdvisoryQueryResponse {
  query: string;
  response: string;
  provisions_cited: ProvisionCited[];
  risk_tier: string;
  confidence_score: number;
  company_id: number | null;
  conversation_id: number;
  timestamp: string;
}

export interface AdvisoryStreamRequest {
  query: string;
  company_id?: number;
  conversation_id?: number;
}

/** SSE event payloads for advisory streaming */
export interface AdvisoryStreamStartEvent {
  conversation_id: number;
}

export interface AdvisoryStreamTokenEvent {
  token: string;
  index: number;
}

export interface AdvisoryStreamCompleteEvent {
  response: string;
  provisions_cited: ProvisionCited[];
  risk_tier: string;
  confidence_score: number;
  conversation_id: number;
  has_active_onboarding?: boolean;
}

export interface AdvisoryMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  provisions_cited?: ProvisionCited[];
  risk_tier?: string;
  confidence_score?: number;
}

export interface AdvisoryHistoryResponse {
  conversation_id: number;
  messages: AdvisoryMessage[];
  total: number;
}

export interface ConversationListItem {
  id: number;
  title: string;
  last_message: string;
  timestamp: string;
  risk_tier?: string;
  message_count: number;
}

export interface ConversationListResponse {
  conversations: ConversationListItem[];
  total: number;
}

export interface ConversationDeleteResponse {
  conversation_id: number;
  deleted: boolean;
}

export interface ConversationRenameResponse {
  conversation_id: number;
  title: string;
  updated: boolean;
}

/* ── Calculator ──────────────────────────────────────────────── */

export interface CpfCalculationRequest {
  gross_salary: number;
  employee_age: number;
  citizenship_status: string; // "sc", "pr", "ep" (or uppercase "SC", "PR", "foreigner")
  pr_year?: number | null; // Required when citizenship_status is "pr"/"PR" (1, 2, or 3+)
  monthly_aw?: number; // Additional Wages (bonus, etc.) — defaults to 0
  ytd_ow?: number; // Year-to-date Ordinary Wages — defaults to 0
  ytd_aw?: number; // Year-to-date Additional Wages — defaults to 0
}

export interface CpfCalculationResponse {
  employer_contribution: number;
  employee_contribution: number;
  total_contribution: number;
  employer_rate: number;
  employee_rate: number;
  total_rate: number;
  cpf_applicable: boolean;
  cpf_tier: string;
  age_band: string;
  ow_subject_to_cpf: number;
  aw_subject_to_cpf: number;
  ow_capped: boolean;
  aw_capped: boolean;
  allocation_oa: number;
  allocation_sa: number;
  allocation_ma: number;
  breakdown: {
    ow: {
      gross: number;
      subject_to_cpf: number;
      capped: boolean;
      employer_cpf: number;
      employee_cpf: number;
    };
    aw: {
      gross: number;
      subject_to_cpf: number;
      capped: boolean;
      employer_cpf: number;
      employee_cpf: number;
    };
    rates: {
      employer: number;
      employee: number;
      total: number;
    };
    ceilings: {
      ow_ceiling: number;
      aw_ceiling_remaining: number;
    };
  };
  timestamp: string;
}

export interface LeaveCalculationRequest {
  years_of_service: number;
  employment_type: string;
}

export interface LeaveCalculationResponse {
  annual_leave_days: number;
  sick_leave_days: number;
  hospitalisation_leave_days: number;
  notes: string[];
}

export interface SalaryCalculationRequest {
  gross_salary: number;
}

export interface SalaryCalculationResponse {
  gross_salary: number;
  cpf_employee_deduction: number;
  estimated_net_pay: number;
  cpf_employer_contribution: number;
  total_cost_to_employer: number;
  notes: string[];
}

/* ── Compliance ──────────────────────────────────────────────── */

export interface ComplianceCheckRequest {
  company_id: number;
  domains?: string[];
}

export interface ComplianceFinding {
  domain: string;
  status: string;
  provisions_checked: number;
  gaps: number;
  /** Legacy fields — present in some response variants */
  issue?: string;
  severity?: string;
  recommendation?: string;
}

export interface ComplianceCheckResponse {
  company_id: number;
  domains_checked: string[];
  status: string;
  findings: ComplianceFinding[];
  risk_tier: string;
  recommendations: string[];
}

export interface ComplianceDomainStatus {
  status: string;
  provisions_count: number;
}

export interface ComplianceStatusResponse {
  company_id: number;
  overall_status: string;
  last_check: string;
  total_provisions: number;
  domains: Record<string, ComplianceDomainStatus>;
}

/* ── Admin / Metrics ────────────────────────────────────────── */

export interface PlatformMetricsResponse {
  queries_tracked: number;
  avg_confidence: number;
  risk_distribution: Record<string, number>;
  kb_provisions: number;
  kb_acts: number;
  kb_domains: number;
  kb_gaps: number;
  feedback_count: number;
  pending_recommendations: number;
  pending_updates: number;
  published_updates: number;
}

/* ── Admin / Regulatory Updates ──────────────────────────────── */

export type UpdateStatus =
  | "draft"
  | "in_review"
  | "approved"
  | "published"
  | "rejected";

export type UpdateUrgency = "low" | "medium" | "high" | "critical";

export interface RegulatoryUpdateResponse {
  id: string;
  title: string;
  description: string;
  source: string;
  urgency: UpdateUrgency;
  status: UpdateStatus;
  effective_date: string;
  created_at: string;
  reviewed_by: string | null;
  published_at: string | null;
  domains_affected: string[];
  alert_message: string;
  impact_summary: string;
  affected_provisions_count: number;
}

export interface CreateUpdateRequest {
  id: string;
  title: string;
  description: string;
  source: string;
  source_url?: string;
  urgency: string;
  affected_provisions: {
    provision_id: string;
    current_text: string;
    new_text: string;
    change_type: string;
  }[];
  effective_date: string;
  domains_affected?: string[];
  alert_message?: string;
  impact_summary?: string;
}

export interface ReviewRequest {
  reviewer: string;
  notes?: string;
}

/* ── Admin / Staleness ───────────────────────────────────────── */

export interface StalenessSummaryResponse {
  current: number;
  review_soon: number;
  stale: number;
  total: number;
}

/* ── Admin / Learning Pipeline (Gaps, Feedback) ──────────────── */

export interface KbGap {
  gap_id: string;
  domains: string[];
  description: string;
  evidence_query_count: number;
  avg_confidence: number;
  negative_feedback_count: number;
  suggested_provisions: string[];
  priority: string;
  detected_at: string;
}

export interface KbGapsResponse {
  gaps: KbGap[];
  total: number;
}

export interface LearningRecommendation {
  recommendation_id: string;
  type: string;
  title: string;
  description: string;
  priority: string;
  evidence_count: number;
  affected_domains: string[];
  status: string;
  proposed_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

export interface LearningRecommendationsResponse {
  recommendations: LearningRecommendation[];
  total: number;
}

/* ── Learning Pipeline (Admin) ──────────────────────────────── */

export interface QueryPattern {
  pattern_id: string;
  description: string;
  domains: string[];
  frequency: number;
  avg_confidence: number;
  avg_satisfaction: number;
  first_seen: string;
  last_seen: string;
  example_queries: string[];
}

export interface QueryPatternsResponse {
  patterns: QueryPattern[];
  total: number;
}

export interface FeedbackRecord {
  feedback_id: string;
  session_id: string;
  is_positive: boolean;
  category: string | null;
  domains: string[];
  query_snippet: string;
  recorded_at: string;
}

export interface FeedbackSummaryResponse {
  total_feedback: number;
  positive_count: number;
  negative_count: number;
  positive_rate: number;
  category_breakdown: Record<string, number>;
  recent: FeedbackRecord[];
}

export interface MonthlyReportResponse {
  report_id: string;
  period: string;
  total_queries: number;
  total_feedback: number;
  positive_feedback_rate: number;
  kb_gaps_count: number;
  routing_insights_count: number;
  resolution_patterns_count: number;
  recommendations_count: number;
  generated_at: string;
}

export interface ComplianceGapAnalysisRequest {
  company_id: number;
  domains?: string[];
}

export interface ComplianceGap {
  domain: string;
  severity: string;
  provisions_found: number;
  reason: string;
  remediation: string;
}

export interface ComplianceGapAnalysisResponse {
  company_id: number;
  domains_analyzed: string[];
  gaps: ComplianceGap[];
  total_gaps: number;
  critical_gaps: number;
  timestamp: string;
}

/* ── Document ────────────────────────────────────────────────── */

export interface DocumentTemplate {
  id: number;
  name: string;
  description: string;
  category: string;
  template_type: string;
  provisions_count: number;
  required_fields: string[];
  optional_fields: string[];
  compliance_notes: string[];
  /** Only present on detail endpoint */
  content?: string;
  linked_provisions?: string[];
  version?: number;
}

export interface DocumentTemplateListResponse {
  templates: DocumentTemplate[];
  total: number;
}

export interface DocumentGenerateRequest {
  template_id: number;
  company_id?: number;
  fields: Record<string, string>;
}

export interface DocumentGenerateResponse {
  template_id: number;
  company_id: number | null;
  document_id: string;
  document: {
    title: string;
    content: string;
    format: string;
  };
  provisions_applied: string[];
  compliance_notes: string[];
  timestamp: string;
}

export interface DocumentHistoryItem {
  document_id: string;
  title: string;
  template_id: number;
  company_id: number | null;
  timestamp: string;
}

export interface DocumentHistoryResponse {
  documents: DocumentHistoryItem[];
  total: number;
}

/* ── Profile ─────────────────────────────────────────────────── */

/** Backend returns this shape from GET /profile/{company_id} */
export interface CompanyProfile {
  id: number;
  name: string;
  uen: string | null;
  sector: string | null;
  headcount_local: number;
  headcount_pr: number;
  headcount_ep: number;
  headcount_sp: number;
  headcount_wp: number;
  total_headcount: number;
  has_foreign_workers?: boolean;
  profile_completeness_score: number;
  is_active: boolean;
}

export interface CompanyProfileCreateRequest {
  name: string;
  uen?: string;
  sector?: string;
  sub_sector?: string;
  headcount_local?: number;
  headcount_pr?: number;
  headcount_ep?: number;
  headcount_sp?: number;
  headcount_wp?: number;
}

export interface CompanyProfileUpdateRequest {
  name?: string;
  uen?: string;
  sector?: string;
  sub_sector?: string;
  headcount_local?: number;
  headcount_pr?: number;
  headcount_ep?: number;
  headcount_sp?: number;
  headcount_wp?: number;
  is_active?: boolean;
}

export interface CompanyProfileUpdateResponse {
  id: number;
  updated_fields: string[];
  updated: boolean;
  timestamp: string;
}

/** Backend returns this shape from GET /profile/{company_id}/workforce */
export interface WorkforceBreakdown {
  company_id: number;
  workforce: {
    local: number;
    pr: number;
    ep: number;
    sp: number;
    wp: number;
  };
  total: number;
  local_ratio: number;
}

/* ── Knowledge Base ──────────────────────────────────────────── */

export interface Act {
  id: string;
  name: string;
  short_name: string;
  description: string;
  authority_level: string;
}

export interface ActListResponse {
  acts: Act[];
  total: number;
}

export interface Domain {
  id: string;
  name: string;
  description: string;
  act_count: number;
}

export interface DomainListResponse {
  domains: Domain[];
  total: number;
}

export interface Provision {
  id: string;
  title: string;
  content: string;
  act_id: string;
  act_name: string;
  domain: string;
  authority_level: string;
  effective_date: string;
}

/** Extended provision returned by the /kb/provisions/ref/{reference} endpoint. */
export interface ProvisionDetail {
  id: number;
  title: string;
  section: string;
  formal_text: string;
  plain_summary: string;
  source_act_id?: number;
  domain_id?: number;
  authority_level?: string;
  source_url?: string;
  cross_references: CrossReference[];
  applicability_rules: ApplicabilityRule[];
  practical_examples: PracticalExample[];
}

export interface CrossReference {
  id: number;
  source_provision_id: number;
  target_provision_id: number;
  relationship_type: string;
  description: string;
}

export interface ApplicabilityRule {
  id: number;
  provision_id: number;
  rule_type: string;
  description: string;
  conditions: string;
}

export interface PracticalExample {
  id: number;
  provision_id: number;
  scenario: string;
  outcome: string;
  explanation: string;
}

export interface KbQueryRequest {
  query: string;
  domain_id?: string;
}

export interface KbQueryResult {
  provision_id: string;
  title: string;
  content: string;
  relevance: number;
  act_name: string;
  domain: string;
}

export interface KbQueryResponse {
  query: string;
  results: KbQueryResult[];
}

/* ── Search ──────────────────────────────────────────────────── */

export interface SemanticSearchRequest {
  query: string;
  top_k?: number;
  domain_id?: string;
  threshold?: number;
}

export interface SearchResult {
  provision_id: string;
  title: string;
  content: string;
  relevance: number;
  act_name: string;
  domain: string;
  authority_level: string;
}

export interface SemanticSearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface FulltextSearchRequest {
  query: string;
  domain_id?: string;
  act_id?: string;
  authority_level?: string;
  page?: number;
  page_size?: number;
}

export interface FulltextSearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  page: number;
  page_size: number;
}

/* ── Clients (multi-tenant consultant view) ──────────────────── */

export interface ClientCompany {
  id: number;
  name: string;
  uen: string;
  sector: string;
  employee_count: number;
  compliance_score: number | null;
  risk_tier: string | null;
  last_activity: string | null;
  created_at: string;
}

export interface ClientListResponse {
  clients: ClientCompany[];
  total: number;
}

export interface ClientCreateRequest {
  name: string;
  uen: string;
  sector: string;
  employee_count: number;
}

/* ── Alerts ──────────────────────────────────────────────────── */

export type AlertSeverity = "critical" | "high" | "medium" | "low";
export type AlertStatus = "unread" | "read" | "dismissed";

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  status: AlertStatus;
  domain: string;
  created_at: string;
  impact_summary: string;
  actions: string[];
  effective_date: string;
  source: string;
}

export interface AlertListResponse {
  alerts: Alert[];
  total: number;
  unread_count: number;
}

export interface AlertUnreadCountResponse {
  unread_count: number;
}

/* ── Emergency ──────────────────────────────────────────────── */

export interface EmergencyStep {
  step_number: number;
  action: string;
  deadline: string;
  detail: string;
}

export interface EmergencyScenario {
  topic_id: string;
  title: string;
  icon: string;
  description: string;
  immediate_obligations: EmergencyStep[];
  documents_needed: string[];
  process_steps: EmergencyStep[];
  when_to_get_help: string[];
  key_provisions: string[];
}

export interface EmergencyScenarioListResponse {
  scenarios: EmergencyScenario[];
  total: number;
}

export interface EscalationRequest {
  topic_id: string;
  description: string;
  company_name?: string;
  contact_email?: string;
  contact_phone?: string;
  urgency?: string;
}

export interface EscalationResponse {
  escalation_id: string;
  topic_id: string;
  status: string;
  message: string;
}

/* ── Advisory Escalation (chat-originated) ──────────────────── */

export type EscalationUrgency = "urgent" | "within-24h" | "general-enquiry";
export type EscalationContactMethod = "email" | "phone";

export interface AdvisoryEscalationRequest {
  situation: string;
  urgency: EscalationUrgency;
  contact_method: EscalationContactMethod;
  contact_value: string;
}

export interface AdvisoryEscalationResponse {
  escalation_id: string;
  status: string;
  message: string;
  expected_response_time: string;
}

/* ── QA Sessions ────────────────────────────────────────────── */

export type QASessionStatus = "active" | "completed";

export type QASamplingStrategy =
  | "random"
  | "lowest-confidence"
  | "flagged-first"
  | "recent-first";

export type QARiskTierFilter = "all" | "green" | "amber" | "red";

export interface QASessionFilters {
  date_from?: string;
  date_to?: string;
  risk_tier?: QARiskTierFilter;
  domain?: string;
  flagged_only?: boolean;
  confidence_min?: number;
  confidence_max?: number;
  sampling_strategy?: QASamplingStrategy;
}

export interface CreateQASessionRequest {
  filters: QASessionFilters;
}

export interface QADimensionScore {
  dimension: string;
  average_score: number;
}

export interface QAFailureCategory {
  category: string;
  count: number;
}

export interface QASession {
  id: string;
  reviewer_name: string;
  status: QASessionStatus;
  conversation_count: number;
  created_at: string;
  completed_at: string | null;
  average_overall_score: number | null;
  dimension_scores: QADimensionScore[] | null;
  failure_categories: QAFailureCategory[] | null;
  filters: QASessionFilters;
}

export interface QASessionListResponse {
  sessions: QASession[];
  total: number;
}

export interface QASessionConversation {
  conversation_id: number;
  query_snippet: string;
  risk_tier: string;
  confidence_score: number;
  overall_score: number | null;
  reviewed: boolean;
  flagged: boolean;
}

export interface QASessionConversationsResponse {
  conversations: QASessionConversation[];
  total: number;
}

/* ── QA Evaluations ────────────────────────────────────────────── */

export type CitationFlagStatus = "correct" | "incorrect" | "missing";

export interface CitationFlag {
  provision_id: string;
  status: CitationFlagStatus;
}

export type QAFailureCategoryValue =
  | "wrong_law_cited"
  | "correct_law_wrong_interpretation"
  | "missed_critical_nuance"
  | "ignored_company_context"
  | "lost_conversation_context"
  | "overly_generic"
  | "wrong_domain_routing"
  | "fabricated_citation"
  | "other";

export type QAAffectedAgent =
  | "employment_act_specialist"
  | "cpf_specialist"
  | "foreign_manpower_specialist"
  | "fair_employment_specialist"
  | "tax_specialist"
  | "wsh_specialist"
  | "pdpa_specialist"
  | "query_analyzer"
  | "orchestrator"
  | "response_synthesizer";

export interface SubmitEvaluationRequest {
  session_id: number;
  conversation_id: string;
  turn_number: number;
  score_legal_accuracy: number;
  score_contextual_relevance: number;
  score_coherence: number;
  score_actionability: number;
  score_risk_awareness: number;
  score_citation_quality: number;
  score_language: number;
  score_completeness: number;
  citation_flags?: CitationFlag[] | null;
  has_material_correction: boolean;
  correction_text?: string | null;
  failure_category?: QAFailureCategoryValue | null;
  affected_agent?: QAAffectedAgent | null;
}

export interface QAEvaluation {
  id: number;
  session_id: number;
  conversation_id: string;
  turn_number: number;
  score_legal_accuracy: number;
  score_contextual_relevance: number;
  score_coherence: number;
  score_actionability: number;
  score_risk_awareness: number;
  score_citation_quality: number;
  score_language: number;
  score_completeness: number;
  citation_flags: CitationFlag[] | null;
  has_material_correction: boolean;
  correction_text: string | null;
  failure_category: QAFailureCategoryValue | null;
  affected_agent: QAAffectedAgent | null;
  created_at: string;
}

export interface QAEvaluationListResponse {
  evaluations: QAEvaluation[];
  total: number;
}

/* ── QA Patches ────────────────────────────────────────────────── */

export type QAPatchStatus = "proposed" | "approved" | "rejected" | "deployed";

export interface QAPatch {
  id: number;
  affected_agent: string;
  failure_category: string;
  current_instruction: string;
  proposed_instruction: string;
  rationale: string;
  status: QAPatchStatus;
  evidence_count: number;
  created_at: string;
  approved_at: string | null;
  approved_by: string | null;
}

export interface QAPatchListResponse {
  patches: QAPatch[];
  total: number;
}

/* ── Help ────────────────────────────────────────────────────── */

export interface HelpArticle {
  id: string;
  title: string;
  content: string;
  category: string;
  order: number;
}

export interface HelpArticleListResponse {
  articles: HelpArticle[];
  total: number;
  categories: string[];
}

export interface GettingStartedStep {
  step_number: number;
  title: string;
  description: string;
  action_label: string;
  action_path: string;
}

export interface GettingStartedResponse {
  title: string;
  introduction: string;
  steps: GettingStartedStep[];
}
