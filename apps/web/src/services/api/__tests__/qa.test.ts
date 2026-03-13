/* ── QA API Service Tests ─────────────────────────────────── */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { qaApi } from "../qa";
import { apiClient } from "../client";

vi.mock("../client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockGet = vi.mocked(apiClient.get);
const mockPost = vi.mocked(apiClient.post);

beforeEach(() => {
  vi.clearAllMocks();
});

/* ── Sessions ────────────────────────────────────────────── */

describe("qaApi.createSession", () => {
  it("posts to /admin/qa/sessions with the request body", async () => {
    const body = { filters: { sampling_strategy: "random" as const } };
    const response = { id: "s1", status: "active" };
    mockPost.mockResolvedValueOnce(response);

    const result = await qaApi.createSession(body);

    expect(mockPost).toHaveBeenCalledWith("/admin/qa/sessions", body);
    expect(result).toEqual(response);
  });
});

describe("qaApi.listSessions", () => {
  it("gets /admin/qa/sessions with no params when none provided", async () => {
    const response = { sessions: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    const result = await qaApi.listSessions();

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/sessions", {});
    expect(result).toEqual(response);
  });

  it("passes status, page, and page_size as query params", async () => {
    const response = { sessions: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    await qaApi.listSessions("active", 2, 20);

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/sessions", {
      status: "active",
      page: "2",
      page_size: "20",
    });
  });
});

describe("qaApi.getSession", () => {
  it("gets /admin/qa/sessions/{id}", async () => {
    const session = { id: "s1", status: "active" };
    mockGet.mockResolvedValueOnce(session);

    const result = await qaApi.getSession("s1");

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/sessions/s1");
    expect(result).toEqual(session);
  });
});

describe("qaApi.getSessionConversations", () => {
  it("gets /admin/qa/sessions/{id}/conversations", async () => {
    const response = { conversations: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    const result = await qaApi.getSessionConversations("s1");

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/sessions/s1/conversations");
    expect(result).toEqual(response);
  });
});

/* ── Evaluations ─────────────────────────────────────────── */

describe("qaApi.submitEvaluation", () => {
  it("posts to /admin/qa/evaluations with the evaluation data", async () => {
    const body = {
      session_id: 1,
      conversation_id: "c1",
      turn_number: 0,
      score_legal_accuracy: 4.5,
      score_contextual_relevance: 4.0,
      score_coherence: 3.5,
      score_actionability: 4.0,
      score_risk_awareness: 4.5,
      score_citation_quality: 3.0,
      score_language: 4.0,
      score_completeness: 3.5,
      has_material_correction: false,
    };
    const response = { id: 1, ...body, created_at: "2026-03-13T00:00:00Z" };
    mockPost.mockResolvedValueOnce(response);

    const result = await qaApi.submitEvaluation(body);

    expect(mockPost).toHaveBeenCalledWith("/admin/qa/evaluations", body);
    expect(result).toEqual(response);
  });
});

describe("qaApi.listEvaluations", () => {
  it("gets /admin/qa/evaluations with no params when none provided", async () => {
    const response = { evaluations: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    const result = await qaApi.listEvaluations();

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/evaluations", {});
    expect(result).toEqual(response);
  });

  it("passes session_id as query param", async () => {
    const response = { evaluations: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    await qaApi.listEvaluations(5);

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/evaluations", {
      session_id: "5",
    });
  });
});

/* ── Patches ─────────────────────────────────────────────── */

describe("qaApi.listPatches", () => {
  it("gets /admin/qa/patches with no params when none provided", async () => {
    const response = { patches: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    const result = await qaApi.listPatches();

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/patches", {});
    expect(result).toEqual(response);
  });

  it("passes status as query param", async () => {
    const response = { patches: [], total: 0 };
    mockGet.mockResolvedValueOnce(response);

    await qaApi.listPatches("proposed");

    expect(mockGet).toHaveBeenCalledWith("/admin/qa/patches", {
      status: "proposed",
    });
  });
});

describe("qaApi.approvePatch", () => {
  it("posts to /admin/qa/patches/{id}/approve", async () => {
    const response = { id: 1, status: "approved" };
    mockPost.mockResolvedValueOnce(response);

    const result = await qaApi.approvePatch(1);

    expect(mockPost).toHaveBeenCalledWith("/admin/qa/patches/1/approve");
    expect(result).toEqual(response);
  });
});

describe("qaApi.rejectPatch", () => {
  it("posts to /admin/qa/patches/{id}/reject", async () => {
    const response = { id: 1, status: "rejected" };
    mockPost.mockResolvedValueOnce(response);

    const result = await qaApi.rejectPatch(1);

    expect(mockPost).toHaveBeenCalledWith("/admin/qa/patches/1/reject");
    expect(result).toEqual(response);
  });
});
