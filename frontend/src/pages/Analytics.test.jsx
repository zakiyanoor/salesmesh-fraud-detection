import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FIXTURES, mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const SUMMARY = {
  ...FIXTURES["GET /api/threat-intelligence/summary"],
  top_features: { as_top_feature: [{ feature: "collusion_score", agents: 70 }, { feature: "customer_similarity", agents: 47 }] },
};

function routes(role = "fraud_analyst", extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/threat-intelligence/summary": SUMMARY,
    ...extra,
  };
}

const card = (name) => screen.findByRole("region", { name });

describe("Analytics", () => {
  it.each(["fraud_analyst", "compliance_officer", "admin"])("shows the four cards to a %s", async (role) => {
    mockApi(routes(role));
    renderApp("/analytics");
    for (const name of ["Suspicion score distribution", "What drives the flags"]) {
      const region = await card(name);
      expect(within(region).queryByRole("alert")).not.toBeInTheDocument();
    }
    const review = await card("Review outcomes");
    expect(within(review).getByText("33.3% overruled")).toBeInTheDocument();
    expect(within(review).getByText("1 of 3 compliance decisions")).toBeInTheDocument();
    expect(within(review).getByText("Overruled means a compliance officer disagreed with the analyst's proposal.")).toBeInTheDocument();
    const averages = await card("Platform average behaviour");
    expect(within(averages).getByText("14.0")).toBeInTheDocument();
    expect(within(averages).getByText("Customer similarity")).toBeInTheDocument();
    expect(document.title).toBe("Analytics · SalesMesh Fraud Detection");
  });

  it("no longer repeats the timeline or the county charts, which are on Threat intelligence", async () => {
    const { calls } = mockApi(routes());
    renderApp("/analytics");
    await card("Review outcomes");
    for (const gone of ["Daily activations", "Highest flagged rates by county", "Flagged agents by county"]) {
      expect(screen.queryByRole("region", { name: gone })).not.toBeInTheDocument();
    }
    expect(calls.some((c) => c.path.startsWith("/api/threat-intelligence/timeline") || c.path.startsWith("/api/threat-intelligence/by-region"))).toBe(false);
  });

  it("shows what drives the flags, with its subtitle and table view", async () => {
    mockApi(routes());
    renderApp("/analytics");
    const drives = await card("What drives the flags");
    expect(within(drives).getByText("Flagged agents by their strongest feature")).toBeInTheDocument();
    await userEvent.click(await within(drives).findByRole("button", { name: "Show as table" }));
    const table = within(drives).getByRole("table", { name: "What drives the flags data" });
    expect(within(table).getAllByRole("row")[1].textContent).toBe("Collusion score70");
  });

  it("keeps the other cards when one fails, and retries it", async () => {
    let attempts = 0;
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/summary": () => (++attempts === 1 ? reply(500, { error: "Summary unavailable" }) : SUMMARY),
    }));
    renderApp("/analytics");
    const drives = await card("What drives the flags");
    expect(await within(drives).findByText("Summary unavailable")).toBeInTheDocument();
    expect(within(await card("Suspicion score distribution")).queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(within(drives).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(within(drives).queryByText("Summary unavailable")).not.toBeInTheDocument());
    expect(attempts).toBe(2);
  });

  it("shows empty states before any data is loaded", async () => {
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/summary": { agents_scored: 0, top_features: { as_top_feature: [] } },
      "GET /api/analytics": { score_distribution: [], region_breakdown: [], platform_averages: {} },
    }));
    renderApp("/analytics");
    expect(await within(await card("Suspicion score distribution")).findByText("No agents are scored yet.")).toBeInTheDocument();
    expect(within(await card("What drives the flags")).getByText("No flagged agents to explain yet.")).toBeInTheDocument();
  });
});

describe("Analytics cutoff", () => {
  it("reads the cutoff in the score distribution subtitle from the API", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": { ...FIXTURES["GET /api/model-info"], cutoff: 2.25 } });
    renderApp("/analytics");
    const card = await screen.findByRole("region", { name: "Suspicion score distribution" });
    await waitFor(() => expect(card).toHaveTextContent("Agents per score range; the cutoff is 2.250"));
  });
});
