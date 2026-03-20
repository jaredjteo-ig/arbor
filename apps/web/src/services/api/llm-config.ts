/* ── LLM Configuration API Service ─────────────────────────── */

import { apiClient } from "./client";

/* ── Types ────────────────────────────────────────────────── */

export type LLMProvider =
  | "openai"
  | "anthropic"
  | "gemini"
  | "deepseek"
  | "mistral"
  | "ollama"
  | "custom";

export interface LLMConfig {
  id: number;
  company_id: number;
  provider: LLMProvider;
  has_key: boolean;
  masked_key: string;
  model_pref: string | null;
  base_url: string | null;
  status: "active" | "invalid" | "revoked";
  updated_by: number | null;
  updated_at: string;
}

export interface LLMUsage {
  company_id: number;
  month: string;
  query_count: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  budget: {
    allowed: boolean;
    remaining_usd: number;
    warning: boolean;
    used_usd: number;
    limit_usd: number;
  };
}

export interface SaveLLMConfigRequest {
  provider: LLMProvider;
  api_key?: string;
  model_pref?: string;
  base_url?: string;
}

export interface ValidateLLMConfigRequest {
  provider: LLMProvider;
  api_key?: string;
  base_url?: string;
  model_pref?: string;
}

export interface ValidationResult {
  valid: boolean;
  message?: string;
  provider_info?: { models?: string[] };
}

/* ── API Methods ─────────────────────────────────────────── */

export const llmConfigApi = {
  /** Get company's active LLM configuration (unwraps backend envelope). */
  async get(companyId: number): Promise<LLMConfig | null> {
    const resp = await apiClient.get<{
      config: LLMConfig | null;
      source: string;
    }>(`/companies/${companyId}/llm-config`);
    return resp.config ?? null;
  },

  /** Save or update company LLM configuration (unwraps backend envelope). */
  async save(
    companyId: number,
    data: SaveLLMConfigRequest,
  ): Promise<LLMConfig> {
    const resp = await apiClient.post<{ config: LLMConfig; message: string }>(
      `/companies/${companyId}/llm-config`,
      data,
    );
    return resp.config;
  },

  /** Delete company LLM configuration. */
  delete(companyId: number): Promise<void> {
    return apiClient.delete(`/companies/${companyId}/llm-config`);
  },

  /** Validate an API key or endpoint before saving. */
  validate(
    companyId: number,
    data: ValidateLLMConfigRequest,
  ): Promise<ValidationResult> {
    return apiClient.post<ValidationResult>(
      `/companies/${companyId}/llm-config/validate`,
      data,
    );
  },

  /** Get current month's LLM usage and budget status. */
  getUsage(companyId: number): Promise<LLMUsage> {
    return apiClient.get<LLMUsage>(`/companies/${companyId}/llm-usage`);
  },
};
