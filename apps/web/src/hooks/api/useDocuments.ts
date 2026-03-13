/* ── Document Hooks ───────────────────────────────────────── */

"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { documentsApi } from "@/services/api/documents";
import type {
  DocumentTemplate,
  DocumentTemplateListResponse,
  DocumentGenerateRequest,
  DocumentGenerateResponse,
} from "@/types/api";

/** Query keys for document domain. */
export const documentKeys = {
  all: ["documents"] as const,
  templates: () => [...documentKeys.all, "templates"] as const,
  template: (templateId: string) =>
    [...documentKeys.all, "template", templateId] as const,
};

/**
 * Fetch all document templates.
 */
export function useDocumentTemplates() {
  return useQuery<DocumentTemplateListResponse, Error>({
    queryKey: documentKeys.templates(),
    queryFn: () => documentsApi.listTemplates(),
  });
}

/**
 * Fetch a single document template by ID.
 * Only fetches when templateId is provided.
 */
export function useDocumentTemplate(templateId: string) {
  return useQuery<DocumentTemplate, Error>({
    queryKey: documentKeys.template(templateId),
    queryFn: () => documentsApi.getTemplate(Number(templateId)),
    enabled: !!templateId,
  });
}

/**
 * Generate a document from a template.
 */
export function useDocumentGenerate() {
  return useMutation<DocumentGenerateResponse, Error, DocumentGenerateRequest>({
    mutationFn: (data) => documentsApi.generate(data),
  });
}
