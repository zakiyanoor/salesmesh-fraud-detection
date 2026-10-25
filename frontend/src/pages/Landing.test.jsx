import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ACCOUNTS, currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";

describe("Landing page", () => {
  it("is the first page at the root before sign in, with Sign in at the top", async () => {
    mockApi(sessionRoutes(null));
    renderApp("/");
    expect(await screen.findByRole("heading", { level: 1, name: "SalesMesh Fraud Detection" })).toBeInTheDocument();
    expect(document.title).toBe("SalesMesh Fraud Detection");
    const header = screen.getByRole("banner");
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
    await userEvent.tab();
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveFocus();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("says in plain words what the system does, that people decide and that detection runs on a schedule", async () => {
    mockApi(sessionRoutes(null));
    renderApp("/");
    expect(await screen.findByText("Highlights unusual activity by sales agents so that people can review it.")).toBeInTheDocument();
    const how = screen.getByRole("region", { name: "How it works" });
    expect(within(how).getByText(/A model looks for unusual activity, and a duplicate activation rule/)).toBeInTheDocument();
    expect(within(how).getByRole("heading", { name: "People decide" })).toBeInTheDocument();
    expect(within(how).getByRole("heading", { name: "Detection runs on a schedule" })).toBeInTheDocument();
  });

  it("lists exactly the four security points", async () => {
    mockApi(sessionRoutes(null));
    renderApp("/");
    const security = await screen.findByRole("region", { name: "Security design" });
    expect(within(security).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Role based access", "Two person review of every decision", "An append only audit log", "Secure sessions",
    ]);
  });

  it("makes no claims, names no accounts and calls no API of its own", async () => {
    const { calls } = mockApi(sessionRoutes(null));
    renderApp("/");
    await screen.findByRole("heading", { level: 1, name: "SalesMesh Fraud Detection" });
    const text = document.body.textContent;
    for (const banned of [/synthetic/i, /%/, /percent/i, /probab/i, /accura/i, /mask/i, /password/i, /demo/i, /analyst_01|admin_01/]) {
      expect(text).not.toMatch(banned);
    }
    // Only the session check that runs before any page; the landing page itself requests nothing.
    expect(calls.map((c) => c.path)).toEqual(["/api/me"]);
    expect(document.querySelectorAll("script[src], link[rel=stylesheet][href^=http]")).toHaveLength(0);
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
    expect(screen.queryByRole("heading", { name: "SalesMesh Fraud Detection" })).not.toBeInTheDocument();
  });

  it("shows the sign-in form with its message at the root when there is one", async () => {
    mockApi({ "GET /api/me": { status: 401, body: { error: "Account is deactivated" } } });
    renderApp("/");
    expect(await screen.findByText("Account is deactivated")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });
});
