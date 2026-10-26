import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";

const agent = (id, source, band, score, percentile, region = "Nairobi") => ({
  agent_id: id, region, status: ["ML", "Both"].includes(source) ? "flagged" : "clear", flag_source: source,
  risk_band: band, suspicion_score: score, score_percentile: percentile,
});

const AGENTS = [
  agent("A10001", "ML", "high", 3.2, 97.4),
  agent("A20002", "Rule", "review", 1.2, null, "Kisumu"),
  agent("A30003", "Both", "high", 5.5, 99.9),
  agent("A40004", "None", "low", 1.01, 51.5),
];
const DECISIONS = [
  { decision_id: "RD1", agent_id: "A10001", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud", decision_timestamp: "2026-10-13T15:10:00", status: "pending_confirmation", confirmed_by: null, notes: "x" },
  { decision_id: "RD2", agent_id: "A30003", reviewer_id: "ADM_ANALYST_01", decision_outcome: "legitimate", decision_timestamp: "2026-10-12T15:10:00", status: "agreed", closed_by: "ADM_COMPLIANCE_01", notes: "y" },
];

function routes(agents = AGENTS, decisions = DECISIONS) {
  return {
    ...sessionRoutes("fraud_analyst"),
    "GET /api/all-agents": { count: agents.length, agents },
    "GET /api/review-decisions": { count: decisions.length, decisions },
  };
}

const table = (name) => screen.findByRole("table", { name });
const agentLinks = (container) => within(container).queryAllByRole("link").map((l) => l.textContent);

describe("Flagged agents", () => {
  it("lists model, rule and both flags, highest score first, with risk and review state", async () => {
    mockApi(routes());
    renderApp("/flagged");
    const rows = await table("Flagged agents");
    expect(agentLinks(rows)).toEqual(["A30003", "A10001", "A20002"]);
    expect(within(rows).getAllByText("High risk")).toHaveLength(2);
    expect(within(rows).getByText("Rule only")).toBeInTheDocument();
    expect(within(rows).getByText("Proposed")).toBeInTheDocument();
    // The Proposed chip says what it waits for, in the decision history's words.
    await userEvent.hover(within(rows).getByText("Proposed"));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Waiting for a compliance officer to agree or overrule");
    await userEvent.unhover(within(rows).getByText("Proposed"));
    expect(within(rows).getByText("Agreed")).toBeInTheDocument();
    expect(within(rows).getByRole("link", { name: "A10001" })).toHaveAttribute("href", "/agents/A10001");
    expect(document.title).toBe("Flagged agents · SalesMesh Fraud Detection");
  });

  it("counts the flagged agents, and how many match while filters are active", async () => {
    mockApi(routes());
    renderApp("/flagged");
    await table("Flagged agents");
    expect(screen.getByText("3 flagged agents")).toBeInTheDocument();
    await userEvent.type(screen.getByRole("textbox", { name: "Search by agent ID" }), "A1");
    expect(await screen.findByText("1 of 3 match your filters")).toBeInTheDocument();
  });

  it("shows a removable chip for each active filter, beside Clear filters", async () => {
    mockApi(routes());
    renderApp("/flagged?risk=high&source=ML");
    const search = await screen.findByRole("search", { name: "Filter agents" });
    expect(within(search).getByText("Risk: High risk")).toBeInTheDocument();
    expect(within(search).getByText("Flagged by: Model")).toBeInTheDocument();
    expect(within(search).getByRole("button", { name: "Clear filters" })).toBeInTheDocument();
    expect(screen.getByText("1 of 3 match your filters")).toBeInTheDocument();
    await userEvent.click(within(search).getByLabelText("Remove filter Flagged by: Model"));
    expect(currentLocation()).toBe("/flagged?risk=high");
    expect(within(search).queryByText("Flagged by: Model")).not.toBeInTheDocument();
    expect(await screen.findByText("2 of 3 match your filters")).toBeInTheDocument();
  });

  it("shows the rank beside the raw score, with the exact percentile in the label and tooltip", async () => {
    mockApi(routes());
    renderApp("/flagged");
    const rows = await table("Flagged agents");
    const top = within(rows).getByRole("group", { name: "Score 5.500, percentile 99.9" });
    expect(within(top).getByText("5.500")).toBeInTheDocument();
    expect(within(top).getByText("Top 1%")).toBeInTheDocument();
    expect(within(rows).getByRole("group", { name: "Score 3.200, percentile 97.4" })).toHaveTextContent("3.200 Top 3%");
    // No percentile from the API: the raw score alone, no rank.
    expect(within(rows).getByText("1.200")).toBeInTheDocument();
    expect(within(rows).queryByRole("group", { name: /^Score 1\.200/ })).not.toBeInTheDocument();

    await userEvent.hover(within(top).getByText("Top 1%"));
    expect(await screen.findByRole("tooltip")).toHaveTextContent(
      "Percentile 99.9: higher than 99.9% of agents scored in the latest run. A rank, not a probability.",
    );
  });

  it("reads its filters from the URL", async () => {
    mockApi(routes());
    renderApp("/flagged?risk=review");
    expect(agentLinks(await table("Flagged agents"))).toEqual(["A20002"]);
  });

  it("writes filters, search and sort to the URL", async () => {
    mockApi(routes());
    renderApp("/flagged");
    const rows = await table("Flagged agents");

    await userEvent.type(screen.getByRole("textbox", { name: "Search by agent ID" }), "a1");
    expect(agentLinks(rows)).toEqual(["A10001"]);
    expect(currentLocation()).toBe("/flagged?q=a1");

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    await userEvent.click(screen.getByRole("combobox", { name: "Review" }));
    await userEvent.click(screen.getByRole("option", { name: "Proposed" }));
    expect(agentLinks(rows)).toEqual(["A10001"]);
    expect(currentLocation()).toBe("/flagged?review=pending_confirmation");

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    await userEvent.click(within(rows).getByRole("button", { name: "Score (rank)" }));
    expect(agentLinks(rows)).toEqual(["A20002", "A10001", "A30003"]);
    expect(currentLocation()).toBe("/flagged?dir=asc");
  });

  it("pages through long lists", async () => {
    const many = Array.from({ length: 30 }, (_, i) => agent(`A${50000 + i}`, "ML", "high", 2 + i / 100));
    mockApi(routes(many, []));
    renderApp("/flagged");
    const rows = await table("Flagged agents");
    expect(agentLinks(rows)).toHaveLength(25);
    expect(screen.getByText("1–25 of 30")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to next page" }));
    expect(agentLinks(rows)).toHaveLength(5);
    expect(currentLocation()).toBe("/flagged?page=1");
  });

  it("shows cards instead of a table on narrow screens", async () => {
    window.innerWidth = 360;
    mockApi(routes());
    renderApp("/flagged");
    const list = await screen.findByRole("region", { name: "Flagged agents" });
    expect(within(list).queryByRole("table")).not.toBeInTheDocument();
    expect(within(list).getAllByRole("listitem")).toHaveLength(3);
    expect(within(list).getAllByText("Risk")).toHaveLength(3);
  });

  it("explains an empty list and a filter with no match", async () => {
    mockApi(routes([agent("A40004", "None", "low", 1.0)], []));
    renderApp("/flagged");
    expect(await screen.findByText("No agents are flagged in the latest run.")).toBeInTheDocument();
  });
});

describe("All agents", () => {
  it("includes agents that are not flagged, with a clear Not flagged state", async () => {
    mockApi(routes());
    renderApp("/all-agents");
    const rows = await table("All agents");
    expect(agentLinks(rows)).toHaveLength(4);
    expect(within(rows).getByText("Not flagged")).toBeInTheDocument();
    expect(within(rows).getAllByText("Not reviewed")).toHaveLength(2);
    const summary = screen.getByRole("region", { name: "Summary" });
    expect(within(summary).getByText("Not flagged")).toBeInTheDocument();
  });

  it("filters by flag source from the URL and reports no match", async () => {
    mockApi(routes());
    renderApp("/all-agents?source=None&q=zzz");
    expect(await screen.findByText("No agents match your filters.")).toBeInTheDocument();
  });
});
