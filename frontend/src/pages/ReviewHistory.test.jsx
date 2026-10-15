import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";

const DECISIONS = [
  {
    decision_id: "RD1", agent_id: "A10001", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
    decision_timestamp: "2026-10-13T15:10:00", status: "pending_confirmation", confirmed_by: null, notes: "Shared customers.",
  },
  {
    decision_id: "RD2", agent_id: "A20002", reviewer_id: "ADM_ANALYST_02", decision_outcome: "legitimate",
    decision_timestamp: "2026-10-12T09:00:00", status: "confirmed", confirmed_by: "ADM_COMPLIANCE_01", notes: null,
  },
];

function routes(role = "fraud_analyst", decisions = DECISIONS) {
  return { ...sessionRoutes(role), "GET /api/review-decisions": { count: decisions.length, decisions } };
}

const table = () => screen.findByRole("table", { name: "Review decisions" });
const agents = (t) => within(t).queryAllByRole("link").map((l) => l.textContent);

describe("Review history", () => {
  it("shows status, proposer, confirmer, notes and dates", async () => {
    mockApi(routes());
    renderApp("/history");
    const t = await table();
    for (const header of ["Agent", "Outcome", "Status", "Proposed by", "Confirmed by", "Notes", "Proposed on"]) {
      expect(within(t).getByRole("columnheader", { name: header })).toBeInTheDocument();
    }
    expect(agents(t)).toEqual(["A10001", "A20002"]);
    expect(within(t).getByText("Proposed")).toBeInTheDocument();
    expect(within(t).getByText("Confirmed")).toBeInTheDocument();
    expect(within(t).getByText("ADM_COMPLIANCE_01")).toBeInTheDocument();
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
    await userEvent.click(screen.getByRole("option", { name: "Confirmed" }));
    expect(agents(t)).toEqual(["A20002"]);
    expect(currentLocation()).toBe("/history?status=confirmed");

    await userEvent.click(screen.getByRole("combobox", { name: "Outcome" }));
    await userEvent.click(screen.getByRole("option", { name: "Confirmed fraud" }));
    expect(screen.getByText("No decisions match your filters.")).toBeInTheDocument();
  });

  it("reads filters from the URL", async () => {
    mockApi(routes("compliance_officer"));
    renderApp("/history?outcome=confirmed_fraud");
    expect(agents(await table())).toEqual(["A10001"]);
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
