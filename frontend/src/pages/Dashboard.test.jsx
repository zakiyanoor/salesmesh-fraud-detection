import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FIXTURES, mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const section = (name) => screen.getByRole("region", { name });

describe("Overview", () => {
  it("shows the summary cards, both charts and the needs-attention list", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    const summary = await screen.findByRole("region", { name: "Summary" });
    expect(await within(summary).findByText("1000")).toBeInTheDocument();
    expect(within(summary).getByText("145")).toBeInTheDocument();
    expect(within(summary).getByText("89")).toBeInTheDocument();
    expect(within(summary).getByText("29")).toBeInTheDocument();
    expect(within(summary).getByText("Succeeded")).toBeInTheDocument();
    expect(within(summary).getByText("Last detection run")).toBeInTheDocument();
    // The five figures with their labels, in order, and no icons.
    expect([...summary.querySelectorAll("p")].map((p) => p.textContent).filter((t) => /^\d+$/.test(t))).toEqual(["1000", "145", "89", "29"]);
    for (const label of ["Agents scored", "Flagged (high risk)", "Review band", "Rule-only flags"]) {
      expect(within(summary).getByText(label)).toBeInTheDocument();
    }
    expect(within(summary).getByText("Flagged by the model. Rule only flags are counted separately.")).toBeInTheDocument();
    expect(within(summary).getByText("13 Oct 2026, 18:07")).toBeInTheDocument();
    expect(summary.querySelector("svg")).toBeNull();

    expect(within(section("Flag sources")).getByText("Model and rule")).toBeInTheDocument();
    expect(within(section("Risk bands")).queryByRole("alert")).not.toBeInTheDocument();
    expect(document.title).toBe("Overview · SalesMesh Fraud Detection");

    const attention = section("Needs attention");
    expect(within(attention).getByRole("link", { name: "A35485" })).toHaveAttribute("href", "/agents/A35485");
    expect(within(attention).getByRole("link", { name: "A10001" })).toBeInTheDocument();
    expect(within(attention).getByRole("group", { name: "Score 5.564, percentile 98.9" })).toHaveTextContent("5.564 Top 2%");
    // Only high-risk agents are listed.
    expect(within(attention).queryByText("A20002")).not.toBeInTheDocument();
    expect(within(attention).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Agent ID", "Score (rank)", "Risk", "Flagged by"]);
    // Flagged by is a chip, as on the other pages.
    expect(within(attention).getAllByText("Model and rule")[0].closest(".MuiChip-root")).not.toBeNull();
  });

  it("draws each score against the cutoff read from the model information, with a text value", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    await within(attention).findByRole("link", { name: "A35485" });
    expect(await within(attention).findAllByText("At or above the model cutoff of 1.445")).not.toHaveLength(0);
  });

  it("uses the cutoff from the API, not a constant", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": { ...FIXTURES["GET /api/model-info"], cutoff: 9.5, test_agents: 150 } });
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    expect(await within(attention).findAllByText("Below the model cutoff of 9.500")).not.toHaveLength(0);
  });

  it("links to all flagged agents and notes where accuracy figures come from", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    expect(await screen.findByRole("link", { name: "See all flagged agents" })).toHaveAttribute("href", "/flagged");
    await waitFor(() => expect(screen.getByTestId("training-note")).toHaveTextContent(
      "These figures include agents the model learned from. Accuracy figures come only from the 150 test agents."));
  });

  it("shows only the first sentence of the note when the test size cannot be read", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": reply(500, { error: "Unavailable" }) });
    renderApp("/");
    await screen.findByRole("region", { name: "Needs attention" });
    await waitFor(() => expect(screen.getByTestId("training-note")).toHaveTextContent(/^These figures include agents the model learned from\.$/));
  });

  it("says how old the latest run is when it is more than 48 hours old", async () => {
    const old = new Date(Date.now() - 5 * 24 * 3_600_000 - 60_000).toISOString().replace("Z", "");
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/detection-runs/latest": { run: { ...FIXTURES["GET /api/detection-runs/latest"].run, started_at: old, finished_at: old } } });
    renderApp("/");
    expect(await screen.findByTestId("stale-run")).toHaveTextContent("The latest detection run is 5 days old. The figures below describe that run.");
    expect(screen.getByTestId("stale-run")).not.toHaveAttribute("role", "alert");
  });

  it("says nothing about age for a recent run", async () => {
    const recent = new Date(Date.now() - 3 * 3_600_000).toISOString().replace("Z", "");
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/detection-runs/latest": { run: { ...FIXTURES["GET /api/detection-runs/latest"].run, started_at: recent, finished_at: recent } } });
    renderApp("/");
    expect(await within(await screen.findByRole("region", { name: "Summary" })).findByText("Succeeded")).toBeInTheDocument();
    expect(screen.queryByTestId("stale-run")).not.toBeInTheDocument();
  });

  it("keeps the chart table views", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    const sources = await screen.findByRole("region", { name: "Flag sources" });
    await userEvent.click(await within(sources).findByRole("button", { name: "Show as table" }));
    expect(within(sources).getByRole("table", { name: "Flag sources data" })).toBeInTheDocument();
    const bands = section("Risk bands");
    await userEvent.click(within(bands).getByRole("button", { name: "Show as table" }));
    expect(within(bands).getByRole("table", { name: "Risk bands data" })).toHaveTextContent("High risk");
    expect(within(bands).getByText("Review: rule only or score 1.3 and above")).toBeInTheDocument();
  });

  it("fetches the latest detection run once for the card and the footer", async () => {
    const { calls } = mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    const summary = await screen.findByRole("region", { name: "Summary" });
    expect(await within(summary).findByText("Succeeded")).toBeInTheDocument();
    expect(await within(screen.getByRole("contentinfo")).findByText(/^Model lof_v3_4f · Last detection run /)).toBeInTheDocument();
    expect(await within(section("Needs attention")).findByRole("link", { name: "A35485" })).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/api/detection-runs/latest")).toHaveLength(1);
  });

  it("shows plain agent ids to an admin, who cannot open agent detail", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    expect(await within(attention).findByText("A35485")).toBeInTheDocument();
    expect(within(attention).queryByRole("link")).not.toBeInTheDocument();
  });

  it("keeps the other cards when one request fails, and retries it", async () => {
    let attempts = 0;
    mockApi({
      ...sessionRoutes("compliance_officer"),
      "GET /api/agent-scores": () => (++attempts === 1 ? reply(500, { error: "Scores unavailable" }) : {
        scores: [{ agent_id: "A35485", anomaly_score: 5.5, flag_source: "Both", risk_band: "high" }],
      }),
    });
    renderApp("/");
    const attention = await screen.findByRole("region", { name: "Needs attention" });
    expect(await within(attention).findByText("Scores unavailable")).toBeInTheDocument();
    expect(within(section("Flag sources")).getByText("Model and rule")).toBeInTheDocument();
    await userEvent.click(within(attention).getByRole("button", { name: "Try again" }));
    expect(await within(attention).findByRole("link", { name: "A35485" })).toBeInTheDocument();
  });

  it("shows empty states before any run has scored agents", async () => {
    mockApi({
      ...sessionRoutes("fraud_analyst"),
      "GET /api/threat-intelligence/summary": { agents_scored: 0, flag_sources: {}, risk_bands: {} },
      "GET /api/detection-runs/latest": { run: null },
      "GET /api/agent-scores": { scores: [] },
    });
    renderApp("/");
    expect(await within(await screen.findByRole("region", { name: "Flag sources" })).findByText("No detection run has scored any agents yet.")).toBeInTheDocument();
    expect(within(section("Needs attention")).getByText("No agent is in the high-risk band.")).toBeInTheDocument();
    expect(within(section("Summary")).getByText("None yet")).toBeInTheDocument();
  });
});
