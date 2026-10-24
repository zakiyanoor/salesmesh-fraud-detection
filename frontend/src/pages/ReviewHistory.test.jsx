import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";

const DECISIONS = [
  {
    decision_id: "RD1", agent_id: "A10001", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
    decision_timestamp: "2026-10-13T15:10:00", status: "pending_confirmation", closed_by: null, final_outcome: null,
    effective_outcome: null, corrections: [], notes: "Shared customers.",
  },
  {
    decision_id: "RD2", agent_id: "A20002", reviewer_id: "ADM_ANALYST_02", decision_outcome: "legitimate",
    decision_timestamp: "2026-10-12T09:00:00", status: "agreed", closed_by: "ADM_COMPLIANCE_01", closed_at: "2026-10-12T10:00:00",
    final_outcome: "legitimate", effective_outcome: "legitimate", corrections: [], notes: null,
  },
  {
    decision_id: "RD3", agent_id: "A30003", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
    decision_timestamp: "2026-10-11T09:00:00", status: "overruled", closed_by: "ADM_COMPLIANCE_01", closed_at: "2026-10-11T12:00:00",
    final_outcome: "legitimate", close_note: "One family.", effective_outcome: "confirmed_fraud", notes: "Same customers.",
    corrections: [{
      correction_id: "RC1", previous_outcome: "legitimate", new_outcome: "confirmed_fraud", corrected_by: "ADM_COMPLIANCE_02",
      corrected_at: "2026-10-14T08:00:00", note: "New evidence of a ring.",
    }],
  },
  {
    decision_id: "RD4", agent_id: "A40004", reviewer_id: "ADM_ANALYST_01", decision_outcome: "legitimate",
    decision_timestamp: "2026-10-10T09:00:00", status: "withdrawn", closed_by: "ADM_ANALYST_01", closed_at: "2026-10-10T09:30:00",
    final_outcome: null, close_note: "Wrong agent.", effective_outcome: null, corrections: [], notes: "Checked.",
  },
];

function routes(role = "fraud_analyst", decisions = DECISIONS) {
  return { ...sessionRoutes(role), "GET /api/review-decisions": { count: decisions.length, decisions } };
}

const table = () => screen.findByRole("table", { name: "Review decisions" });
const agents = (t) => within(t).queryAllByRole("link").map((l) => l.textContent);

describe("Review history", () => {
  it("shows status, outcome in force, proposer, who closed it, notes and dates", async () => {
    mockApi(routes());
    renderApp("/history");
    const t = await table();
    for (const header of ["Agent", "Proposed outcome", "Status", "Outcome in force", "Proposed by", "Closed by", "Notes", "Proposed on"]) {
      expect(within(t).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(agents(t)).toEqual(["A10001", "A20002", "A30003", "A40004"]);
    for (const status of ["Proposed", "Agreed", "Overruled", "Withdrawn", "Corrected"]) {
      expect(within(t).getByText(status)).toBeInTheDocument();
    }
    expect(within(t).getAllByText("ADM_COMPLIANCE_01")).toHaveLength(2);
    expect(within(t).getByText("Waiting")).toBeInTheDocument();
    expect(within(t).getByText("Shared customers.")).toBeInTheDocument();
    expect(within(t).getByText("None (before notes were required)")).toBeInTheDocument();
    expect(document.title).toBe("Review history · SalesMesh Fraud Detection");
  });

  it("filters by status and outcome and keeps the filters in the URL", async () => {
    mockApi(routes());
    renderApp("/history");
    const t = await table();
    await userEvent.click(screen.getByRole("combobox", { name: "Status" }));
    await userEvent.click(screen.getByRole("option", { name: "Agreed" }));
    expect(agents(t)).toEqual(["A20002"]);
    expect(currentLocation()).toBe("/history?status=agreed");

    await userEvent.click(screen.getByRole("combobox", { name: "Proposed outcome" }));
    await userEvent.click(screen.getByRole("option", { name: "Confirmed fraud" }));
    expect(screen.getByText("No decisions match your filters.")).toBeInTheDocument();
  });

  it("reads filters from the URL", async () => {
    mockApi(routes("compliance_officer"));
    renderApp("/history?outcome=confirmed_fraud");
    expect(agents(await table())).toEqual(["A10001", "A30003"]);
  });

  it("opens the full history of a decision: proposal, overrule and correction", async () => {
    mockApi(routes());
    renderApp("/history");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Show the history of the decision for A30003" }));
    const dialog = screen.getByRole("dialog", { name: "Decision history for A30003" });
    expect(within(dialog).getByText(/Proposed by ADM_ANALYST_01/)).toBeInTheDocument();
    expect(within(dialog).getByText(/Overruled by ADM_COMPLIANCE_01 .*: final outcome Legitimate/)).toBeInTheDocument();
    expect(within(dialog).getByText("One family.")).toBeInTheDocument();
    expect(within(dialog).getByText(/Corrected by ADM_COMPLIANCE_02 .*: Legitimate to Confirmed fraud/)).toBeInTheDocument();
    expect(within(dialog).getByText("New evidence of a ring.")).toBeInTheDocument();
    expect(within(dialog).getByText("Outcome in force: Confirmed fraud")).toBeInTheDocument();
  });

  it("shows a withdrawal with its note", async () => {
    mockApi(routes());
    renderApp("/history");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Show the history of the decision for A40004" }));
    const dialog = screen.getByRole("dialog", { name: "Decision history for A40004" });
    expect(within(dialog).getByText(/Withdrawn by ADM_ANALYST_01/)).toBeInTheDocument();
    expect(within(dialog).getByText("Wrong agent.")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockApi(routes("fraud_analyst", []));
    renderApp("/history");
    expect(await screen.findByText("No decisions recorded yet.")).toBeInTheDocument();
  });

  it("is not open to admins", async () => {
    mockApi(routes("admin"));
    renderApp("/history");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });
});
