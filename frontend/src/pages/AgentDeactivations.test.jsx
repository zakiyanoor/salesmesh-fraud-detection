import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const REQUESTS = [
  {
    deactivation_id: "DA1", agent_id: "A10001", decision_id: "RD1", decision_status: "agreed", final_outcome: "confirmed_fraud",
    effective_outcome: "confirmed_fraud", requested_by: "ADM_COMPLIANCE_01", requested_at: "2026-10-27T05:30:00",
    status: "pending_deactivation", actioned_by: null, actioned_at: null, note: null,
  },
  {
    deactivation_id: "DA2", agent_id: "A20002", decision_id: "RD2", decision_status: "overruled", final_outcome: "confirmed_fraud",
    effective_outcome: "confirmed_fraud", requested_by: "ADM_COMPLIANCE_01", requested_at: "2026-10-26T05:30:00",
    status: "deactivated", actioned_by: "ADM_ADMIN_01", actioned_at: "2026-10-26T14:26:00", note: null,
  },
  {
    deactivation_id: "DA3", agent_id: "A30003", decision_id: "RD3", decision_status: "agreed", final_outcome: "confirmed_fraud",
    effective_outcome: "legitimate", requested_by: "ADM_COMPLIANCE_01", requested_at: "2026-10-25T05:30:00",
    status: "cancelled", actioned_by: "ADM_COMPLIANCE_01", actioned_at: "2026-10-25T09:00:00", note: "Wrong month.",
  },
];

function routes(role = "admin", extra = {}) {
  return { ...sessionRoutes(role), "GET /api/admin/agent-deactivations": { count: REQUESTS.length, deactivations: REQUESTS }, ...extra };
}

const table = () => screen.findByRole("table", { name: "Agent deactivations" });
const row = (t, agentId) => within(t).getByText(agentId).closest("tr");

describe("Agent deactivations", () => {
  it("lists requests with agent, decision, status and action, pending first", async () => {
    mockApi(routes());
    renderApp("/agent-deactivations");
    const t = await table();
    expect(within(t).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Agent", "Decision", "Status", "Action"]);
    const rows = within(t).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.querySelector("td").textContent)).toEqual(["A10001", "A20002", "A30003"]);
    expect(within(row(t, "A10001")).getByText("RD1")).toBeInTheDocument();
    expect(within(row(t, "A10001")).getByText("Confirmed fraud")).toBeInTheDocument();
    expect(within(row(t, "A10001")).getByText("Deactivation pending")).toBeInTheDocument();
    expect(within(row(t, "A20002")).getByText("Deactivated")).toBeInTheDocument();
    expect(within(row(t, "A30003")).getByText("Cancelled")).toBeInTheDocument();
    expect(within(row(t, "A30003")).getByText("Legitimate")).toBeInTheDocument();
    expect(document.title).toBe("Agent deactivations · SalesMesh Fraud Detection");
  });

  it("offers Deactivate Agent only on pending rows", async () => {
    mockApi(routes());
    renderApp("/agent-deactivations");
    const t = await table();
    expect(within(row(t, "A10001")).getByRole("button", { name: "Deactivate Agent A10001" })).toHaveTextContent("Deactivate Agent");
    expect(within(row(t, "A20002")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(row(t, "A30003")).queryByRole("button")).not.toBeInTheDocument();
    expect(within(row(t, "A20002")).getByText("Deactivated by ADM_ADMIN_01, 26 Oct 2026, 17:26")).toBeInTheDocument();
  });

  it("deactivates after confirming, saying nothing is deleted, and updates the row", async () => {
    const { calls } = mockApi(routes("admin", {
      "POST /api/admin/agent-deactivations/DA1/confirm": {
        message: "Agent deactivated",
        deactivation: { ...REQUESTS[0], status: "deactivated", actioned_by: "ADM_ADMIN_01", actioned_at: "2026-10-27T06:00:00" },
      },
    }));
    renderApp("/agent-deactivations");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Deactivate Agent A10001" }));
    const dialog = screen.getByRole("dialog", { name: "Deactivate Agent" });
    expect(dialog).toHaveTextContent("Agent A10001 will be marked deactivated.");
    expect(dialog).toHaveTextContent("Nothing will be deleted");
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate Agent" }));
    expect(await screen.findByText("Agent A10001 is deactivated.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(row(t, "A10001")).getByText("Deactivated")).toBeInTheDocument();
    expect(within(row(t, "A10001")).queryByRole("button")).not.toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST").map((c) => c.path)).toEqual(["/api/admin/agent-deactivations/DA1/confirm"]);
  });

  it("cancel closes the dialog without a request", async () => {
    const { calls } = mockApi(routes());
    renderApp("/agent-deactivations");
    await userEvent.click(within(await table()).getByRole("button", { name: "Deactivate Agent A10001" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("shows the server's refusal in the dialog", async () => {
    mockApi(routes("admin", {
      "POST /api/admin/agent-deactivations/DA1/confirm": reply(409, { error: "Deactivation request DA1 is already deactivated" }),
    }));
    renderApp("/agent-deactivations");
    await userEvent.click(within(await table()).getByRole("button", { name: "Deactivate Agent A10001" }));
    const dialog = screen.getByRole("dialog", { name: "Deactivate Agent" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate Agent" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Deactivation request DA1 is already deactivated");
  });

  it("shows an empty state when nothing is waiting", async () => {
    mockApi(routes("admin", { "GET /api/admin/agent-deactivations": { count: 0, deactivations: [] } }));
    renderApp("/agent-deactivations");
    expect(await screen.findByText("No agent is waiting to be deactivated.")).toBeInTheDocument();
  });

  it.each(["fraud_analyst", "compliance_officer"])("is not open to a %s", async (role) => {
    const { calls } = mockApi(routes(role));
    renderApp("/agent-deactivations");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/admin/agent-deactivations")).toBe(false);
  });
});
