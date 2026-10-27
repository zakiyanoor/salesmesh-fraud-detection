import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FIXTURES, currentLocation, mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const section = (name) => screen.findByRole("region", { name });

describe("Detection guide", () => {
  it.each([
    ["fraud_analyst", "Review history"], ["compliance_officer", "Confirm queue"], ["admin", "Accounts"],
  ])("is the last menu item of a %s and opens from it", async (role) => {
    mockApi(sessionRoutes(role));
    renderApp("/");
    await screen.findByRole("heading", { name: "Overview" });
    const menu = within(screen.getByRole("navigation", { name: "Main menu" })).getAllByRole("link");
    expect(menu.at(-1)).toHaveTextContent("Detection guide");
    await userEvent.click(menu.at(-1));
    expect(await screen.findByRole("heading", { level: 1, name: "Detection guide" })).toBeInTheDocument();
    expect(currentLocation()).toBe("/detection-guide");
    expect(document.title).toBe("Detection guide · SalesMesh Fraud Detection");
  });

  it("sends the old address to the new one", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/how-it-works");
    expect(await screen.findByRole("heading", { level: 1, name: "Detection guide" })).toBeInTheDocument();
    expect(currentLocation()).toBe("/detection-guide");
  });

  it("has the sections in order, and no other text", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/detection-guide");
    expect(await screen.findByText("How agents are flagged, and how to read the numbers.")).toBeInTheDocument();
    const titles = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(titles).toEqual([
      "How a flag is made", "What the model looks at", "Flag sources and risk bands", "Reading a score",
      "How well it did on test agents", "Glossary",
    ]);
    expect(screen.queryByText(/What the system does|People decide|learned from/)).not.toBeInTheDocument();
  });

  it("shows the five steps and how often detection runs, from the API", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/detection-guide");
    const steps = await section("How a flag is made");
    expect(within(steps).getAllByRole("listitem").map((li) => li.querySelectorAll("p")[1].textContent)).toEqual([
      "Collect activations", "Compare with other agents", "Score", "Flag at the cutoff", "A person reviews",
    ]);
    expect(await within(steps).findByText("Detection runs once a day. Every page shows the latest run.")).toBeInTheDocument();
  });

  it("describes the four signals with when each is unusual, and the duplicate rule", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/detection-guide");
    const signals = await section("What the model looks at");
    for (const name of ["Busiest 24 hours", "Spread of working hours", "Look-alike customer IDs", "Customers shared with other agents"]) {
      const cardEl = within(signals).getByRole("article", { name });
      expect(within(cardEl).getByText(/^Unusual when /)).toBeInTheDocument();
    }
    expect(within(signals).getByRole("article", { name: "The duplicate activation rule" })).toHaveTextContent(/same customer and client pair/);
    const sources = within(await section("Flag sources and risk bands")).getByRole("table", { name: "Flag sources and risk bands" });
    expect(within(sources).getAllByRole("row").slice(1).map((r) => r.cells[0].textContent)).toEqual(["Model", "Rule only", "Model and rule", "Not flagged"]);
  });

  it("marks a typical agent and the cutoff from the API, and says scores are not probabilities once", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": { ...FIXTURES["GET /api/model-info"], cutoff: 1.5 } });
    renderApp("/detection-guide");
    const reading = await section("Reading a score");
    expect(await within(reading).findByText("Cutoff, 1.500")).toBeInTheDocument();
    expect(within(reading).getByText("Typical agent, about 1")).toBeInTheDocument();
    expect(screen.getAllByText("Scores and ranks are not probabilities. A flag asks a person to look; it is not a finding of fraud.")).toHaveLength(1);
  });

  it("summarises precision and recall with counts, and reveals the full results", async () => {
    mockApi(sessionRoutes("compliance_officer"));
    renderApp("/detection-guide");
    const results = await section("How well it did on test agents");
    const model = await within(results).findByRole("article", { name: "Model" });
    expect(model).toHaveTextContent("Precision0.6015 of 25Recall0.7915 of 19");
    expect(within(results).getByRole("article", { name: "Duplicate activation rule" })).toHaveTextContent("Precision1.0016 of 16");
    expect(within(results).getByRole("article", { name: "Model or rule" })).toHaveTextContent("Recall1.0019 of 19");
    expect(within(results).getByText("Measured once on 150 held out test agents, 19 of them fraud.")).toBeInTheDocument();
    expect(within(results).getByText("Not a promise for other data.")).toBeInTheDocument();
    expect(within(results).queryByRole("table")).not.toBeInTheDocument();
    await userEvent.click(within(results).getByRole("button", { name: "Show full results" }));
    const rows = within(within(results).getByRole("table", { name: "Test results" })).getAllByRole("row").slice(1);
    expect(rows[0].textContent).toBe("Model250.60 (15 of 25)0.79 (15 of 19)0.85 (0.68 to 0.96)0.95 (0.90 to 0.99)");
    expect(within(results).getByText(/min expected cost 5:1/)).toBeInTheDocument();
  });

  it("has a collapsible glossary and a footer with the model and the last run", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/detection-guide");
    const glossary = await section("Glossary");
    const precision = within(glossary).getByRole("button", { name: "Precision" });
    expect(precision).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(precision);
    expect(precision).toHaveAttribute("aria-expanded", "true");
    expect(within(glossary).getByText(/the share that were really fraud/)).toBeVisible();
    expect(await screen.findByTestId("guide-footer")).toHaveTextContent("Model lof_v3_4f. Last detection run 13 Oct 2026, 18:07");
  });

  it("keeps the plain-language sections when the figures cannot be loaded", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/model-info": reply(500, { error: "Figures unavailable" }) });
    renderApp("/detection-guide");
    expect(await within(await section("How well it did on test agents")).findByText("Figures unavailable")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "What the model looks at" })).toBeInTheDocument();
  });
});
