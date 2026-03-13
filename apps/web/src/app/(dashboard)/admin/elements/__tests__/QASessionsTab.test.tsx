/* ── QASessionsTab Tests ──────────────────────────────────── */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { QASessionsTab } from "../QASessionsTab";
import type { QASession, QASessionListResponse } from "@/types/api";

/* ── Mock the hook ────────────────────────────────────────── */

const mockUseQaSessions = vi.fn();
const mockUseCreateQaSession = vi.fn();

vi.mock("@/hooks/api/useQa", () => ({
  useQaSessions: (...args: unknown[]) => mockUseQaSessions(...args),
  useCreateQaSession: () => mockUseCreateQaSession(),
}));

/* ── Helpers ──────────────────────────────────────────────── */

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderWithClient(ui: React.ReactElement) {
  const client = createQueryClient();
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function makeSession(overrides: Partial<QASession> = {}): QASession {
  return {
    id: "s1",
    reviewer_name: "Alice",
    status: "active",
    conversation_count: 5,
    created_at: "2026-03-10T00:00:00Z",
    completed_at: null,
    average_overall_score: null,
    dimension_scores: null,
    failure_categories: null,
    filters: {},
    ...overrides,
  };
}

/* ── Tests ────────────────────────────────────────────────── */

beforeEach(() => {
  vi.clearAllMocks();
  mockUseCreateQaSession.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  });
});

describe("QASessionsTab", () => {
  it("shows a loading skeleton while data is fetching", () => {
    mockUseQaSessions.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    // Skeleton uses animate-pulse class
    const skeleton = document.querySelector(".animate-pulse");
    expect(skeleton).toBeTruthy();
  });

  it("shows an error message when the query fails", () => {
    mockUseQaSessions.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network failure"),
    });

    renderWithClient(<QASessionsTab />);

    expect(screen.getByText("Failed to load QA sessions")).toBeInTheDocument();
    expect(screen.getByText("Network failure")).toBeInTheDocument();
  });

  it("shows the empty state when there are no sessions", () => {
    mockUseQaSessions.mockReturnValue({
      data: { sessions: [], total: 0 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    expect(screen.getByText("No QA sessions yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Start a new session to begin reviewing conversation quality.",
      ),
    ).toBeInTheDocument();
  });

  it("renders session rows with correct data", () => {
    const sessions: QASession[] = [
      makeSession({ id: "s1", reviewer_name: "Alice", status: "active" }),
      makeSession({
        id: "s2",
        reviewer_name: "Bob",
        status: "completed",
        completed_at: "2026-03-12T00:00:00Z",
        average_overall_score: 4.2,
        conversation_count: 10,
      }),
    ];

    mockUseQaSessions.mockReturnValue({
      data: { sessions, total: 2 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    // Both reviewer names visible
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();

    // Status badges (use getAllByText for "Completed" since it also appears as a column header)
    expect(screen.getByText("Active")).toBeInTheDocument();
    const completedElements = screen.getAllByText("Completed");
    // At least one should be the badge (span), and one is the table header (th)
    expect(completedElements.length).toBeGreaterThanOrEqual(2);

    // Average score for completed session
    expect(screen.getByText("4.2")).toBeInTheDocument();

    // Total sessions count
    expect(screen.getByText("2 sessions total")).toBeInTheDocument();
  });

  it("shows 'Start New Session' button", () => {
    mockUseQaSessions.mockReturnValue({
      data: { sessions: [], total: 0 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    // There are two Start New Session buttons (header + empty state)
    const buttons = screen.getAllByText("Start New Session");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
  });

  it("renders 'View' link for completed sessions only", () => {
    const sessions: QASession[] = [
      makeSession({ id: "s1", status: "active" }),
      makeSession({
        id: "s2",
        status: "completed",
        completed_at: "2026-03-12T00:00:00Z",
        average_overall_score: 3.8,
      }),
    ];

    mockUseQaSessions.mockReturnValue({
      data: { sessions, total: 2 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    // Only one "View" link -- for the completed session
    const viewLinks = screen.getAllByText("View");
    expect(viewLinks).toHaveLength(1);
  });

  it("sorts active sessions before completed ones", () => {
    const sessions: QASession[] = [
      makeSession({
        id: "s1",
        reviewer_name: "Completed-First",
        status: "completed",
        completed_at: "2026-03-12T00:00:00Z",
        average_overall_score: 4.0,
        created_at: "2026-03-11T00:00:00Z",
      }),
      makeSession({
        id: "s2",
        reviewer_name: "Active-Second",
        status: "active",
        created_at: "2026-03-10T00:00:00Z",
      }),
    ];

    mockUseQaSessions.mockReturnValue({
      data: { sessions, total: 2 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    const rows = screen.getAllByRole("row");
    // First data row (index 1 after header) should be the active session
    const firstDataRow = rows[1];
    expect(firstDataRow.textContent).toContain("Active-Second");
  });

  it("navigates to session summary when 'View' is clicked", async () => {
    const user = userEvent.setup();
    const sessions: QASession[] = [
      makeSession({
        id: "s2",
        reviewer_name: "Bob",
        status: "completed",
        completed_at: "2026-03-12T00:00:00Z",
        average_overall_score: 4.2,
        conversation_count: 10,
        dimension_scores: [{ dimension: "Legal Accuracy", average_score: 4.5 }],
        failure_categories: [],
      }),
    ];

    mockUseQaSessions.mockReturnValue({
      data: { sessions, total: 1 } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    const viewLink = screen.getByText("View");
    await user.click(viewLink);

    // After clicking, the SessionSummary should render
    expect(screen.getByText("Session Scorecard")).toBeInTheDocument();
    expect(screen.getByText("Back to sessions list")).toBeInTheDocument();
  });

  it("does not show pagination when there is only one page", () => {
    mockUseQaSessions.mockReturnValue({
      data: {
        sessions: [makeSession()],
        total: 1,
      } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    expect(screen.queryByText(/Page \d+ of/)).not.toBeInTheDocument();
  });

  it("shows pagination controls when total exceeds page size", () => {
    mockUseQaSessions.mockReturnValue({
      data: {
        sessions: Array.from({ length: 10 }, (_, i) =>
          makeSession({ id: `s${i}`, reviewer_name: `Reviewer ${i}` }),
        ),
        total: 25,
      } satisfies QASessionListResponse,
      isLoading: false,
      error: null,
    });

    renderWithClient(<QASessionsTab />);

    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    expect(screen.getByLabelText("Previous page")).toBeDisabled();
    expect(screen.getByLabelText("Next page")).not.toBeDisabled();
  });
});
