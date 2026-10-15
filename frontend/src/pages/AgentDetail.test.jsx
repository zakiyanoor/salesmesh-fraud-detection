import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";
import { PROPOSED_MESSAGE } from "../review";

const DETAIL = {
  agent_id: "A35485", region: "Elgeyo-Marakwet", account_status: "active", risk_band: "high",
  registration_timestamp: "2026-06-11T20:56:24",
  identity: { full_name: "Agnes Omondi", phone_number: "**********067", national_id_number: "*****291" },
  features: { submission_frequency: 21, time_of_day_dist: 0.788, customer_similarity: 0.103, collusion_score: 0.464 },
  flag: { flag_id: "FL93b6b96d", flag_status: "flagged", model_version: "lof_v3_4f", suspicion_score: 5.564 },
  score: {
    anomaly_score: 5.563827, threshold: 1.444799, flagged: true, rule_flagged: true, duplicate_pairs: 19,
    flag_source: "Both", risk_band: "high", reasons: "46% of customers also used by other agents vs typical 0%",
  },
  duplicate_evidence: [
    { customer_id: "CUST16131148", client_id: "CL09", other_agent_id: "A62923", reason: "shared customer", record_ids: ["R1", "R2"] },
  ],
};
const RULE_ONLY = {
  ...DETAIL, agent_id: "A20002", risk_band: "review", flag: null,
  score: { ...DETAIL.score, anomaly_score: 1.2, flagged: false, flag_source: "Rule", risk_band: "review" },
};
const PAST = {
  decision_id: "RD1", agent_id: "A35485", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
  decision_timestamp: "2026-10-13T15:10:00", status: "confirmed", confirmed_by: "ADM_COMPLIANCE_01",
  notes: "Shares customers with two agents.",
};

function routes(role, extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/agents/A35485": DETAIL,
    "GET /api/agents/A20002": RULE_ONLY,
    "GET /api/review-decisions": { count: 1, decisions: [PAST] },
    ...extra,
  };
}

const panel = () => screen.getByRole("region", { name: "Propose a decision" });

describe("Agent detail", () => {
  it("shows the header, score against the cutoff, the four features and masked identity", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    expect(await screen.findByText("5.564")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agent A35485", level: 1 })).toBeInTheDocument();
    expect(document.title).toBe("Agent A35485 · SalesMesh Fraud Detection");
    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(screen.getByText("Model and rule")).toBeInTheDocument();
    expect(screen.getByText(/At or above the model cutoff of 1\.445/)).toBeInTheDocument();

    const features = screen.getByRole("region", { name: "Features" });
    for (const label of ["Submission frequency", "Time-of-day entropy", "Customer similarity", "Collusion score"]) {
      expect(within(features).getByText(label)).toBeInTheDocument();
    }
    expect(within(features).getByText(/at least one other agent also activated/)).toBeInTheDocument();

    const identity = screen.getByRole("region", { name: "Identity" });
    expect(within(identity).getByText("A. O.")).toBeInTheDocument();
    expect(within(identity).getByText("**********067")).toBeInTheDocument();
    expect(screen.queryByText(/Agnes|Omondi/)).not.toBeInTheDocument();

    expect(within(screen.getByRole("table", { name: "Duplicate activation evidence" })).getByText("CUST16131148")).toBeInTheDocument();
  });

  it("shows the agent's previous decisions as a timeline", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    const history = await screen.findByRole("list", { name: "Decision history" });
    expect(within(history).getByText("Confirmed fraud")).toBeInTheDocument();
    expect(within(history).getByText("Confirmed")).toBeInTheDocument();
    expect(within(history).getByText(/Proposed by ADM_ANALYST_01/)).toBeInTheDocument();
    expect(within(history).getByText("Confirmed by ADM_COMPLIANCE_01")).toBeInTheDocument();
    expect(within(history).getByText("Shares customers with two agents.")).toBeInTheDocument();
  });

  it("validates the outcome and notes before sending anything", async () => {
    const { calls } = mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    await screen.findByRole("region", { name: "Propose a decision" });
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));
    expect(within(panel()).getByText("Choose an outcome.")).toBeInTheDocument();
    expect(within(panel()).getByText("Notes are required.")).toBeInTheDocument();

    await userEvent.click(within(panel()).getByLabelText("Legitimate"));
    await userEvent.type(within(panel()).getByLabelText(/Notes/), "   ");
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));
    expect(within(panel()).getByText("Notes are required.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("counts characters live and refuses more than 1000", async () => {
    const { calls } = mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    await screen.findByRole("region", { name: "Propose a decision" });
    const notes = within(panel()).getByLabelText(/Notes/);
    expect(within(panel()).getByText("0 / 1000")).toBeInTheDocument();
    expect(within(panel()).getByText(/Runs of 7 or more digits/)).toBeInTheDocument();
    await userEvent.type(notes, "Checked");
    expect(within(panel()).getByText("7 / 1000")).toBeInTheDocument();

    await userEvent.clear(notes);
    await userEvent.click(notes);
    await userEvent.paste("a".repeat(1001));
    expect(within(panel()).getByText("1001 / 1000")).toBeInTheDocument();
    await userEvent.click(within(panel()).getByLabelText("Confirmed fraud"));
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));
    expect(within(panel()).getByText("Notes must be at most 1000 characters (now 1001).")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);
  });

  it("proposes a decision with trimmed notes and says it awaits compliance confirmation", async () => {
    let decisions = [PAST];
    const { calls } = mockApi(routes("fraud_analyst", {
      "GET /api/review-decisions": () => ({ count: decisions.length, decisions }),
      "POST /api/review-decisions": (request) => {
        decisions = [{ ...PAST, decision_id: "RD2", status: "pending_confirmation", confirmed_by: null, notes: request.body.notes, decision_outcome: request.body.decision_outcome }, ...decisions];
        return reply(201, { message: "Review decision proposed; awaiting compliance confirmation", decision_id: "RD2", status: "pending_confirmation", notes: request.body.notes });
      },
    }));
    renderApp("/agents/A35485");
    await screen.findByRole("region", { name: "Propose a decision" });
    await userEvent.click(within(panel()).getByLabelText("Confirmed fraud"));
    await userEvent.type(within(panel()).getByLabelText(/Notes/), "  Same customers as A62923.  ");
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));

    const status = await within(panel()).findByRole("status");
    expect(status).toHaveTextContent(PROPOSED_MESSAGE);
    expect(status.textContent).toMatch(/proposed/i);
    expect(status.textContent).toMatch(/waiting for a compliance officer/i);
    expect(status.textContent).not.toMatch(/saved|recorded|is final/i);

    const post = calls.find((c) => c.method === "POST");
    expect(post.body).toEqual({ flag_id: "FL93b6b96d", decision_outcome: "confirmed_fraud", notes: "Same customers as A62923." });
    const history = screen.getByRole("list", { name: "Decision history" });
    expect(await within(history).findByText("Same customers as A62923.")).toBeInTheDocument();
    expect(within(history).getByText("Proposed")).toBeInTheDocument();
    expect(within(history).getByText("Waiting for compliance confirmation")).toBeInTheDocument();
  });

  it("shows the server's message when a proposal is refused", async () => {
    mockApi(routes("fraud_analyst", { "POST /api/review-decisions": reply(400, { error: "notes must not be empty" }) }));
    renderApp("/agents/A35485");
    await screen.findByRole("region", { name: "Propose a decision" });
    await userEvent.click(within(panel()).getByLabelText("Legitimate"));
    await userEvent.type(within(panel()).getByLabelText(/Notes/), "ok");
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));
    expect(await within(panel()).findByRole("alert")).toHaveTextContent("notes must not be empty");
  });

  it("shows rule-only evidence read-only and explains why it cannot be reviewed", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A20002");
    expect(await screen.findByText(/Only the duplicate rule flagged this agent/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Propose a decision" })).not.toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Duplicate activation evidence" })).toBeInTheDocument();
    expect(screen.getByText("Rule only")).toBeInTheDocument();
  });

  it("sends a compliance officer to the confirm queue instead of showing the form", async () => {
    mockApi(routes("compliance_officer"));
    renderApp("/agents/A35485");
    expect(await screen.findByRole("link", { name: "Open the confirm queue" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Propose a decision" })).not.toBeInTheDocument();
  });

  it("sends an admin to the access denied page", async () => {
    mockApi(routes("admin"));
    renderApp("/agents/A35485");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });

  it("shows an error state for an unknown agent", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/agents/NOPE": reply(404, { error: "Agent not found" }) }));
    renderApp("/agents/NOPE");
    expect(await screen.findByText("Agent not found")).toBeInTheDocument();
  });
});
