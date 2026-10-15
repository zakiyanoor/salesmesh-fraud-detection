import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const SUMMARY = {
  agents_scored: 1000, flagged: 145, flagged_rate: 0.145, rule_flagged: 102,
  flag_sources: { ML: 72, Rule: 29, Both: 73, None: 826 },
  risk_bands: { high: 145, review: 89, low: 766 },
  commission_kes: { total: 17232310, flagged_agents: 3701730, flagged_share: 0.214813 },
  top_features: {
    as_top_feature: [{ feature: "collusion_score", agents: 70 }, { feature: "customer_similarity", agents: 47 }],
    in_top_three: [{ feature: "time_of_day_entropy", agents: 123 }],
  },
};
const SHARING = {
  shared_customers: 279, clusters_total: 12, limits: { customers: 50, clusters: 50 },
  customers: [],
  clusters: [{ size: 3, agent_ids: ["A57819", "A80697", "A95717"], client_ids: ["CL01", "CL02"], customer_count: 33, flagged_agents: 3 }],
};
const TOP = {
  scores: [{ agent_id: "A35485", anomaly_score: 5.563827, flag_source: "Both", risk_band: "high", top_features: ["collusion_score", "submission_frequency"] }],
};

function routes(role, extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/threat-intelligence/summary": SUMMARY,
    "GET /api/threat-intelligence/timeline": { first_day: "2026-08-01", last_day: "2026-08-01", days: [{ date: "2026-08-01", flagged_agents: 965, other_agents: 3534 }] },
    "GET /api/threat-intelligence/by-region": { regions: [], top_by_flagged_rate: [{ region: "Lamu", agents: 5, flagged: 2, rule_flagged: 1, flagged_rate: 0.4 }], min_agents_for_top: 5 },
    "GET /api/threat-intelligence/customer-sharing": SHARING,
    "GET /api/agent-scores": TOP,
    ...extra,
  };
}

const card = (name) => screen.findByRole("region", { name });

describe("Threat intelligence", () => {
  it("shows the summary, every card, and links agent ids for an analyst", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const summary = await card("Summary");
    expect(await within(summary).findByText("14.5%")).toBeInTheDocument();
    expect(within(summary).getByText("21.5%")).toBeInTheDocument();
    expect(within(await card("Flag sources")).getByText("Rule only")).toBeInTheDocument();
    for (const name of ["What drives the flags", "Activation timeline", "Regional flagged rates"]) {
      expect(within(await card(name)).queryByRole("alert")).not.toBeInTheDocument();
    }
    const top = await card("Top risk agents");
    expect(within(top).getByRole("link", { name: "A35485" })).toHaveAttribute("href", "/agents/A35485");
    expect(within(top).getByText("Collusion score, Submission frequency")).toBeInTheDocument();
    const groups = await card("Connected agents");
    expect(within(groups).getByRole("link", { name: "A80697" })).toBeInTheDocument();
    expect(within(groups).getByText(/279 customers/)).toBeInTheDocument();
    expect(document.title).toBe("Threat intelligence · SalesMesh Fraud Detection");
  });

  it("shows agent ids as plain text to an admin", async () => {
    mockApi(routes("admin"));
    renderApp("/threat-intelligence");
    const top = await card("Top risk agents");
    expect(await within(top).findByText("A35485")).toBeInTheDocument();
    expect(within(top).queryByRole("link")).not.toBeInTheDocument();
    expect(within(await card("Connected agents")).queryByRole("link")).not.toBeInTheDocument();
  });

  it("is open to compliance officers", async () => {
    mockApi(routes("compliance_officer"));
    renderApp("/threat-intelligence");
    expect(await screen.findByRole("heading", { name: "Threat intelligence", level: 1 })).toBeInTheDocument();
    expect(await within(await card("Top risk agents")).findByRole("link", { name: "A35485" })).toBeInTheDocument();
  });

  it("keeps the other cards when one fails, and retries it", async () => {
    let attempts = 0;
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/customer-sharing": () => (++attempts === 1 ? reply(404, { error: "No successful detection run yet" }) : SHARING),
    }));
    renderApp("/threat-intelligence");
    const groups = await card("Connected agents");
    expect(await within(groups).findByText("No successful detection run yet")).toBeInTheDocument();
    expect(within(await card("Top risk agents")).queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(within(groups).getByRole("button", { name: "Try again" }));
    expect(await within(groups).findByRole("link", { name: "A57819" })).toBeInTheDocument();
  });

  it("shows empty states before any run", async () => {
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/summary": { agents_scored: 0, flag_sources: {}, risk_bands: {}, top_features: { as_top_feature: [] } },
      "GET /api/agent-scores": { scores: [] },
      "GET /api/threat-intelligence/customer-sharing": { shared_customers: 0, clusters_total: 0, clusters: [] },
    }));
    renderApp("/threat-intelligence");
    expect(await within(await card("Flag sources")).findByText("No successful detection run yet.")).toBeInTheDocument();
    expect(within(await card("Top risk agents")).getByText("No successful detection run yet.")).toBeInTheDocument();
    expect(within(await card("Connected agents")).getByText("No agents share customers.")).toBeInTheDocument();
  });
});
