import { describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { configureAxe } from "vitest-axe";
import * as matchers from "vitest-axe/matchers";
import { mockApi, renderApp, sessionRoutes } from "./server";

expect.extend(matchers);

// jsdom cannot compute colours, so contrast is checked by theme.test.js instead of axe.
const axe = configureAxe({ rules: { "color-contrast": { enabled: false } } });

const DECISION = {
  decision_id: "RD1", agent_id: "A10001", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
  decision_timestamp: "2026-10-13T15:10:00", status: "pending_confirmation", confirmed_by: null, notes: "Shared customers.",
};
const DATA = {
  "GET /api/review-decisions": { count: 1, decisions: [DECISION] },
  "GET /api/threat-intelligence/timeline": { days: [{ date: "2026-08-01", flagged_agents: 965, other_agents: 3534 }] },
  "GET /api/threat-intelligence/by-region": { regions: [], top_by_flagged_rate: [{ region: "Lamu", agents: 5, flagged: 2, flagged_rate: 0.4 }] },
  "GET /api/threat-intelligence/customer-sharing": {
    shared_customers: 3, clusters_total: 1, clusters: [{ size: 2, agent_ids: ["A10001", "A20002"], client_ids: ["CL01"], customer_count: 3, flagged_agents: 1 }],
  },
  "GET /api/threat-intelligence/ring-candidates": {
    rule: "...", min_shared_customers: 3, flagged_agents: 145, candidates_total: 1,
    candidates: [{ candidate_id: "cand_01", size: 2, agent_ids: ["A10001", "A20002"], shared_customers: 4, client_ids: ["CL01"] }],
  },
  "GET /api/threat-intelligence/ring-candidates/cand_01": {
    run_id: "RUN1", candidate_id: "cand_01", size: 2, rule: "...", min_shared_customers: 3,
    nodes: [
      { agent_id: "A10001", county: "Nairobi", flag_source: "ML", risk_band: "high", activations: 3, linked_members: 1 },
      { agent_id: "A20002", county: "Lamu", flag_source: "Rule", risk_band: "review", activations: 2, linked_members: 1 },
    ],
    edges: [{ source: "A10001", target: "A20002", shared_customers: 4, meets_rule: true }],
    counties: ["Lamu", "Nairobi"], county_count: 2, county_note: "County is information only. The model never uses it.",
    first_day: "2026-08-01", last_day: "2026-08-01", days: [{ date: "2026-08-01", activations: 5, by_agent: { A10001: 3, A20002: 2 } }],
    note: "Days are as recorded in the data.",
  },
  "GET /api/audit-log": {
    total: 1, count: 1, offset: 0, limit: 25,
    entries: [{ log_id: "AL1", timestamp: "2026-10-13T15:00:00", actor: "ADM_ANALYST_01", actor_type: "user", category: "review", action: "propose_decision", target_agent_id: "A10001", request_ip: "127.0.*.*", details: { decision_id: "RD1", notes: "Shared customers." } }],
  },
};

async function expectNoViolations() {
  // Let lazy pages, charts and requests settle before scanning.
  await waitFor(() => expect(document.querySelectorAll("[aria-busy=true]")).toHaveLength(0));
  expect(await axe(document.body)).toHaveNoViolations();
}

const PAGES = [
  ["fraud_analyst", "/", "Overview"],
  ["fraud_analyst", "/flagged", "Flagged agents"],
  ["fraud_analyst", "/all-agents", "All agents"],
  ["fraud_analyst", "/agents/A10001", "Agent A10001"],
  ["fraud_analyst", "/history", "Review history"],
  ["fraud_analyst", "/analytics", "Analytics"],
  ["compliance_officer", "/threat-intelligence", "Threat intelligence"],
  ["compliance_officer", "/review/confirm", "Confirm queue"],
  ["admin", "/audit-log", "Audit log"],
  ["admin", "/detection-guide", "Detection guide"],
  ["admin", "/reports", "Reports"],
  ["admin", "/accounts", "Accounts"],
  ["admin", "/flagged", "Access denied"],
  ["fraud_analyst", "/no-such-page", "Page not found"],
];

describe("accessibility (axe)", () => {
  it.each(PAGES)("%s on %s has no violations, one h1 and all landmarks", async (role, path, title) => {
    mockApi({ ...sessionRoutes(role), ...DATA });
    renderApp(path);
    expect(await screen.findByRole("heading", { level: 1, name: title })).toBeInTheDocument();
    await expectNoViolations();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Main menu" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
  });

  it.each([
    ["light", 360], ["light", 1280], ["dark", 360], ["dark", 1280],
  ])("the landing page has no violations in the %s scheme at %ipx", async (scheme, width) => {
    window.localStorage.setItem("salesmesh.colorMode", scheme);
    window.innerWidth = width;
    mockApi(sessionRoutes(null));
    renderApp("/");
    await screen.findByRole("heading", { level: 1, name: /^Fraud detection for sales agent networks/ });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it.each(["light", "dark"])("the sign-in page has no violations in the %s scheme", async (scheme) => {
    window.localStorage.setItem("salesmesh.colorMode", scheme);
    mockApi(sessionRoutes(null));
    renderApp("/sign-in");
    await screen.findByRole("button", { name: "Sign in" });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("a signed-in page with charts and the ring graph has no violations in the dark scheme", async () => {
    window.localStorage.setItem("salesmesh.colorMode", "dark");
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/threat-intelligence");
    await screen.findByRole("group", { name: /Graph of ring candidate cand_01/ });
    await expectNoViolations();
  });

  it("the phone layout has no violations, with the menu open", async () => {
    window.innerWidth = 360;
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/");
    await screen.findByRole("heading", { level: 1, name: "Overview" });
    await expectNoViolations();
    await userEvent.click(screen.getByRole("button", { name: "Open menu" }));
    await screen.findByRole("navigation", { name: "Main menu" });
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("the overview in the dark scheme, with both chart tables open, has no violations", async () => {
    window.localStorage.setItem("salesmesh.colorMode", "dark");
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    await within(attention).findAllByRole("link");
    for (const name of ["Flag sources", "Risk bands"]) {
      await userEvent.click(within(screen.getByRole("region", { name })).getByRole("button", { name: "Show as table" }));
    }
    await expectNoViolations();
  });

  it("the overview's compact list on a phone has no violations", async () => {
    // useMediaQuery reads matchMedia: report a phone width so Needs attention renders as a list.
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      matches: /max-width:\s*599/.test(query), media: query, onchange: null,
      addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {}, dispatchEvent: () => false,
    }));
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    const list = await within(attention).findByRole("list", { name: "Agents that need attention" });
    expect(within(list).getAllByRole("listitem").length).toBeGreaterThan(0);
    expect(within(attention).queryByRole("table")).not.toBeInTheDocument();
    await expectNoViolations();
    vi.restoreAllMocks();
  });

  it("the audit drawer and a chart's table view have no violations", async () => {
    mockApi({ ...sessionRoutes("admin"), ...DATA });
    renderApp("/audit-log");
    const table = await screen.findByRole("table", { name: "Audit events" });
    await userEvent.click(within(table).getByRole("button", { name: /^Details of/ }));
    await screen.findByRole("dialog");
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it("charts have a text alternative and a table view", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/threat-intelligence");
    const card = await screen.findByRole("region", { name: "Flagged agents by county" });
    expect(await within(card).findByRole("img", { name: /Flagged agents by county chart/ })).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Show as table" }));
    const data = within(card).getByRole("table", { name: "Flagged agents by county data" });
    expect(within(data).getByText("Lamu")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Show as chart" })).toHaveAttribute("aria-pressed", "true");
    await expectNoViolations();
  });

  it("the skip link is the first stop and moves to the main content", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/history");
    await screen.findByRole("heading", { level: 1, name: "Review history" });
    await userEvent.tab();
    const skip = screen.getByRole("link", { name: "Skip to content" });
    expect(skip).toHaveFocus();
    expect(skip).toHaveAttribute("href", "#main-content");
    expect(screen.getByRole("main")).toHaveAttribute("id", "main-content");
  });

  it("the ring table showing all connected agents has no violations", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/threat-intelligence");
    const rings = await screen.findByRole("region", { name: "Ring candidates" });
    await within(rings).findByRole("table", { name: "Ring candidate groups" });
    await userEvent.click(within(rings).getByRole("button", { name: "All connected agents" }));
    await within(rings).findByRole("table", { name: "Connected agent groups" });
    await expectNoViolations();
  });

  it("the ring graph with a selected agent has no violations", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/threat-intelligence");
    const svg = await screen.findByRole("group", { name: /Graph of ring candidate cand_01/ });
    await userEvent.click(within(svg).getByRole("button", { name: /Agent A10001/ }));
    await expectNoViolations();
  });

  it("the customer dialog on agent detail has no violations", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), ...DATA });
    renderApp("/agents/A10001");
    await userEvent.click(await screen.findByRole("button", { name: "Open customer CUST10000001" }));
    await within(await screen.findByRole("dialog")).findByText(/Used by 2 agents/);
    expect(await axe(document.body)).toHaveNoViolations();
  });

  it.each(["Agree with", "Overrule"])("the %s dialog in the confirm queue has no violations", async (action) => {
    mockApi({ ...sessionRoutes("compliance_officer"), ...DATA });
    renderApp("/review/confirm");
    await userEvent.click(await screen.findByRole("button", { name: `${action} the proposal for A10001` }));
    await screen.findByRole("dialog");
    expect(await axe(document.body)).toHaveNoViolations();
  });
});
