import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const decision = (id, agent, status, extra = {}) => ({
  decision_id: id, agent_id: agent, reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
  decision_timestamp: "2026-10-13T15:10:00", status, confirmed_by: status === "confirmed" ? "ADM_COMPLIANCE_01" : null,
  notes: `Notes for ${agent}`, ...extra,
});

const DECISIONS = [
  decision("RD1", "A10001", "pending_confirmation"),
  decision("RD2", "A20002", "pending_confirmation", { decision_outcome: "legitimate", reviewer_id: "ADM_COMPLIANCE_01" }),
  decision("RD3", "A30003", "confirmed"),
];

function routes(role = "compliance_officer", extra = {}) {
  return { ...sessionRoutes(role), "GET /api/review-decisions": { count: 3, decisions: DECISIONS }, ...extra };
}

const queue = () => screen.findByRole("table", { name: "Decisions waiting for confirmation" });

describe("Confirm queue", () => {
  it("lists only proposed decisions with agent, proposer, outcome, notes and date", async () => {
    mockApi(routes());
    renderApp("/review/confirm");
    const table = await queue();
    expect(within(table).getByRole("link", { name: "A10001" })).toHaveAttribute("href", "/agents/A10001");
    expect(within(table).getByText("A20002")).toBeInTheDocument();
    expect(within(table).queryByText("A30003")).not.toBeInTheDocument();
    expect(within(table).getByText("Notes for A10001")).toBeInTheDocument();
    expect(within(table).getAllByText("ADM_ANALYST_01")).toHaveLength(1);
    expect(within(table).getByText("Legitimate")).toBeInTheDocument();
    expect(document.title).toBe("Confirm queue · SalesMesh Fraud Detection");
  });

  it("confirms after the dialog, then removes the row and says it is final", async () => {
    const { calls } = mockApi(routes("compliance_officer", {
      "POST /api/review-decisions/RD1/confirm": { message: "Review decision confirmed", decision_id: "RD1", status: "confirmed", confirmed_by: "ADM_COMPLIANCE_02" },
    }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Confirm the decision for A10001" }));

    const dialog = screen.getByRole("dialog", { name: "Confirm this decision?" });
    expect(within(dialog).getByText("Notes for A10001")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Confirm decision" }));

    expect(await screen.findByText("Decision for A10001 confirmed. It is now final.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(table).queryByText("A10001")).not.toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST").path).toBe("/api/review-decisions/RD1/confirm");
  });

  it("keeps the row and explains the error when you try to confirm your own proposal", async () => {
    mockApi(routes("compliance_officer", {
      "POST /api/review-decisions/RD2/confirm": reply(403, { error: "A decision cannot be confirmed by the admin who proposed it" }),
    }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Confirm the decision for A20002" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    const alert = await within(screen.getByRole("dialog")).findByRole("alert");
    expect(alert).toHaveTextContent("A decision cannot be confirmed by the admin who proposed it. Another compliance officer must confirm it.");
    // A refused confirmation does not sign the user out or hide the page.
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(within(table).getByText("A20002")).toBeInTheDocument();
  });

  it("drops a decision someone else confirmed first", async () => {
    mockApi(routes("compliance_officer", { "POST /api/review-decisions/RD1/confirm": reply(409, { error: "Decision is already confirmed" }) }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Confirm the decision for A10001" }));
    await userEvent.click(screen.getByRole("button", { name: "Confirm decision" }));
    expect(await screen.findByText(/already confirmed by someone else/)).toBeInTheDocument();
    expect(within(table).queryByText("A10001")).not.toBeInTheDocument();
  });

  it("cancel closes the dialog without a request", async () => {
    const { calls } = mockApi(routes());
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Confirm the decision for A10001" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("shows an empty state when nothing is waiting", async () => {
    mockApi(routes("compliance_officer", { "GET /api/review-decisions": { count: 1, decisions: [DECISIONS[2]] } }));
    renderApp("/review/confirm");
    expect(await screen.findByText("No decisions are waiting for confirmation.")).toBeInTheDocument();
  });

  it("shows an error state with retry", async () => {
    mockApi(routes("compliance_officer", { "GET /api/review-decisions": reply(500, { error: "Database unavailable" }) }));
    renderApp("/review/confirm");
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it.each(["fraud_analyst", "admin"])("sends a %s to the access denied page", async (role) => {
    mockApi(routes(role));
    renderApp("/review/confirm");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });

  it("shows confirm buttons on cards on narrow screens", async () => {
    window.innerWidth = 360;
    mockApi(routes());
    renderApp("/review/confirm");
    const list = await screen.findByRole("region", { name: "Decisions waiting for confirmation" });
    expect(within(list).getByRole("button", { name: "Confirm the decision for A10001" })).toBeInTheDocument();
  });
});
