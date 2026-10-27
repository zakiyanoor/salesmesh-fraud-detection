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
    expect(within(review).getByTestId("overrule-rate")).toHaveTextContent("33.3%");
    expect(within(review).getByText("of compliance decisions overruled")).toBeInTheDocument();
    expect(within(review).getByText("1 of 3")).toBeInTheDocument();
    expect(within(review).getByText("Agreed 2")).toBeInTheDocument();
    expect(within(review).getByText("Overruled 1")).toBeInTheDocument();
    expect(within(review).getAllByText("Overruled means a compliance officer disagreed with the analyst's proposal.")).toHaveLength(1);
    expect(within(review).getByText("Open and withdrawn proposals are not counted.")).toBeInTheDocument();
    expect(within(review).getByText("How compliance decisions compare with analyst proposals.")).toBeInTheDocument();
    const averages = await card("Average behaviour across all agents");
    expect(within(averages).getByText("From the latest detection run.")).toBeInTheDocument();
    expect(within(averages).getByRole("article", { name: "Busiest 24 hours" })).toHaveTextContent("Busiest 24 hours14.0activations in 24 hours");
    expect(within(averages).getByRole("article", { name: "Look-alike customer IDs" })).toBeInTheDocument();
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
    // The column names stay; the values use the shared plain names.
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Strongest feature", "Flagged agents"]);
    expect(within(table).getAllByRole("row")[1].textContent).toBe("Customers shared with other agents70");
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

describe("Review outcomes", () => {
  const withReview = (review) => ({ "GET /api/analytics": { ...FIXTURES["GET /api/analytics"], review: { ...FIXTURES["GET /api/analytics"].review, ...review } } });

  it.each([
    [{ agreed: 4, overruled: 1 }, "20%", "1 of 5"],
    [{ agreed: 2, overruled: 1 }, "33.3%", "1 of 3"],
    [{ agreed: 0, overruled: 2 }, "100%", "2 of 2"],
  ])("follows the decisions: %j gives %s", async (review, rate, count) => {
    mockApi(routes("fraud_analyst", withReview(review)));
    renderApp("/analytics");
    const card = await screen.findByRole("region", { name: "Review outcomes" });
    expect(await within(card).findByTestId("overrule-rate")).toHaveTextContent(new RegExp(`^${rate.replace(".", "\\.")}$`));
    expect(within(card).getByText(count)).toBeInTheDocument();
  });

  it("says no decisions yet instead of a rate or a bar, and never NaN or 0%", async () => {
    mockApi(routes("fraud_analyst", withReview({ agreed: 0, overruled: 0, overrule_rate: null })));
    renderApp("/analytics");
    const card = await screen.findByRole("region", { name: "Review outcomes" });
    expect(await within(card).findByTestId("overrule-rate")).toHaveTextContent("No decisions yet");
    expect(card.textContent).not.toMatch(/NaN|0%|Agreed 0/);
  });

  it("shows the other states as tiles, with overdue in the warning colour only above 0", async () => {
    mockApi(routes("fraud_analyst", withReview({ open: 3, overdue: 0, withdrawn: 2, corrections: 1 })));
    renderApp("/analytics");
    const card = await screen.findByRole("region", { name: "Review outcomes" });
    await within(card).findByText("Open");
    for (const [label, value] of [["Open", "3"], ["Overdue", "0"], ["Withdrawn", "2"], ["Corrections", "1"]]) {
      expect(within(card).getByText(label).nextSibling).toHaveTextContent(value);
    }
    expect(within(card).queryByText(/^Agreed$|^Overruled$/)).not.toBeInTheDocument();
  });
});
