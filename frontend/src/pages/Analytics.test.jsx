import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const TIMELINE = {
  first_day: "2026-08-01", last_day: "2026-08-02",
  days: [{ date: "2026-08-01", flagged_agents: 965, other_agents: 3534 }, { date: "2026-08-02", flagged_agents: 900, other_agents: 3400 }],
};
const REGIONS = {
  regions: [], min_agents_for_top: 5,
  top_by_flagged_rate: [{ region: "Lamu", agents: 5, flagged: 2, rule_flagged: 1, flagged_rate: 0.4 }],
};

function routes(role = "fraud_analyst", extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/threat-intelligence/timeline": TIMELINE,
    "GET /api/threat-intelligence/by-region": REGIONS,
    ...extra,
  };
}

const card = (name) => screen.findByRole("region", { name });

describe("Analytics", () => {
  it.each(["fraud_analyst", "compliance_officer", "admin"])("shows every chart card to a %s", async (role) => {
    mockApi(routes(role));
    renderApp("/analytics");
    for (const name of ["Daily activations", "Suspicion score distribution", "Highest flagged rates by county", "Flagged agents by county"]) {
      const region = await card(name);
      expect(within(region).queryByRole("alert")).not.toBeInTheDocument();
    }
    const review = await card("Review outcomes");
    expect(within(review).getByText("33.3% overruled")).toBeInTheDocument();
    expect(within(review).getByText("1 of 3 compliance decisions")).toBeInTheDocument();
    const averages = await card("Platform average behaviour");
    expect(within(averages).getByText("14.0")).toBeInTheDocument();
    expect(within(averages).getByText("Customer similarity")).toBeInTheDocument();
    expect(document.title).toBe("Analytics · SalesMesh Fraud Detection");
  });

  it("keeps the other cards when one fails, and retries it", async () => {
    let attempts = 0;
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/timeline": () => (++attempts === 1 ? reply(500, { error: "Timeline unavailable" }) : TIMELINE),
    }));
    renderApp("/analytics");
    const timeline = await card("Daily activations");
    expect(await within(timeline).findByText("Timeline unavailable")).toBeInTheDocument();
    expect(within(await card("Suspicion score distribution")).queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(within(timeline).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(within(timeline).queryByText("Timeline unavailable")).not.toBeInTheDocument());
    expect(within(timeline).queryByRole("alert")).not.toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it("shows empty states before any data is loaded", async () => {
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/timeline": { days: [] },
      "GET /api/threat-intelligence/by-region": { top_by_flagged_rate: [] },
      "GET /api/analytics": { score_distribution: [], region_breakdown: [], platform_averages: {} },
    }));
    renderApp("/analytics");
    expect(await within(await card("Daily activations")).findByText("No activation records are loaded yet.")).toBeInTheDocument();
    expect(within(await card("Suspicion score distribution")).getByText("No agents are scored yet.")).toBeInTheDocument();
    expect(within(await card("Highest flagged rates by county")).getByText("No county has enough agents yet.")).toBeInTheDocument();
  });
});
