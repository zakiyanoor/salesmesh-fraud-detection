import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ACCOUNTS, mockApi, renderApp, reply, sessionRoutes } from "./server";

const menu = () => screen.getByRole("navigation", { name: "Main menu" });
const menuLabels = () => within(menu()).getAllByRole("link").map((link) => link.textContent);

describe("session restore", () => {
  it("restores a signed-in session from /api/me on load", async () => {
    const { calls } = mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(within(menu()).getByText("Signed in as analyst_01")).toBeInTheDocument();
    expect(within(menu()).getByText("Fraud analyst")).toBeInTheDocument();
    expect(calls[0].path).toBe("/api/me");
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("shows the sign-in page without a message when there is no session", async () => {
    mockApi(sessionRoutes(null));
    renderApp("/");
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(document.title).toBe("Sign in · SalesMesh Fraud Detection");
  });

  it("says when the restored account is deactivated", async () => {
    mockApi({ "GET /api/me": reply(401, { error: "Account is deactivated" }) });
    renderApp("/");
    expect(await screen.findByText("Account is deactivated")).toBeInTheDocument();
  });

  it("signs in with the role from the login response and opens the requested page", async () => {
    mockApi({ ...sessionRoutes(null), "POST /api/login": { message: "Login successful", ...ACCOUNTS.admin } });
    renderApp("/accounts");
    await userEvent.type(await screen.findByLabelText("Username"), "admin_01");
    await userEvent.type(screen.getByLabelText("Password"), "LanternHarbour58");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Accounts" })).toBeInTheDocument();
    expect(screen.getByText("Coming in the next step")).toBeInTheDocument();
  });

  it("shows a wrong password on the form", async () => {
    mockApi({ ...sessionRoutes(null), "POST /api/login": reply(401, { error: "Invalid username or password" }) });
    renderApp("/");
    await userEvent.type(await screen.findByLabelText("Username"), "analyst_01");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Invalid username or password")).toBeInTheDocument();
  });
});

describe("role-based menus and guards", () => {
  it.each([
    ["fraud_analyst", ["Overview", "Flagged agents", "All agents", "Threat intelligence", "Analytics", "Review history"]],
    ["compliance_officer", ["Overview", "Flagged agents", "All agents", "Threat intelligence", "Analytics", "Review history", "Confirm queue", "Audit log"]],
    ["admin", ["Overview", "Threat intelligence", "Analytics", "Audit log", "Reports", "Accounts"]],
  ])("%s sees only its menu", async (role, expected) => {
    mockApi(sessionRoutes(role));
    renderApp("/");
    await screen.findByRole("heading", { name: "Overview" });
    expect(menuLabels()).toEqual(expected);
  });

  it.each([
    ["fraud_analyst", "/accounts"],
    ["fraud_analyst", "/confirm-queue"],
    ["fraud_analyst", "/audit-log"],
    ["compliance_officer", "/reports"],
    ["admin", "/flagged"],
    ["admin", "/agents/A10001"],
    ["admin", "/history"],
  ])("%s opening %s gets Access denied", async (role, path) => {
    mockApi(sessionRoutes(role));
    renderApp(path);
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });

  it.each([
    ["compliance_officer", "/confirm-queue", "Confirm queue"],
    ["compliance_officer", "/audit-log", "Audit log"],
    ["fraud_analyst", "/flagged", "Flagged agents"],
    ["admin", "/reports", "Reports"],
  ])("%s may open %s", async (role, path, title) => {
    mockApi(sessionRoutes(role));
    renderApp(path);
    expect(await screen.findByRole("heading", { name: title, level: 1 })).toBeInTheDocument();
  });

  it("an unknown address shows the not found page", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/no-such-page");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("the review form is only for fraud analysts", async () => {
    mockApi(sessionRoutes("compliance_officer"));
    renderApp("/agents/A10001");
    await screen.findByRole("heading", { name: "A10001" });
    expect(screen.queryByRole("button", { name: "Submit decision" })).not.toBeInTheDocument();
  });
});

describe("error handling", () => {
  it("a 401 from any request signs out and shows why", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/flagged-agents": reply(401, { error: "Account is deactivated" }) });
    renderApp("/flagged");
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
    expect(screen.getByText("Account is deactivated")).toBeInTheDocument();
  });

  it("an expired session asks to sign in again", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/analytics": reply(401, { error: "Authentication required" }) });
    renderApp("/analytics");
    expect(await screen.findByText("Your session has ended. Please sign in again.")).toBeInTheDocument();
  });

  it("a 403 shows Access denied and keeps the user signed in", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/analytics": reply(403, { error: "Forbidden" }) });
    renderApp("/analytics");
    expect(await screen.findByRole("heading", { name: "Access denied" })).toBeInTheDocument();
    expect(within(menu()).getByText("Signed in as analyst_01")).toBeInTheDocument();
  });

  it("a 404 shows an error state and keeps the user signed in", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/agents/NOPE": reply(404, { error: "Agent not found" }) });
    renderApp("/agents/NOPE");
    expect(await screen.findByText("Agent not found")).toBeInTheDocument();
    expect(within(menu()).getByText("Signed in as analyst_01")).toBeInTheDocument();
  });

  it("a 500 shows an error with retry, and retry loads the page", async () => {
    let attempts = 0;
    mockApi({
      ...sessionRoutes("fraud_analyst"),
      "GET /api/review-decisions": () => (++attempts === 1 ? reply(500, { error: "Database unavailable" }) : { count: 0, decisions: [] }),
    });
    renderApp("/history");
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("No decisions recorded yet.")).toBeInTheDocument();
    expect(attempts).toBe(2);
  });

  it.each([
    ["the server fails", reply(500, {})],
    ["the network is down", new TypeError("Failed to fetch")],
  ])("logout clears the session even when %s", async (_, outcome) => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "POST /api/logout": outcome });
    renderApp("/");
    await screen.findByRole("heading", { name: "Overview" });
    await userEvent.click(within(menu()).getByRole("button", { name: "Sign out" }));
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeInTheDocument();
  });
});

describe("storage", () => {
  it("keeps no token or password in localStorage or sessionStorage", async () => {
    const written = [];
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function setItem(key, value) {
      written.push([key, value]);
      return original.call(this, key, value);
    };
    try {
      mockApi({ ...sessionRoutes(null), "POST /api/login": { message: "Login successful", ...ACCOUNTS.fraud_analyst } });
      renderApp("/");
      await userEvent.type(await screen.findByLabelText("Username"), "analyst_01");
      await userEvent.type(screen.getByLabelText("Password"), "RiverbankTrader42");
      await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
      await screen.findByRole("heading", { name: "Overview" });
      await userEvent.click(within(menu()).getByRole("button", { name: "Switch to dark mode" }));

      const stored = [...written];
      for (const storage of [window.localStorage, window.sessionStorage]) {
        for (let i = 0; i < storage.length; i += 1) stored.push([storage.key(i), storage.getItem(storage.key(i))]);
      }
      const text = JSON.stringify(stored).toLowerCase();
      expect(text).not.toContain("riverbanktrader42");
      expect(text).not.toMatch(/token|password|session|cookie/);
      expect(new Set(stored.map(([key]) => key))).toEqual(new Set(["salesmesh.colorMode"]));
      expect(window.sessionStorage.length).toBe(0);
    } finally {
      Storage.prototype.setItem = original;
    }
  });
});

describe("responsive layout", () => {
  it("below md the menu is a drawer behind a menu button", async () => {
    window.innerWidth = 360;
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/");
    await screen.findByRole("heading", { name: "Overview" });
    expect(screen.queryByRole("navigation", { name: "Main menu" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Open menu" }));
    await userEvent.click(within(menu()).getByRole("link", { name: "Analytics" }));
    expect(await screen.findByRole("heading", { name: "Analytics" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("navigation", { name: "Main menu" })).not.toBeInTheDocument());
  });

  it("each page sets its document title", async () => {
    mockApi(sessionRoutes("fraud_analyst"));
    renderApp("/all-agents");
    await screen.findByRole("heading", { name: "All agents" });
    expect(document.title).toBe("All agents · SalesMesh Fraud Detection");
  });
});
