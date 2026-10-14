import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

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

    expect(within(section("Flag sources")).getByText("Model and rule")).toBeInTheDocument();
    expect(within(section("Risk bands")).queryByRole("alert")).not.toBeInTheDocument();
    expect(document.title).toBe("Overview · SalesMesh Fraud Detection");

    const attention = section("Needs attention");
    expect(within(attention).getByRole("link", { name: "A35485" })).toHaveAttribute("href", "/agents/A35485");
    expect(within(attention).getByRole("link", { name: "A10001" })).toBeInTheDocument();
    // Only high-risk agents are listed.
    expect(within(attention).queryByText("A20002")).not.toBeInTheDocument();
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
