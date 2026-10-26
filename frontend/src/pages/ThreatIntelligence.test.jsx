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
    ...extra,
  };
}

const card = (name) => screen.findByRole("region", { name });

describe("Threat intelligence", () => {
  it("opens with one summary line and three sections: rings, timeline and counties", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    expect(await screen.findByTestId("threat-summary")).toHaveTextContent(
      "145 of 1000 agents (14.5%) flagged by the model. Their records carry 21.5% of commission paid.");
    for (const name of ["Ring candidates", "Activation timeline", "Flagged agents by county"]) {
      expect(within(await card(name)).queryByRole("alert")).not.toBeInTheDocument();
    }
    expect(document.title).toBe("Threat intelligence · SalesMesh Fraud Detection");
  });

  it("no longer shows the figure cards, flag sources, top risk agents, what drives the flags or a second county chart", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    await card("Ring candidates");
    for (const gone of ["Summary", "Flag sources", "Top risk agents", "What drives the flags", "Connected agents", "County flagged rates"]) {
      expect(screen.queryByRole("region", { name: gone })).not.toBeInTheDocument();
    }
  });

  it("shows only the first sentence when the commission share is unavailable", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/threat-intelligence/summary": { ...SUMMARY, commission_kes: undefined } }));
    renderApp("/threat-intelligence");
    expect(await screen.findByTestId("threat-summary")).toHaveTextContent(/^145 of 1000 agents \(14\.5%\) flagged by the model\.$/);
  });

  it("lists ring candidates with the agent count first, shared customers, clients and a Show button", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("2 groups among the 145 agents the model flagged.")).toBeInTheDocument();
    const table = within(rings).getByRole("table", { name: "Ring candidate groups" });
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Group", "Agents", "Shared customers", "Clients", "Graph"]);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(2);
    expect(within(rows[0]).getByText("cand_01")).toBeInTheDocument();
    expect(rows[0].textContent).toContain("3:A11607,A14278,A33509");
    expect(within(rows[0]).getByRole("link", { name: "A14278" })).toHaveAttribute("href", "/agents/A14278");
    expect(within(rows[0]).getByText("41")).toBeInTheDocument();
    expect(within(rows[0]).getByText("CL01, CL04")).toBeInTheDocument();
    expect(within(rows[1]).getByRole("button", { name: "Show the graph of cand_02" })).toBeInTheDocument();
    expect(within(rings).getByText("A candidate is a lead for review, not a confirmed ring. No labels are used.")).toBeInTheDocument();
    expect(within(rings).getByText(/all connected agents shows every group of agents, flagged or not/)).toBeInTheDocument();
  });

  it("switches the table to all connected agents, which have no graph", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    await within(rings).findByRole("table", { name: "Ring candidate groups" });
    await userEvent.click(within(rings).getByRole("button", { name: "All connected agents" }));
    const table = within(rings).getByRole("table", { name: "Connected agent groups" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows[0].textContent).toContain("Group 1");
    expect(rows[0].textContent).toContain("3:A57819,A80697,A95717");
    expect(within(rows[0]).getByText("33")).toBeInTheDocument();
    expect(within(rows[0]).queryByRole("button")).not.toBeInTheDocument();
    expect(within(rings).getByText(/279 customers were activated by more than one agent/)).toBeInTheDocument();
    expect(within(rings).getByRole("button", { name: "All connected agents" })).toHaveAttribute("aria-pressed", "true");
    // The chosen candidate's graph stays.
    expect(await card("Ring graph: cand_01")).toBeInTheDocument();
  });

  it("draws the first ring as a graph with a pairs table, members, counties and no customer id", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const graphCard = await card("Ring graph: cand_01");
    const svg = await within(graphCard).findByRole("group", { name: /Graph of ring candidate cand_01: 3 agents and 2 pairs/ });
    expect(within(svg).getAllByRole("button")).toHaveLength(3);
    // Line counts show only on hover, focus or selection.
    expect(within(svg).queryByText("30")).not.toBeInTheDocument();
    const pairs = within(graphCard).getByRole("table", { name: "Pairs in cand_01 that share customers" });
    expect(within(pairs).getAllByRole("row").slice(1).map((r) => r.textContent)).toEqual(["A11607A1427830Yes", "A11607A335092No"]);
    const members = within(graphCard).getByRole("table", { name: "Members of cand_01" });
    expect(within(members).getAllByText("Nairobi")).toHaveLength(2);
    expect(within(graphCard).getByText("2 counties: Kisumu, Nairobi.")).toBeInTheDocument();
    expect(within(graphCard).getByText("Dot size is the agent's activations. Line thickness is the shared customers.")).toBeInTheDocument();
    expect(graphCard.textContent).not.toMatch(/\bred\b|solid|dashed/i);
    expect(document.body.textContent).not.toMatch(/CUST\d/);
  });

  it("selects an agent with the keyboard: its pairs in a panel, an Open agent link, Escape clears", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const graphCard = await card("Ring graph: cand_01");
    const svg = await within(graphCard).findByRole("group", { name: /Graph of ring candidate cand_01/ });
    const node = within(svg).getByRole("button", { name: /Agent A11607, Nairobi, Model, 9 activations, shares customers with 2/ });
    // Tab order follows the agent IDs: from A14278, Shift+Tab reaches A11607.
    const second = within(svg).getByRole("button", { name: /Agent A14278/ });
    await userEvent.click(second);
    await userEvent.keyboard("{Escape}");
    await userEvent.unhover(second);
    await userEvent.tab({ shift: true });
    expect(node).toHaveFocus();
    // Focus shows the counts on the agent's lines, including its pair with A33509.
    expect(await within(svg).findByText("2")).toBeInTheDocument();
    await userEvent.keyboard("{Enter}");
    expect(node).toHaveAttribute("aria-pressed", "true");
    const panel = within(graphCard).getByRole("list", { name: "Pairs of A11607" });
    expect(within(panel).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["A1427830 shared customers", "A335092 shared customers"]);
    expect(within(graphCard).getByRole("link", { name: "Open agent" })).toHaveAttribute("href", "/agents/A11607");
    await userEvent.keyboard("{Escape}");
    expect(node).toHaveAttribute("aria-pressed", "false");
    expect(within(graphCard).queryByRole("list", { name: "Pairs of A11607" })).not.toBeInTheDocument();
    await userEvent.tab();
    expect(within(svg).getByRole("button", { name: /Agent A14278/ })).toHaveFocus();
  });

  it("fades agents that are not linked to the selected one", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const svg = await within(await card("Ring graph: cand_01")).findByRole("group", { name: /Graph of ring candidate cand_01/ });
    await userEvent.click(within(svg).getByRole("button", { name: /Agent A14278/ }));
    expect(within(svg).getByRole("button", { name: /Agent A33509/ })).toHaveAttribute("opacity", "0.2");
    expect(within(svg).getByRole("button", { name: /Agent A11607/ })).toHaveAttribute("opacity", "1");
  });

  it("draws a group of two", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    await card("Ring graph: cand_01");
    await userEvent.click(screen.getByRole("button", { name: "Show the graph of cand_02" }));
    const svg = await within(await card("Ring graph: cand_02")).findByRole("group", { name: /cand_02: 2 agents and 1 pairs/ });
    expect(within(svg).getAllByRole("button")).toHaveLength(2);
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

  it("keeps the timeline and county chart with their table views", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/threat-intelligence");
    const timeline = await card("Activation timeline");
    await userEvent.click(await within(timeline).findByRole("button", { name: "Show as table" }));
    expect(within(timeline).getByRole("table", { name: "Activation timeline data" })).toHaveTextContent("965");
    const counties = await card("Flagged agents by county");
    await userEvent.click(within(counties).getByRole("button", { name: "Show as table" }));
    const table = within(counties).getByRole("table", { name: "Flagged agents by county data" });
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["County", "Flagged agents", "All agents", "Flagged rate"]);
    expect(within(table).getAllByRole("row")[1].textContent).toBe("Lamu2540.0%");
  });

  it("shows ring candidate agent ids as plain text to an admin, with no Open agent link", async () => {
    mockApi(routes("admin"));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("A23833")).toBeInTheDocument();
    expect(within(rings).queryByRole("link")).not.toBeInTheDocument();
  });

  it("keeps the other sections when ring candidates fail, and retries them", async () => {
    let attempts = 0;
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/ring-candidates": () => (++attempts === 1 ? reply(500, { error: "Ring candidates unavailable" }) : RINGS),
    }));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    expect(await within(rings).findByText("Ring candidates unavailable")).toBeInTheDocument();
    expect(within(await card("Activation timeline")).queryByRole("alert")).not.toBeInTheDocument();
    await userEvent.click(within(rings).getByRole("button", { name: "Try again" }));
    expect(await within(rings).findByRole("link", { name: "A23833" })).toBeInTheDocument();
  });

  it("explains when the connected groups cannot be loaded", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/threat-intelligence/customer-sharing": reply(500, { error: "Groups unavailable" }) }));
    renderApp("/threat-intelligence");
    const rings = await card("Ring candidates");
    await within(rings).findByRole("table", { name: "Ring candidate groups" });
    await userEvent.click(within(rings).getByRole("button", { name: "All connected agents" }));
    expect(await within(rings).findByText("Groups unavailable")).toBeInTheDocument();
  });

  it("is open to compliance officers", async () => {
    mockApi(routes("compliance_officer"));
    renderApp("/threat-intelligence");
    expect(await screen.findByRole("heading", { name: "Threat intelligence", level: 1 })).toBeInTheDocument();
    expect(await within(await card("Ring candidates")).findByRole("link", { name: "A23833" })).toBeInTheDocument();
  });

  it("shows empty states before any run", async () => {
    mockApi(routes("fraud_analyst", {
      "GET /api/threat-intelligence/summary": { agents_scored: 0, flag_sources: {}, risk_bands: {}, top_features: { as_top_feature: [] } },
      "GET /api/threat-intelligence/timeline": { days: [] },
      "GET /api/threat-intelligence/by-region": { regions: [], top_by_flagged_rate: [] },
      "GET /api/threat-intelligence/customer-sharing": { shared_customers: 0, clusters_total: 0, clusters: [] },
      "GET /api/threat-intelligence/ring-candidates": { flagged_agents: 0, candidates_total: 0, candidates: [] },
    }));
    renderApp("/threat-intelligence");
    expect(await screen.findByText("No successful detection run yet.")).toBeInTheDocument();
    expect(await within(await card("Ring candidates")).findByText("No flagged agents share 3 or more customers.")).toBeInTheDocument();
    expect(within(await card("Activation timeline")).getByText("No activation records are loaded yet.")).toBeInTheDocument();
    expect(within(await card("Flagged agents by county")).getByText("No county has enough agents yet.")).toBeInTheDocument();
  });
});
