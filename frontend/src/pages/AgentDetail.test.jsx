import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";
import { PROPOSED_MESSAGE, WITHDRAWN_MESSAGE } from "../review";

const DETAIL = {
  agent_id: "A35485", region: "Elgeyo-Marakwet", account_status: "active", risk_band: "high",
  registration_timestamp: "2026-06-11T20:56:24",
  identity: { full_name: "Agnes Omondi", phone_number: "**********067", national_id_number: "*****291" },
  features: { submission_frequency: 21, time_of_day_dist: 0.788, customer_similarity: 0.103, collusion_score: 0.464 },
  flag: { flag_id: "FL93b6b96d", flag_status: "flagged", model_version: "lof_v3_4f", suspicion_score: 5.564 },
  score: {
    anomaly_score: 5.563827, score_percentile: 98.9, threshold: 1.444799, flagged: true, rule_flagged: true, duplicate_pairs: 19,
    flag_source: "Both", risk_band: "high", reasons: "46% of customers also used by other agents vs typical 0%",
  },
  duplicate_evidence: [
    { customer_id: "CUST16131148", customer_ref: "c_3f9a1b2c4d5e6f708192a3b4", client_id: "CL09", other_agent_id: "A62923", reason: "shared customer", record_ids: ["R1", "R2"] },
  ],
  review: {
    reviewable: true, reason: null, flag_id: "FL93b6b96d", flag_source: "Both", open_decision_id: null,
    open_proposed_by: null, open_is_mine: false, final_decision_id: null, effective_outcome: null,
  },
};
// As the API returns them: every agent has a flag row (status "clear" when the model did not flag it).
const RULE_ONLY = {
  ...DETAIL, agent_id: "A20002", risk_band: "review",
  flag: { flag_id: "FL20002", flag_status: "clear", model_version: "lof_v3_4f", suspicion_score: 1.2 },
  score: { ...DETAIL.score, anomaly_score: 1.2, flagged: false, flag_source: "Rule", risk_band: "review" },
  review: { ...DETAIL.review, flag_id: "FL20002", flag_source: "Rule" },
};
const NOT_FLAGGED = {
  ...DETAIL, agent_id: "A10053", risk_band: "low", duplicate_evidence: [],
  flag: { flag_id: "FL10053", flag_status: "clear", model_version: "lof_v3_4f", suspicion_score: 1.08 },
  score: { ...DETAIL.score, anomaly_score: 1.077, flagged: false, rule_flagged: false, duplicate_pairs: 0, flag_source: "None", risk_band: "low" },
  review: { ...DETAIL.review, reviewable: false, reason: "This agent is not flagged in the latest detection run", flag_id: "FL10053", flag_source: "None" },
};
const CUSTOMER = {
  customer: { customer_ref: "c_3f9a1b2c4d5e6f708192a3b4", customer_id: "CUST16131148" },
  run_id: "RUN1", agent_count: 2, client_count: 2, client_ids: ["CL04", "CL09"],
  first_seen: "2026-08-03T10:12:00", last_seen: "2026-08-27T16:40:00",
  agents: [
    { agent_id: "A35485", flag_source: "Both", risk_band: "high", activations: 2, client_ids: ["CL09"], first_seen: "2026-08-03T10:12:00", last_seen: "2026-08-27T16:40:00" },
    { agent_id: "A62923", flag_source: "Rule", risk_band: "review", activations: 1, client_ids: ["CL04"], first_seen: "2026-08-10T09:00:00", last_seen: "2026-08-10T09:00:00" },
  ],
  activations_total: 3, activations_limit: 200,
  activations: [
    { timestamp: "2026-08-27T16:40:00", agent_id: "A35485", client_id: "CL09", status: "completed" },
    { timestamp: "2026-08-10T09:00:00", agent_id: "A62923", client_id: "CL04", status: "failed" },
    { timestamp: "2026-08-03T10:12:00", agent_id: "A35485", client_id: "CL09", status: "completed" },
  ],
};
const ACTIVITY = {
  agent_id: "A35485", run_id: "RUN1", first_day: "2026-08-01", last_day: "2026-08-03",
  days: [
    { date: "2026-08-01", activations: 5, completed: 4, duplicate_evidence: true },
    { date: "2026-08-02", activations: 0, completed: 0, duplicate_evidence: false },
    { date: "2026-08-03", activations: 2, completed: 2, duplicate_evidence: false },
  ],
  hours: Array.from({ length: 24 }, (_, hour) => ({ hour, activations: hour === 9 ? 4 : hour === 14 ? 3 : 0 })),
  totals: { activations: 7, completed: 6 }, note: "Days and hours are as recorded in the data.",
};
const CUSTOMER_ROUTE = "GET /api/customers/c_3f9a1b2c4d5e6f708192a3b4";
const withReview = (review) => ({ ...DETAIL, review: { ...DETAIL.review, reviewable: false, ...review } });
const MY_OPEN = withReview({ reason: "This flag already has an open proposal", open_decision_id: "RD2", open_proposed_by: "ADM_ANALYST_01", open_is_mine: true });
const FINAL = withReview({ reason: "This flag already has a final decision", final_decision_id: "RD1", effective_outcome: "confirmed_fraud" });
const PAST = {
  decision_id: "RD1", agent_id: "A35485", reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud",
  decision_timestamp: "2026-10-13T15:10:00", status: "agreed", closed_by: "ADM_COMPLIANCE_01",
  closed_at: "2026-10-13T16:00:00", final_outcome: "confirmed_fraud", effective_outcome: "confirmed_fraud", corrections: [],
  notes: "Shares customers with two agents.",
};

function routes(role, extra = {}) {
  return {
    ...sessionRoutes(role),
    "GET /api/agents/A35485": DETAIL,
    "GET /api/agents/A35485/activity": ACTIVITY,
    "GET /api/agents/A20002": RULE_ONLY,
    "GET /api/agents/A10053": NOT_FLAGGED,
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
    expect(screen.getByText(
      "Higher than 98.9% of agents scored in the latest run. This is a rank, not a probability.",
    )).toBeInTheDocument();

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
    expect(within(history).getByText("Agreed")).toBeInTheDocument();
    expect(within(history).getByText(/Proposed by ADM_ANALYST_01/)).toBeInTheDocument();
    expect(within(history).getByText(/Agreed by ADM_COMPLIANCE_01/)).toBeInTheDocument();
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
    let detail = DETAIL;
    let decisions = [PAST];
    const { calls } = mockApi(routes("fraud_analyst", {
      "GET /api/agents/A35485": () => detail,
      "GET /api/review-decisions": () => ({ count: decisions.length, decisions }),
      "POST /api/review-decisions": (request) => {
        decisions = [{ ...PAST, decision_id: "RD2", status: "pending_confirmation", confirmed_by: null, notes: request.body.notes, decision_outcome: request.body.decision_outcome }, ...decisions];
        detail = MY_OPEN;
        return reply(201, { message: "Review decision proposed; awaiting compliance confirmation", decision_id: "RD2", status: "pending_confirmation", notes: request.body.notes });
      },
    }));
    renderApp("/agents/A35485");
    await screen.findByRole("region", { name: "Propose a decision" });
    expect(within(panel()).getByText("Flagged by: Model and rule in the latest detection run.")).toBeInTheDocument();
    await userEvent.click(within(panel()).getByLabelText("Confirmed fraud"));
    await userEvent.type(within(panel()).getByLabelText(/Notes/), "  Same customers as A62923.  ");
    await userEvent.click(within(panel()).getByRole("button", { name: "Propose decision" }));

    const status = await screen.findByRole("status");
    expect(status).toHaveTextContent(PROPOSED_MESSAGE);
    expect(status.textContent).toMatch(/proposed/i);
    expect(status.textContent).toMatch(/waiting for a compliance officer/i);
    expect(status.textContent).not.toMatch(/saved|recorded|is final/i);

    const post = calls.find((c) => c.method === "POST");
    expect(post.body).toEqual({ flag_id: "FL93b6b96d", decision_outcome: "confirmed_fraud", notes: "Same customers as A62923." });
    expect(await screen.findByRole("button", { name: "Withdraw proposal" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Propose a decision" })).not.toBeInTheDocument();
    const history = screen.getByRole("list", { name: "Decision history" });
    expect(await within(history).findByText("Same customers as A62923.")).toBeInTheDocument();
    expect(within(history).getByText("Proposed")).toBeInTheDocument();
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

  it("lets an analyst propose on an agent only the duplicate rule flagged", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A20002");
    const form = await screen.findByRole("region", { name: "Propose a decision" });
    expect(within(form).getByText("Flagged by: Rule only in the latest detection run.")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Duplicate activation evidence" })).toBeInTheDocument();
    expect(screen.getByText("Rule only")).toBeInTheDocument();
  });

  it("explains that an agent nobody flagged has nothing to review", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A10053");
    expect(await screen.findByText("This agent is not flagged in the latest detection run")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Propose a decision" })).not.toBeInTheDocument();
  });

  it("withdraws the analyst's own open proposal with a required note", async () => {
    let detail = MY_OPEN;
    const { calls } = mockApi(routes("fraud_analyst", {
      "GET /api/agents/A35485": () => detail,
      "POST /api/review-decisions/RD2/withdraw": () => { detail = DETAIL; return { status: "withdrawn" }; },
    }));
    renderApp("/agents/A35485");
    expect(await screen.findByText(/Your proposal is waiting for a compliance officer/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Withdraw proposal" }));
    const dialog = screen.getByRole("dialog", { name: "Withdraw this proposal?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Withdraw proposal" }));
    expect(within(dialog).getByText("Notes are required.")).toBeInTheDocument();
    expect(calls.some((c) => c.method === "POST")).toBe(false);

    await userEvent.type(within(dialog).getByLabelText(/Note/), " Proposed on the wrong agent. ");
    await userEvent.click(within(dialog).getByRole("button", { name: "Withdraw proposal" }));
    expect(await screen.findByRole("status")).toHaveTextContent(WITHDRAWN_MESSAGE);
    expect(calls.find((c) => c.method === "POST").body).toEqual({ notes: "Proposed on the wrong agent." });
    expect(await screen.findByRole("region", { name: "Propose a decision" })).toBeInTheDocument();
  });

  it("shows another analyst's open proposal without a withdraw button", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/agents/A35485": { ...MY_OPEN, review: { ...MY_OPEN.review, open_proposed_by: "ADM_ANALYST_02", open_is_mine: false } } }));
    renderApp("/agents/A35485");
    expect(await screen.findByText("A proposal by ADM_ANALYST_02 is waiting for a compliance officer.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Withdraw proposal" })).not.toBeInTheDocument();
  });

  it("tells an analyst that only a compliance officer can change a final decision", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/agents/A35485": FINAL }));
    renderApp("/agents/A35485");
    expect(await screen.findByText("Final outcome: Confirmed fraud. Only a compliance officer can correct it.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /correction/i })).not.toBeInTheDocument();
  });

  it("lets a compliance officer record a correction with the other outcome preset and a required note", async () => {
    let detail = FINAL;
    const { calls } = mockApi(routes("compliance_officer", {
      "GET /api/agents/A35485": () => detail,
      "POST /api/review-decisions/RD1/corrections": () => {
        detail = withReview({ final_decision_id: "RD1", effective_outcome: "legitimate" });
        return reply(201, { effective_outcome: "legitimate" });
      },
    }));
    renderApp("/agents/A35485");
    await userEvent.click(await screen.findByRole("button", { name: "Record a correction" }));
    const dialog = screen.getByRole("dialog", { name: "Record a correction" });
    expect(within(dialog).getByLabelText("Legitimate")).toBeChecked();
    await userEvent.click(within(dialog).getByRole("button", { name: "Record correction" }));
    expect(within(dialog).getByText("Notes are required.")).toBeInTheDocument();

    await userEvent.type(within(dialog).getByLabelText(/Note/), "The customer list was from the wrong month.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Record correction" }));
    expect(await screen.findByRole("status")).toHaveTextContent("The outcome in force is now Legitimate");
    expect(calls.find((c) => c.method === "POST").body).toEqual({
      new_outcome: "legitimate", expected_current_outcome: "confirmed_fraud", notes: "The customer list was from the wrong month.",
    });
    expect(await screen.findByText(/Final outcome: Legitimate/)).toBeInTheDocument();
  });

  it("keeps the correction dialog open with the server's message when it is refused", async () => {
    mockApi(routes("compliance_officer", {
      "GET /api/agents/A35485": FINAL,
      "POST /api/review-decisions/RD1/corrections": reply(409, { error: "The decision's outcome is now legitimate, not confirmed_fraud; reload and try again" }),
    }));
    renderApp("/agents/A35485");
    await userEvent.click(await screen.findByRole("button", { name: "Record a correction" }));
    const dialog = screen.getByRole("dialog", { name: "Record a correction" });
    await userEvent.type(within(dialog).getByLabelText(/Note/), "Wrong month.");
    await userEvent.click(within(dialog).getByRole("button", { name: "Record correction" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("reload and try again");
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

  it("opens a customer from the evidence by its reference and shows agents, clients and dates", async () => {
    const { calls } = mockApi(routes("fraud_analyst", { [CUSTOMER_ROUTE]: CUSTOMER }));
    renderApp("/agents/A35485");
    await userEvent.click(await screen.findByRole("button", { name: "Open customer CUST16131148" }));
    const dialog = await screen.findByRole("dialog", { name: "Customer CUST16131148" });
    expect(await within(dialog).findByText(/Used by 2 agents across 2 clients/)).toBeInTheDocument();
    expect(within(dialog).getByText(/CL04, CL09/)).toBeInTheDocument();
    expect(within(dialog).getByText(/First seen .* Last seen/)).toBeInTheDocument();
    const agents = within(dialog).getByRole("table", { name: "Agents who used this customer" });
    expect(within(agents).getByRole("link", { name: "A62923" })).toHaveAttribute("href", "/agents/A62923");
    expect(within(agents).getByText("Rule only")).toBeInTheDocument();
    const activations = within(dialog).getByRole("table", { name: "Activations" });
    expect(within(activations).getAllByRole("row")).toHaveLength(4);
    expect(within(dialog).queryByText(/Showing the latest/)).not.toBeInTheDocument();
    expect(within(dialog).getByText("Opening this view is recorded in the audit log.")).toBeInTheDocument();

    const request = calls.find((c) => c.path.startsWith("/api/customers/"));
    expect(request.url).toBe("/api/customers/c_3f9a1b2c4d5e6f708192a3b4?from_agent=A35485");
    expect(calls.some((c) => c.url.includes("CUST16131148"))).toBe(false);
  });

  it("says when the activations list is capped", async () => {
    mockApi(routes("compliance_officer", { [CUSTOMER_ROUTE]: { ...CUSTOMER, activations_total: 350, activations_limit: 200 } }));
    renderApp("/agents/A35485");
    await userEvent.click(await screen.findByRole("button", { name: "Open customer CUST16131148" }));
    expect(await screen.findByText("Showing the latest 3 of 350 activations.")).toBeInTheDocument();
  });

  it("fetches the customer again on every open, so every open is audited", async () => {
    const { calls } = mockApi(routes("fraud_analyst", { [CUSTOMER_ROUTE]: CUSTOMER }));
    renderApp("/agents/A35485");
    const open = await screen.findByRole("button", { name: "Open customer CUST16131148" });
    await userEvent.click(open);
    const dialog = await screen.findByRole("dialog", { name: "Customer CUST16131148" });
    await within(dialog).findByText(/Used by 2 agents/);
    await userEvent.click(within(dialog).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await userEvent.click(open);
    await within(await screen.findByRole("dialog")).findByText(/Used by 2 agents/);
    expect(calls.filter((c) => c.path.startsWith("/api/customers/"))).toHaveLength(2);
  });

  it("shows the server's message when the customer cannot be shown", async () => {
    mockApi(routes("fraud_analyst", {
      [CUSTOMER_ROUTE]: reply(500, { error: "This access could not be recorded in the audit log, so the customer is not shown" }),
    }));
    renderApp("/agents/A35485");
    await userEvent.click(await screen.findByRole("button", { name: "Open customer CUST16131148" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/could not be recorded in the audit log/)).toBeInTheDocument();
    expect(within(dialog).queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows one row per day with completed counts and marks only days with duplicate evidence", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    const card = await screen.findByRole("region", { name: "Daily activity" });
    const table = await within(card).findByRole("table", { name: "Activations per day" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual([
      "2026-08-0154Duplicate evidence on this day", "2026-08-0200", "2026-08-0322",
    ]);
    expect(within(card).getByText(/Days and hours are as recorded in the data\./)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/flagged on this day/i);
  });

  it("shows activations by hour of day as a chart with a table view", async () => {
    mockApi(routes("fraud_analyst"));
    renderApp("/agents/A35485");
    const card = await screen.findByRole("region", { name: "Activations by hour of day" });
    expect(await within(card).findByRole("img", { name: /Activations by hour of day chart/ })).toBeInTheDocument();
    expect(within(card).getByText("7 activations, 6 completed.")).toBeInTheDocument();
    await userEvent.click(within(card).getByRole("button", { name: "Show as table" }));
    const table = within(card).getByRole("table", { name: "Activations by hour of day data" });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(25);
    expect(rows[10].textContent).toBe("94");
  });

  it("keeps the rest of the page when the activity cannot be loaded", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/agents/A35485/activity": reply(500, { error: "Activity unavailable" }) }));
    renderApp("/agents/A35485");
    const card = await screen.findByRole("region", { name: "Daily activity" });
    expect(await within(card).findByText("Activity unavailable")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Evidence" })).toBeInTheDocument();
  });

  it("shows an error state for an unknown agent", async () => {
    mockApi(routes("fraud_analyst", { "GET /api/agents/NOPE": reply(404, { error: "Agent not found" }) }));
    renderApp("/agents/NOPE");
    expect(await screen.findByText("Agent not found")).toBeInTheDocument();
  });
});
