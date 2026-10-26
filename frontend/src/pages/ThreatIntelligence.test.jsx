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
const RINGS = {
  rule: "Agents the model flagged ...", min_shared_customers: 3, flagged_agents: 145, candidates_total: 2,
  candidates: [
    { candidate_id: "cand_01", size: 3, agent_ids: ["A11607", "A14278", "A33509"], shared_customers: 41, client_ids: ["CL01", "CL04"] },
    { candidate_id: "cand_02", size: 2, agent_ids: ["A23833", "A65723"], shared_customers: 4, client_ids: ["CL09"] },
  ],
};
const day = (date, a, b, c) => ({ date, activations: a + b + c, by_agent: { A11607: a, A14278: b, A33509: c } });
const GRAPH_1 = {
  run_id: "RUN1", candidate_id: "cand_01", size: 3, rule: "...", min_shared_customers: 3,
  nodes: [
    { agent_id: "A11607", county: "Nairobi", flag_source: "ML", risk_band: "high", activations: 9, linked_members: 2 },
    { agent_id: "A14278", county: "Kisumu", flag_source: "Both", risk_band: "high", activations: 6, linked_members: 1 },
    { agent_id: "A33509", county: "Nairobi", flag_source: "ML", risk_band: "high", activations: 4, linked_members: 1 },
  ],
  edges: [
    { source: "A11607", target: "A14278", shared_customers: 30, meets_rule: true },
    { source: "A11607", target: "A33509", shared_customers: 2, meets_rule: false },
  ],
  counties: ["Kisumu", "Nairobi"], county_count: 2,
  county_note: "County is the agent's region in the loaded data, shown for information only. The model never uses it.",
  first_day: "2026-08-01", last_day: "2026-08-02", days: [day("2026-08-01", 5, 4, 1), day("2026-08-02", 4, 2, 3)],
  note: "Days are as recorded in the data.",
};
const GRAPH_2 = {
  ...GRAPH_1, candidate_id: "cand_02", size: 2, counties: ["Lamu"], county_count: 1,
  nodes: [
    { agent_id: "A23833", county: "Lamu", flag_source: "ML", risk_band: "high", activations: 3, linked_members: 1 },
    { agent_id: "A65723", county: "Lamu", flag_source: "Both", risk_band: "high", activations: 2, linked_members: 1 },
  ],
  edges: [{ source: "A23833", target: "A65723", shared_customers: 4, meets_rule: true }],
  days: [{ date: "2026-08-01", activations: 5, by_agent: { A23833: 3, A65723: 2 } }],
};
const TOP = {
  scores: [{ agent_id: "A35485", anomaly_score: 5.563827, score_percentile: 98.9, flag_source: "Both", risk_band: "high", top_features: ["collusion_score", "submission_frequency"] }],
};

function routes(role, extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/threat-intelligence/summary": SUMMARY,
    "GET /api/threat-intelligence/timeline": { first_day: "2026-08-01", last_day: "2026-08-01", days: [{ date: "2026-08-01", flagged_agents: 965, other_agents: 3534 }] },
    "GET /api/threat-intelligence/by-region": { regions: [], top_by_flagged_rate: [{ region: "Lamu", agents: 5, flagged: 2, rule_flagged: 1, flagged_rate: 0.4 }], min_agents_for_top: 5 },
    "GET /api/threat-intelligence/customer-sharing": SHARING,
    "GET /api/threat-intelligence/ring-candidates": RINGS,
    "GET /api/threat-intelligence/ring-candidates/cand_01": GRAPH_1,
    "GET /api/threat-intelligence/ring-candidates/cand_02": GRAPH_2,
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
    expect(within(top).getByRole("group", { name: "Score 5.564, percentile 98.9" })).toHaveTextContent("5.564 Top 2%");
    const groups = await card("Connected agents");
    expect(within(groups).getByRole("link", { name: "A80697" })).toBeInTheDocument();
    expect(within(groups).getByText(/279 customers/)).toBeInTheDocument();
    expect(document.title).toBe("Threat intelligence · SalesMesh Fraud Detection");
  });

  it("lists ring candidates with linked agents, sizes, shared customers and clients", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("2 groups among the 145 agents the model flagged.")).toBeInTheDocument();
    const rows = within(within(rings).getByRole("table", { name: "Ring candidate groups" })).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("cand_01")).toBeInTheDocument();
    expect(within(rows[0]).getByRole("link", { name: "A14278" })).toHaveAttribute("href", "/agents/A14278");
    expect(within(rows[0]).getByText("41")).toBeInTheDocument();
    expect(within(rows[0]).getByText("CL01, CL04")).toBeInTheDocument();
    expect(within(rows[1]).getAllByRole("link").map((l) => l.textContent)).toEqual(["A23833", "A65723"]);
    expect(within(rings).getByText("A candidate is a lead for review, not a confirmed ring. No labels are used.")).toBeInTheDocument();
  });

  it("draws the first ring as a graph with shared customer counts, a pairs table, counties and no customer id", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const graphCard = await card("Ring graph: cand_01");
    const svg = await within(graphCard).findByRole("group", { name: /Graph of ring candidate cand_01: 3 agents and 2 pairs/ });
    expect(within(svg).getAllByRole("button")).toHaveLength(3);
    expect(within(svg).getByText("30")).toBeInTheDocument();
    const pairs = within(graphCard).getByRole("table", { name: "Pairs in cand_01 that share customers" });
    expect(within(pairs).getAllByRole("row").slice(1).map((r) => r.textContent)).toEqual(["A11607A1427830Yes", "A11607A335092No"]);
    const members = within(graphCard).getByRole("table", { name: "Members of cand_01" });
    expect(within(members).getAllByText("Nairobi")).toHaveLength(2);
    expect(within(graphCard).getByText("2 counties: Kisumu, Nairobi.")).toBeInTheDocument();
    expect(within(graphCard).getByText(/The model never uses it/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/CUST\d/);
  });

  it("lets a keyboard user select an agent in the graph to highlight its pairs", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const svg = await within(await card("Ring graph: cand_01")).findByRole("group", { name: /Graph of ring candidate cand_01/ });
    const node = within(svg).getByRole("button", { name: /Agent A11607, county Nairobi, shares customers with 2/ });
    node.focus();
    expect(node).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("A11607 shares customers with A14278 (30), A33509 (2).")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    expect(node).toHaveAttribute("aria-pressed", "false");
    await userEvent.tab();
    expect(within(svg).getByRole("button", { name: /Agent A14278/ })).toHaveFocus();
  });

  it("shows another ring and its group activity per day with a table view", async () => {
    const { calls } = mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    await card("Ring graph: cand_01");
    await userEvent.click(screen.getByRole("button", { name: "Show the graph of cand_02" }));
    expect(await card("Ring graph: cand_02")).toBeInTheDocument();
    expect(calls.some((c) => c.path === "/api/threat-intelligence/ring-candidates/cand_02")).toBe(true);
    const activity = await card("Group activity: cand_02");
    await userEvent.click(within(activity).getByRole("button", { name: "Show as table" }));
    const table = within(activity).getByRole("table", { name: "Group activity: cand_02 data" });
    expect(within(table).getAllByRole("row")[1].textContent).toBe("2026-08-01532");
  });

  it("shows ring candidate agent ids as plain text to an admin", async () => {
    mockApi(routes("admin"));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("A23833")).toBeInTheDocument();
    expect(within(rings).queryByRole("link")).not.toBeInTheDocument();
  });

  it("keeps the other cards when ring candidates fail, and retries them", async () => {
    let attempts = 0;
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/ring-candidates": () => (++attempts === 1 ? reply(500, { error: "Ring candidates unavailable" }) : RINGS),
    }));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("Ring candidates unavailable")).toBeInTheDocument();
    expect(within(await card("Connected agents")).queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(within(rings).getByRole("button", { name: "Try again" }));
    expect(await within(rings).findByRole("link", { name: "A23833" })).toBeInTheDocument();
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
      "GET /api/threat-intelligence/ring-candidates": { flagged_agents: 0, candidates_total: 0, candidates: [] },
    }));
    renderApp("/threat-intelligence");
    expect(await within(await card("Flag sources")).findByText("No successful detection run yet.")).toBeInTheDocument();
    expect(within(await card("Top risk agents")).getByText("No successful detection run yet.")).toBeInTheDocument();
    expect(within(await card("Connected agents")).getByText("No agents share customers.")).toBeInTheDocument();
    expect(within(await card("Ring candidates")).getByText("No flagged agents share 3 or more customers.")).toBeInTheDocument();
  });
});
