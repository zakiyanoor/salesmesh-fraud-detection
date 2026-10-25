import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const section = (name) => screen.findByRole("region", { name });

describe("How the model works", () => {
  it.each(["fraud_analyst", "compliance_officer", "admin"])("is in the menu of a %s and opens from it", async (role) => {
    mockApi(sessionRoutes(role));
    renderApp("/");
    await screen.findByRole("heading", { name: "Overview" });
    await userEvent.click(within(screen.getByRole("navigation", { name: "Main menu" })).getByRole("link", { name: "How the model works" }));
    expect(await screen.findByRole("heading", { level: 1, name: "How the model works" })).toBeInTheDocument();
    expect(document.title).toBe("How the model works · SalesMesh Fraud Detection");
  });

  it("explains in plain words that people decide and that detection runs on a schedule", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/how-it-works");
    const what = await section("What the system does");
    expect(within(what).getByText(/People decide\./)).toBeInTheDocument();
    expect(await within(what).findByText(/Detection runs on a schedule, not live: once a day by default/)).toBeInTheDocument();
    const signals = await section("The four signals");
    for (const name of ["Busiest 24 hours", "Spread of working hours", "Look-alike customer IDs", "Customers shared with other agents"]) {
      expect(within(signals).getByText(name)).toBeInTheDocument();
    }
    expect(within(await section("The duplicate activation rule")).getByText(/same customer and client pair/)).toBeInTheDocument();
    expect(within(await section("Flag sources and risk bands")).getByText(/Model, Rule only, Both/)).toBeInTheDocument();
  });

  it("shows the cutoff from the API and says scores are not probabilities", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/how-it-works");
    const scores = await section("Scores and the cutoff");
    expect(within(scores).getByText("Scores and ranks are not probabilities. A score does not say how likely an agent is to be committing fraud.")).toBeInTheDocument();
    expect(await within(scores).findByText("1.445")).toBeInTheDocument();
    expect(within(scores).getByText(/min expected cost 5:1/)).toBeInTheDocument();
  });

  it("shows the test results from the API, where they were measured, and a glossary", async () => {
    mockApi(sessionRoutes("compliance_officer"));
    renderApp("/how-it-works");
    const results = await section("How well it did on test agents");
    const rows = within(await within(results).findByRole("table", { name: "Test results" })).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      "Model250.60 (15 of 25)0.79 (15 of 19)0.85 (0.68 to 0.96)0.95 (0.90 to 0.99)",
      "Duplicate activation rule161.00 (16 of 16)0.84 (16 of 19)0.86 (0.70 to 1.00)0.92 (0.82 to 1.00)",
      "Model or rule (the system)290.66 (19 of 29)1.00 (19 of 19)not comparablenot comparable",
    ]);
    expect(within(results).getByText(/Measured on the 150 held-out test agents, scored once with the frozen model; not a promise for other data\./)).toBeInTheDocument();
    const glossary = await section("Glossary");
    for (const term of ["Precision", "Recall", "PR AUC", "ROC AUC"]) expect(within(glossary).getByText(term)).toBeInTheDocument();
  });

  it("keeps the plain-language sections when the figures cannot be loaded", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": reply(500, { error: "Figures unavailable" }) });
    renderApp("/how-it-works");
    expect(await within(await section("How well it did on test agents")).findByText("Figures unavailable")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Glossary" })).toBeInTheDocument();
    expect(screen.getByText(/Detection runs on a schedule, not live\./)).toBeInTheDocument();
  });
});
