import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { currentLocation, mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const entry = (i, extra = {}) => ({
  log_id: `AL${i}`, timestamp: `2026-10-13T15:${String(i % 60).padStart(2, "0")}:00`, actor: "ADM_ANALYST_01",
  admin_id: "ADM_ANALYST_01", actor_type: "user", category: "review", action: "propose_decision",
  target_agent_id: "A35485", request_ip: "127.0.*.*",
  details: { decision_id: `RD${i}`, flag_id: "FL1", decision_outcome: "confirmed_fraud", notes: "Called **********067." },
  ...extra,
});

const ENTRIES = [
  entry(1),
  entry(2, {
    actor: "anonymous", category: "authorization", action: "access_denied", target_agent_id: null,
    details: { route: "/api/audit-log", method: "GET", role: null, status: 401, reason: "Authentication required", password_hash: "should-never-show", session_token: "nope" },
  }),
];

function routes(role = "admin", handler) {
  return {
    ...sessionRoutes(role),
    "GET /api/audit-log": handler || ((req) => {
      const params = new URL(req.url, "http://x").searchParams;
      return { total: ENTRIES.length, count: ENTRIES.length, offset: Number(params.get("offset")), limit: Number(params.get("limit")), filters: {}, entries: ENTRIES };
    }),
  };
}

const table = () => screen.findByRole("table", { name: "Audit events" });
const auditCalls = (calls) => calls.filter((c) => c.path === "/api/audit-log").map((c) => new URL(c.url, "http://x").searchParams);

describe("Audit log", () => {
  it("lists events with actor, category, action, plain agent id and result", async () => {
    mockApi(routes());
    renderApp("/audit-log");
    const t = await table();
    expect(within(t).getByText("Decision proposed")).toBeInTheDocument();
    expect(within(t).getByText("Access denied")).toBeInTheDocument();
    expect(within(t).getByText("Refused")).toBeInTheDocument();
    expect(within(t).getByText("A35485")).toBeInTheDocument();
    expect(within(t).queryByRole("link")).not.toBeInTheDocument();
    expect(document.title).toBe("Audit log · SalesMesh Fraud Detection");
  });

  it("sends filters and paging to the server and keeps them in the URL", async () => {
    const { calls } = mockApi(routes());
    renderApp("/audit-log?category=review&page=1&size=10");
    await table();
    let params = auditCalls(calls).at(-1);
    expect(Object.fromEntries(params)).toEqual({ category: "review", limit: "10", offset: "10" });

    await userEvent.type(screen.getByRole("textbox", { name: "Actor" }), "ADM_ADMIN_01");
    expect(currentLocation()).toBe("/audit-log?category=review&page=1&size=10");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(currentLocation()).toBe("/audit-log?category=review&size=10&actor=ADM_ADMIN_01");
    await waitFor(() => expect(Object.fromEntries(auditCalls(calls).at(-1))).toEqual({ category: "review", actor: "ADM_ADMIN_01", limit: "10", offset: "0" }));

    // Dates are typed as day/month/year and sent in the API format.
    await userEvent.type(screen.getByLabelText("From date"), "01/10/2026");
    await userEvent.type(screen.getByLabelText("To date"), "13/10/2026");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => {
      params = auditCalls(calls).at(-1);
      expect(params.get("date_from")).toBe("2026-10-01");
      expect(params.get("date_to")).toBe("2026-10-13");
    });

    await userEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(currentLocation()).toBe("/audit-log?size=10");
  });

  it("shows an inline error for an invalid date or a From date after the To date, and applies nothing", async () => {
    const { calls } = mockApi(routes());
    renderApp("/audit-log");
    await table();
    const before = auditCalls(calls).length;
    await userEvent.type(screen.getByLabelText("From date"), "2026-10-01");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(screen.getByText("Enter a real date as dd/mm/yyyy.")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("From date"));
    await userEvent.type(screen.getByLabelText("From date"), "14/10/2026");
    await userEvent.type(screen.getByLabelText("To date"), "13/10/2026");
    await userEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    expect(screen.getByText("The To date must be on or after the From date.")).toBeInTheDocument();
    expect(auditCalls(calls)).toHaveLength(before);
    expect(currentLocation()).toBe("/audit-log");
  });

  it("shows dates from the address as day/month/year", async () => {
    mockApi(routes());
    renderApp("/audit-log?date_from=2026-10-01");
    await table();
    expect(screen.getByLabelText("From date")).toHaveValue("01/10/2026");
  });

  it("uses the new subtitle and accepts a username as the actor", async () => {
    mockApi(routes());
    renderApp("/audit-log");
    await table();
    expect(screen.getByText("A permanent record of who did what, and when. Entries cannot be changed or deleted.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Actor" })).toHaveAttribute("placeholder", "Username or account ID");
  });

  it.each([
    ["", true], ["review", true], ["ai_decision", true], ["authentication", false], ["report", false], ["admin", false],
  ])("shows the Agent column for category '%s': %s", async (category, shown) => {
    mockApi(routes());
    renderApp(`/audit-log${category ? `?category=${category}` : ""}`);
    const t = await table();
    const headers = within(t).getAllByRole("columnheader").map((c) => c.textContent);
    expect(headers.includes("Agent")).toBe(shown);
  });

  it("leaves the Agent field out of the drawer for a sign-in entry", async () => {
    mockApi(routes("admin", () => ({ total: 1, count: 1, entries: [entry(1, { category: "authentication", action: "login", target_agent_id: null, details: { role: "admin" } })] })));
    renderApp("/audit-log");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: /^Details of/ }));
    const drawer = await screen.findByRole("dialog");
    expect(within(drawer).queryByText("Agent")).not.toBeInTheDocument();
    expect(within(drawer).getByText("Administrator")).toBeInTheDocument();
    expect(within(drawer).getByText("Person")).toBeInTheDocument();
  });

  it("pages on the server", async () => {
    const { calls } = mockApi(routes("admin", (req) => {
      const offset = Number(new URL(req.url, "http://x").searchParams.get("offset"));
      return { total: 30, count: offset === 0 ? 25 : 5, offset, limit: 25, entries: Array.from({ length: offset === 0 ? 25 : 5 }, (_, i) => entry(offset + i + 1)) };
    }));
    renderApp("/audit-log");
    await table();
    expect(screen.getByText("1–25 of 30")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Go to next page" }));
    expect(await screen.findByText("26–30 of 30")).toBeInTheDocument();
    expect(auditCalls(calls).at(-1).get("offset")).toBe("25");
    expect(currentLocation()).toBe("/audit-log?page=1");
  });

  it("opens the full event in a drawer that hides secrets, traps focus, closes with Esc and returns focus", async () => {
    mockApi(routes());
    renderApp("/audit-log");
    const t = await table();
    const trigger = within(t).getAllByRole("button", { name: /^Details of Access denied/ })[0];
    await userEvent.click(trigger);

    const drawer = await screen.findByRole("dialog", { name: "Access denied" });
    expect(within(drawer).getByText("Authentication required")).toBeInTheDocument();
    expect(within(drawer).getByText("/api/audit-log")).toBeInTheDocument();
    expect(within(drawer).getByText("127.0.*.*")).toBeInTheDocument();
    expect(drawer.textContent).not.toMatch(/should-never-show|password_hash|session_token|nope/);

    for (let i = 0; i < 4; i += 1) {
      await userEvent.tab();
      expect(drawer.contains(document.activeElement)).toBe(true);
    }

    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });

  it("opens the drawer from a row click and returns focus to the row", async () => {
    mockApi(routes());
    renderApp("/audit-log");
    const t = await table();
    const row = within(t).getByText("Decision proposed").closest("tr");
    await userEvent.click(row);
    const drawer = await screen.findByRole("dialog", { name: "Decision proposed" });
    expect(within(drawer).getByText("Called **********067.")).toBeInTheDocument();
    await userEvent.click(within(drawer).getByRole("button", { name: "Close details" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(row).toHaveFocus();
  });

  it("shows empty and error states", async () => {
    mockApi(routes("admin", () => ({ total: 0, count: 0, offset: 0, limit: 25, entries: [] })));
    const { unmount } = renderApp("/audit-log");
    expect(await screen.findByText("No audit events yet.")).toBeInTheDocument();
    unmount();

    mockApi(routes("admin", () => reply(400, { error: "category must be one of [...]" })));
    renderApp("/audit-log?category=bad");
    expect(await screen.findByText("category must be one of [...]")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it.each(["fraud_analyst", "compliance_officer"])("sends a %s to the access denied page", async (role) => {
    mockApi(routes(role));
    renderApp("/audit-log");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });
});
