/* ── SessionSummary Tests ─────────────────────────────────── */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SessionSummary } from "../SessionSummary";
import type { QASession } from "@/types/api";

/* ── Helpers ──────────────────────────────────────────────── */

function makeSession(overrides: Partial<QASession> = {}): QASession {
  return {
    id: "s1",
    reviewer_name: "Alice",
    status: "completed",
    conversation_count: 10,
    created_at: "2026-03-10T00:00:00Z",
    completed_at: "2026-03-12T00:00:00Z",
    average_overall_score: 4.2,
    dimension_scores: [
      { dimension: "Legal Accuracy", average_score: 4.5 },
      { dimension: "Coherence", average_score: 3.8 },
      { dimension: "Actionability", average_score: 4.0 },
    ],
    failure_categories: [
      { category: "Missing citation", count: 3 },
      { category: "Incorrect jurisdiction", count: 1 },
    ],
    filters: {},
    ...overrides,
  };
}

/* ── Tests ────────────────────────────────────────────────── */

describe("SessionSummary", () => {
  it("renders the back button", () => {
    render(<SessionSummary session={makeSession()} onClose={vi.fn()} />);

    expect(screen.getByText("Back to sessions list")).toBeInTheDocument();
  });

  it("calls onClose when back button is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    render(<SessionSummary session={makeSession()} onClose={onClose} />);

    await user.click(screen.getByText("Back to sessions list"));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("displays the session scorecard header", () => {
    render(<SessionSummary session={makeSession()} onClose={vi.fn()} />);

    expect(screen.getByText("Session Scorecard")).toBeInTheDocument();
  });

  it("shows the reviewer name and conversation count", () => {
    render(
      <SessionSummary
        session={makeSession({
          reviewer_name: "Bob",
          conversation_count: 15,
        })}
        onClose={vi.fn()}
      />,
    );

    const meta = screen.getByText(/Reviewed by Bob/);
    expect(meta).toBeInTheDocument();
    expect(meta.textContent).toContain("15 conversations");
  });

  it("shows the overall score badge", () => {
    render(
      <SessionSummary
        session={makeSession({ average_overall_score: 4.2 })}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText(/Overall: 4\.2 \/ 5/)).toBeInTheDocument();
  });

  it("renders per-dimension score bars", () => {
    render(<SessionSummary session={makeSession()} onClose={vi.fn()} />);

    expect(screen.getByText("Per-Dimension Scores")).toBeInTheDocument();
    expect(screen.getByText("Legal Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Coherence")).toBeInTheDocument();
    expect(screen.getByText("Actionability")).toBeInTheDocument();

    // Check formatted scores
    expect(screen.getByText("4.5 / 5")).toBeInTheDocument();
    expect(screen.getByText("3.8 / 5")).toBeInTheDocument();
    expect(screen.getByText("4.0 / 5")).toBeInTheDocument();
  });

  it("renders failure category breakdown", () => {
    render(<SessionSummary session={makeSession()} onClose={vi.fn()} />);

    expect(screen.getByText("Failure Categories")).toBeInTheDocument();
    expect(screen.getByText("Missing citation")).toBeInTheDocument();
    expect(screen.getByText("Incorrect jurisdiction")).toBeInTheDocument();

    // Total failures shown (3 + 1 = 4)
    expect(screen.getByText(/4 total failures/)).toBeInTheDocument();
  });

  it("shows empty state when no scores or failures exist", () => {
    render(
      <SessionSummary
        session={makeSession({
          dimension_scores: [],
          failure_categories: [],
        })}
        onClose={vi.fn()}
      />,
    );

    expect(
      screen.getByText("No scoring data available for this session."),
    ).toBeInTheDocument();
  });

  it("handles null dimension_scores and failure_categories gracefully", () => {
    render(
      <SessionSummary
        session={makeSession({
          dimension_scores: null,
          failure_categories: null,
        })}
        onClose={vi.fn()}
      />,
    );

    expect(
      screen.getByText("No scoring data available for this session."),
    ).toBeInTheDocument();
  });
});
