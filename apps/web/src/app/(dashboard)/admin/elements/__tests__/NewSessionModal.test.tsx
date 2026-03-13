/* ── NewSessionModal Tests ────────────────────────────────── */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NewSessionModal } from "../NewSessionModal";

/* ── Mock the hook ────────────────────────────────────────── */

const mockMutate = vi.fn();
const mockUseCreateQaSession = vi.fn();

vi.mock("@/hooks/api/useQa", () => ({
  useCreateQaSession: () => mockUseCreateQaSession(),
}));

/* ── Helpers ──────────────────────────────────────────────── */

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function renderModal(open: boolean, onClose = vi.fn()) {
  const client = createQueryClient();
  return {
    onClose,
    ...render(
      <QueryClientProvider client={client}>
        <NewSessionModal open={open} onClose={onClose} />
      </QueryClientProvider>,
    ),
  };
}

/* ── Tests ────────────────────────────────────────────────── */

beforeEach(() => {
  vi.clearAllMocks();
  mockUseCreateQaSession.mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isError: false,
    error: null,
  });
});

describe("NewSessionModal", () => {
  it("renders nothing when open is false", () => {
    renderModal(false);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders the modal dialog when open is true", () => {
    renderModal(true);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Start New QA Session")).toBeInTheDocument();
  });

  it("renders all form fields", () => {
    renderModal(true);

    // Date range
    expect(screen.getByText("Date from")).toBeInTheDocument();
    expect(screen.getByText("Date to")).toBeInTheDocument();

    // Selects
    expect(screen.getByText("Risk tier")).toBeInTheDocument();
    expect(screen.getByText("Domain")).toBeInTheDocument();
    expect(screen.getByText("Sampling strategy")).toBeInTheDocument();

    // Flagged toggle
    expect(screen.getByText("Flagged conversations only")).toBeInTheDocument();

    // Confidence range
    expect(screen.getByText("Confidence range")).toBeInTheDocument();
  });

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal(true);

    await user.click(screen.getByText("Cancel"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls onClose when the X button is clicked", async () => {
    const user = userEvent.setup();
    const { onClose } = renderModal(true);

    await user.click(screen.getByLabelText("Close modal"));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("calls createSession.mutate when Start Session is clicked", async () => {
    const user = userEvent.setup();
    renderModal(true);

    await user.click(screen.getByText("Start Session"));

    expect(mockMutate).toHaveBeenCalledOnce();
    // Check that the first argument contains filters with sampling_strategy
    const callArgs = mockMutate.mock.calls[0];
    expect(callArgs[0]).toHaveProperty("filters");
    expect(callArgs[0].filters).toHaveProperty("sampling_strategy", "random");
  });

  it("shows loading state when mutation is pending", () => {
    mockUseCreateQaSession.mockReturnValue({
      mutate: mockMutate,
      isPending: true,
      isError: false,
      error: null,
    });

    renderModal(true);

    const startBtn = screen.getByText("Start Session").closest("button");
    expect(startBtn).toBeDisabled();
  });

  it("shows error message when mutation fails", () => {
    mockUseCreateQaSession.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: true,
      error: new Error("Failed to create session"),
    });

    renderModal(true);

    expect(screen.getByText("Failed to create session")).toBeInTheDocument();
  });

  it("toggles flagged-only checkbox", async () => {
    const user = userEvent.setup();
    renderModal(true);

    const checkbox = screen.getByRole("checkbox");
    expect(checkbox).not.toBeChecked();

    await user.click(checkbox);
    expect(checkbox).toBeChecked();
  });
});
