/* ── Document API Service ─────────────────────────────────── */

import { apiClient } from "./client";
import type {
  DocumentTemplate,
  DocumentTemplateListResponse,
  DocumentGenerateRequest,
  DocumentGenerateResponse,
  DocumentHistoryResponse,
} from "@/types/api";

export const documentsApi = {
  /** List all available document templates, optionally filtered by category. */
  listTemplates(category?: string): Promise<DocumentTemplateListResponse> {
    const params: Record<string, string> = {};
    if (category) params.category = category;
    return apiClient.get<DocumentTemplateListResponse>(
      "/document/templates",
      Object.keys(params).length > 0 ? params : undefined,
    );
  },

  /** Get a specific document template by ID (includes full content). */
  getTemplate(templateId: number): Promise<DocumentTemplate> {
    return apiClient.get<DocumentTemplate>(`/document/templates/${templateId}`);
  },

  /** Resolve a template slug to a policy-modal prefill payload.
   *
   * Red-team P5-VL-2: compliance Action Items deep-link via
   * /policies?template=<slug>. This endpoint returns
   *   { title, category, content, found_template, known_slug, linked_provisions }
   * tailored for the Add Policy modal. Always 200 — unknown slugs
   * yield an empty payload so the modal opens cleanly.
   */
  getTemplatePrefillBySlug(slug: string): Promise<{
    slug: string;
    found_template: boolean;
    known_slug: boolean;
    title: string;
    category: string;
    content: string;
    linked_provisions: string[];
  }> {
    return apiClient.get<{
      slug: string;
      found_template: boolean;
      known_slug: boolean;
      title: string;
      category: string;
      content: string;
      linked_provisions: string[];
    }>(`/document/templates/by-slug/${encodeURIComponent(slug)}`);
  },

  /** Generate a document from a template with field values. */
  generate(data: DocumentGenerateRequest): Promise<DocumentGenerateResponse> {
    return apiClient.post<DocumentGenerateResponse>("/document/generate", data);
  },

  /** List previously generated documents, optionally scoped to a company. */
  history(companyId?: number): Promise<DocumentHistoryResponse> {
    const params: Record<string, string> = {};
    if (companyId) params.company_id = String(companyId);
    return apiClient.get<DocumentHistoryResponse>(
      "/document/history",
      Object.keys(params).length > 0 ? params : undefined,
    );
  },

  /** Download a previously generated document by ID. Returns the URL for download. */
  downloadUrl(documentId: string, format: "pdf" | "txt" = "pdf"): string {
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${base}/document/download/${documentId}?format=${format}`;
  },
};
