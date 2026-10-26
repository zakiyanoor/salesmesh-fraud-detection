import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ACCOUNTS, currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";
import { DUPLICATE_RULE, PERMISSIONS, ROLES, SECURITY, SIGNALS, STEPS } from "./landingContent";
import { FLAG_STEPS, STEPS as FLOW_STEPS } from "../components/flowDiagramContent";

const HEADLINE = "Fraud detection for sales agent networks, with every decision reviewed by two people and recorded.";

async function open(width = 1280) {
  window.innerWidth = width;
  const api = mockApi(sessionRoutes(null));
  renderApp("/");
  await screen.findByRole("heading", { level: 1, name: HEADLINE });
  return api;
}

const region = (name) => screen.getByRole("region", { name });

describe("Landing page", () => {
  it("has the headline, the paragraph and Sign in as the first tab stop", async () => {
    await open();
    await waitFor(() => expect(document.title).toBe("SalesMesh Fraud Detection"));
    expect(screen.getByText(/^SalesMesh compares each agent's activations with typical agent behaviour and applies a duplicate activation rule\. Flagged agents are passed to a fraud analyst with the supporting evidence, and a compliance officer agrees or overrules the proposed outcome\.$/)).toBeInTheDocument();
    const header = screen.getByRole("banner");
    expect(within(header).getByText("SalesMesh")).toBeInTheDocument();
    expect(within(header).getByRole("button", { name: /^Theme: / })).toBeInTheDocument();
    await userEvent.tab();
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveFocus();
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  });

  it("draws how a flag is made with a title, a description, the three flag sources and a text list", async () => {
    await open();
    const diagram = screen.getByRole("img", { name: /How a flag is made/ });
    for (const f of FLAG_STEPS) expect(within(diagram).getAllByText(f.label).length).toBeGreaterThan(0);
    expect(within(diagram).getByText("Fraud analyst")).toBeInTheDocument();
    expect(within(diagram).getByText("Compliance officer")).toBeInTheDocument();
    const list = within(region("How a flag is made")).getByRole("list");
    expect(within(list).getAllByRole("listitem").map((li) => li.textContent)).toEqual(FLOW_STEPS);
  });

  it("stacks the diagram on narrow screens", async () => {
    await open(360);
    const diagram = screen.getByRole("img", { name: /How a flag is made/ });
    expect(diagram.getAttribute("viewBox")).toBe("0 0 340 732");
    expect(within(diagram).getByText("Four signals")).toBeInTheDocument();
  });

  it("explains the four signals and the rule as definition lists", async () => {
    await open();
    const section = region("What it looks at");
    for (const [term, meaning] of [...SIGNALS, DUPLICATE_RULE]) {
      expect(within(section).getByText(term).tagName).toBe("DT");
      expect(within(section).getByText(meaning).tagName).toBe("DD");
    }
  });

  it("lists the real sequence from flag to decision", async () => {
    await open();
    const section = region("From flag to decision");
    expect(within(section).getByText("A flag prompts a review. It is not a finding.")).toBeInTheDocument();
    const steps = within(section).getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(steps).toEqual(STEPS.map(([title]) => title));
    expect(within(section).getByText(/Detection runs on a schedule, not live\./)).toBeInTheDocument();
  });

  it("shows who can do what as a table, and as a list on a phone", async () => {
    await open();
    const table = within(region("Who can do what")).getByRole("table");
    expect(within(table).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Action", ...ROLES]);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows.map((r) => r.textContent)).toEqual(PERMISSIONS.map(([action, allowed]) => action + allowed.map((y) => (y ? "Yes" : "No")).join("")));
  });

  it("gives the phone the same permissions as a list", async () => {
    await open(360);
    const section = region("Who can do what");
    expect(within(section).queryByRole("table")).not.toBeInTheDocument();
    expect(within(section).getByText("Propose an outcome for a flagged agent").nextSibling).toHaveTextContent("Fraud analyst only.");
    expect(within(section).getByText("Read the audit log").nextSibling).toHaveTextContent("Compliance officer and administrator only.");
    expect(within(section).getByText("Open the threat intelligence views").nextSibling).toHaveTextContent("All three roles.");
  });

  it("names exactly the four security points that are true in the code", async () => {
    await open();
    const section = region("Security design");
    const terms = [...section.querySelectorAll("dt")].map((dt) => dt.textContent);
    expect(terms).toEqual(SECURITY.map(([, term]) => term));
    expect(section.textContent).not.toMatch(/mask/i);
  });

  it("has a footer whose links all land on sections of the page", async () => {
    await open();
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("Fraud detection for sales agent networks in Kenya.")).toBeInTheDocument();
    expect(within(footer).getByText("SalesMesh Fraud Detection. ICS Project II, 2026.")).toBeInTheDocument();
    expect(within(footer).getByText("Accounts are managed by an administrator.")).toBeInTheDocument();
    const nav = within(footer).getByRole("navigation", { name: "Page sections" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      "The four signals", "The duplicate activation rule", "How a flag is made",
      "From flag to decision", "Who can do what", "Corrections and the audit trail",
      "Role based access", "Two person review", "Append only audit log", "Secure sessions", "Sign in",
    ]);
    for (const link of links.slice(0, -1)) {
      const target = link.getAttribute("href");
      expect(target.startsWith("#")).toBe(true);
      expect(document.getElementById(target.slice(1))).not.toBeNull();
    }
    expect(links.at(-1)).toHaveAttribute("href", "/sign-in");
    expect(document.querySelectorAll("a[href^='http'], a[href^='mailto']")).toHaveLength(0);
  });

  it("follows the copy rules", async () => {
    await open();
    const text = document.body.textContent;
    const banned = [/synthetic/i, /%/, /percent/i, /probab/i, /accura/i, /real[ -]time/i, /demo/i, /password/i,
      /analyst_01|admin_01/, /—/, / · /, /→|->/, /©/, /@/];
    for (const pattern of banned) expect(text).not.toMatch(pattern);
    expect(text).toMatch(/schedule/);
  });

  it("makes no request of its own", async () => {
    const { calls } = await open();
    expect(calls.map((c) => c.path)).toEqual(["/api/me"]);
  });

  it("switches to the dark scheme from its own toggle", async () => {
    await open();
    await userEvent.click(within(screen.getByRole("banner")).getByRole("button", { name: /^Theme: / }));
    await userEvent.click(screen.getByRole("menuitemradio", { name: "Dark" }));
    expect(document.documentElement.getAttribute("data-color-scheme")).toBe("dark");
    expect(window.localStorage.getItem("salesmesh.colorMode")).toBe("dark");
  });

  it("leads to the existing sign-in form, and signing in opens the usual home page", async () => {
    mockApi({ ...sessionRoutes(null), "POST /api/login": { message: "Login successful", ...ACCOUNTS.fraud_analyst } });
    renderApp("/");
    await userEvent.click(within(await screen.findByRole("banner")).getByRole("link", { name: "Sign in" }));
    expect(currentLocation()).toBe("/sign-in");
    await userEvent.type(await screen.findByLabelText("Username"), "analyst_01");
    await userEvent.type(screen.getByLabelText("Password"), "test-only-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(currentLocation()).toBe("/");
  });

  it("sends a signed-in user at the root to the usual home page", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: HEADLINE })).not.toBeInTheDocument();
  });

  it("shows the sign-in form with its message at the root when there is one", async () => {
    mockApi({ "GET /api/me": { status: 401, body: { error: "Account is deactivated" } } });
    renderApp("/");
    expect(await screen.findByText("Account is deactivated")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});
