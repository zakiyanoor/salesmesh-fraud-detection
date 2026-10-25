import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const decision = (id, agent, status, extra = {}) => ({
  decision_id: id, agent_id: agent, reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
  decision_timestamp: "2026-10-13T15:10:00", status, flag_source: "ML", still_flagged: true, overdue: false,
  closed_by: status === "agreed" ? "ADM_COMPLIANCE_01" : null, final_outcome: status === "agreed" ? "confirmed_fraud" : null,
  corrections: [], notes: `Notes for ${agent}`, ...extra,
});

const DECISIONS = [
  decision("RD1", "A10001", "pending_confirmation"),
  decision("RD2", "A20002", "pending_confirmation", { decision_outcome: "legitimate", reviewer_id: "ADM_COMPLIANCE_01", flag_source: "Rule" }),
  decision("RD3", "A30003", "agreed"),
  decision("RD4", "A40004", "pending_confirmation", { overdue: true, still_flagged: false, flag_source: "Both", decision_timestamp: "2026-10-01T09:00:00" }),
  decision("RD5", "A50005", "withdrawn"),
];

function routes(role = "compliance_officer", extra = {}) {
  return { ...sessionRoutes(role), "GET /api/review-decisions": { count: DECISIONS.length, decisions: DECISIONS }, ...extra };
}

const queue = () => screen.findByRole("table", { name: "Decisions waiting for confirmation" });
const rowOf = (table, agent) => within(table).getByText(agent).closest("tr");

describe("Confirm queue", () => {
  it("lists only open proposals, oldest first, with flag source, proposer, outcome, notes and date", async () => {
    mockApi(routes());
    renderApp("/review/confirm");
    const table = await queue();
    const agents = within(table).getAllByRole("link").map((l) => l.textContent);
    expect(agents).toEqual(["A40004", "A10001", "A20002"]);
    expect(within(table).getByText("A20002")).toBeInTheDocument();
    expect(within(table).queryByText("A30003")).not.toBeInTheDocument();
    expect(within(table).queryByText("A50005")).not.toBeInTheDocument();
    expect(within(table).getByText("Notes for A10001")).toBeInTheDocument();
    expect(within(rowOf(table, "A20002")).getByText("Rule only")).toBeInTheDocument();
    expect(within(table).getByText("Legitimate")).toBeInTheDocument();
    expect(document.title).toBe("Confirm queue · SalesMesh Fraud Detection");
  });

  it("marks an overdue proposal and one whose agent is no longer flagged, and decides nothing itself", async () => {
    const { calls } = mockApi(routes());
    renderApp("/review/confirm");
    const table = await queue();
    expect(within(rowOf(table, "A40004")).getByText("Overdue")).toBeInTheDocument();
    expect(within(rowOf(table, "A40004")).getByText("No longer flagged in the latest run")).toBeInTheDocument();
    expect(within(rowOf(table, "A10001")).queryByText("Overdue")).not.toBeInTheDocument();
    expect(screen.getByText(/nothing is decided automatically/)).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("agrees without a note, then removes the row and gives the final outcome", async () => {
    const { calls } = mockApi(routes("compliance_officer", {
      "POST /api/review-decisions/RD1/agree": { status: "agreed", final_outcome: "confirmed_fraud" },
    }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Agree with the proposal for A10001" }));
    const dialog = screen.getByRole("dialog", { name: "Agree with this proposal?" });
    expect(within(dialog).getByText(/Notes for A10001/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Note (optional)")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Agree" }));

    expect(await screen.findByText("Proposal for A10001 agreed. The final outcome is Confirmed fraud.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(table).queryByText("A10001")).not.toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect([post.path, post.body]).toEqual(["/api/review-decisions/RD1/agree", {}]);
  });

  it("overrules with the other outcome preset and a required note", async () => {
    const { calls } = mockApi(routes("compliance_officer", {
      "POST /api/review-decisions/RD1/overrule": { status: "overruled", final_outcome: "legitimate" },
    }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Overrule the proposal for A10001" }));
    const dialog = screen.getByRole("dialog", { name: "Overrule this proposal?" });
    expect(within(dialog).getByLabelText("Legitimate")).toBeChecked();
    await userEvent.click(within(dialog).getByRole("button", { name: "Overrule" }));
    expect(within(dialog).getByText("Notes are required.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await userEvent.type(within(dialog).getByLabelText(/Note/), "The shared customers are one family.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Overrule" }));
    expect(await screen.findByText("Proposal for A10001 overruled. The final outcome is Legitimate.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST").body).toEqual({ final_outcome: "legitimate", notes: "The shared customers are one family." });
  });

  it("keeps the row and explains the error when you try to decide your own proposal", async () => {
    mockApi(routes("compliance_officer", {
      "POST /api/review-decisions/RD2/agree": reply(403, { error: "A decision cannot be agreed or overruled by the admin who proposed it" }),
    }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Agree with the proposal for A20002" }));
    await userEvent.click(screen.getByRole("button", { name: "Agree" }));
    const alert = await within(screen.getByRole("dialog")).findByRole("alert");
    expect(alert).toHaveTextContent("A decision cannot be agreed or overruled by the admin who proposed it. Another compliance officer must decide it.");
    // A refused action does not sign the user out or hide the page.
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(within(table).getByText("A20002")).toBeInTheDocument();
  });

  it("drops a proposal that was withdrawn or decided meanwhile", async () => {
    mockApi(routes("compliance_officer", { "POST /api/review-decisions/RD1/agree": reply(409, { error: "Decision RD1 is already withdrawn" }) }));
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Agree with the proposal for A10001" }));
    await userEvent.click(screen.getByRole("button", { name: "Agree" }));
    expect(await screen.findByText(/already withdrawn or decided by someone else/)).toBeInTheDocument();
    expect(within(table).queryByText("A10001")).not.toBeInTheDocument();
  });

  it("cancel closes the dialog without a request", async () => {
    const { calls } = mockApi(routes());
    renderApp("/review/confirm");
    const table = await queue();
    await userEvent.click(within(table).getByRole("button", { name: "Overrule the proposal for A10001" }));
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

  it("shows agree and overrule buttons on cards on narrow screens", async () => {
    window.innerWidth = 360;
    mockApi(routes());
    renderApp("/review/confirm");
    const list = await screen.findByRole("region", { name: "Decisions waiting for confirmation" });
    expect(within(list).getByRole("button", { name: "Agree with the proposal for A10001" })).toBeInTheDocument();
    expect(within(list).getByRole("button", { name: "Overrule the proposal for A10001" })).toBeInTheDocument();
  });
});
