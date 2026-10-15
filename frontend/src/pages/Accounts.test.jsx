import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const ACCOUNTS = [
  { admin_id: "ADM_ADMIN_01", username: "admin_01", role: "admin", is_active: true },
  { admin_id: "ADM_ANALYST_01", username: "analyst_01", role: "fraud_analyst", is_active: true },
  { admin_id: "ADM_COMPLIANCE_01", username: "compliance_01", role: "compliance_officer", is_active: true },
  { admin_id: "ADM001", username: "admin", role: "administrator", is_active: false, password_hash: "scrypt:32768:8:1$leak$leak" },
];

function routes(role = "admin", extra = {}) {
  return { ...sessionRoutes(role), "GET /api/admin/accounts": { count: ACCOUNTS.length, accounts: ACCOUNTS }, ...extra };
}

const table = () => screen.findByRole("table", { name: "Accounts" });
const row = (t, username) => within(t).getByText(username).closest("tr");

describe("Accounts", () => {
  it("lists accounts with role and status, never a password hash", async () => {
    mockApi(routes());
    renderApp("/accounts");
    const t = await table();
    expect(within(row(t, "analyst_01")).getByText("Fraud analyst")).toBeInTheDocument();
    expect(within(row(t, "compliance_01")).getByText("Compliance officer")).toBeInTheDocument();
    expect(within(row(t, "admin")).getByText("administrator (not a valid role)")).toBeInTheDocument();
    expect(within(row(t, "admin")).getByText("Deactivated")).toBeInTheDocument();
    expect(within(row(t, "analyst_01")).getByText("Active")).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/scrypt|leak|password_hash/);
    expect(screen.getByText(/New accounts and password resets are not available here/)).toBeInTheDocument();
    expect(document.title).toBe("Accounts · SalesMesh Fraud Detection");
  });

  it("does not offer changes to your own account", async () => {
    mockApi(routes());
    renderApp("/accounts");
    const own = row(await table(), "admin_01");
    expect(within(own).getByText("(you)")).toBeInTheDocument();
    expect(within(own).queryByRole("button")).not.toBeInTheDocument();
  });

  it("deactivates after confirming and updates the row", async () => {
    const { calls } = mockApi(routes("admin", {
      "POST /api/admin/accounts/ADM_ANALYST_01/deactivate": { message: "Account updated", changed: true, account: { ...ACCOUNTS[1], is_active: false } },
    }));
    renderApp("/accounts");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Deactivate analyst_01" }));
    const dialog = screen.getByRole("dialog", { name: "Deactivate account" });
    expect(calls.some((c) => c.method === "POST")).toBe(false);
    await userEvent.click(within(dialog).getByRole("button", { name: "Deactivate account" }));
    expect(await screen.findByText("analyst_01 is deactivated.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(within(row(t, "analyst_01")).getByText("Deactivated")).toBeInTheDocument();
    expect(within(t).getByRole("button", { name: "Reactivate analyst_01" })).toBeInTheDocument();
  });

  it("changes a role through the dialog", async () => {
    const { calls } = mockApi(routes("admin", {
      "PATCH /api/admin/accounts/ADM_ANALYST_01/role": (req) => ({ message: "Account updated", changed: true, account: { ...ACCOUNTS[1], role: req.body.role } }),
    }));
    renderApp("/accounts");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Change role of analyst_01" }));
    const dialog = screen.getByRole("dialog", { name: "Change role" });
    await userEvent.click(within(dialog).getByRole("combobox", { name: "Role" }));
    await userEvent.click(screen.getByRole("option", { name: "Compliance officer" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Change role" }));
    expect(await screen.findByText("analyst_01 is now Compliance officer.")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "PATCH").body).toEqual({ role: "compliance_officer" });
    expect(within(row(t, "analyst_01")).getByText("Compliance officer")).toBeInTheDocument();
  });

  it("shows the server's refusal in the dialog and leaves the row unchanged", async () => {
    mockApi(routes("admin", {
      "POST /api/admin/accounts/ADM_COMPLIANCE_01/deactivate": reply(409, { error: "The last active admin cannot be demoted or deactivated" }),
    }));
    renderApp("/accounts");
    const t = await table();
    await userEvent.click(within(t).getByRole("button", { name: "Deactivate compliance_01" }));
    await userEvent.click(screen.getByRole("button", { name: "Deactivate account" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("The last active admin cannot be demoted or deactivated");
    await userEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(within(row(t, "compliance_01")).getByText("Active")).toBeInTheDocument();
  });

  it("shows empty and error states", async () => {
    mockApi(routes("admin", { "GET /api/admin/accounts": { count: 0, accounts: [] } }));
    const { unmount } = renderApp("/accounts");
    expect(await screen.findByText("No accounts exist yet.")).toBeInTheDocument();
    unmount();

    mockApi(routes("admin", { "GET /api/admin/accounts": reply(500, { error: "Database unavailable" }) }));
    renderApp("/accounts");
    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it.each(["fraud_analyst", "compliance_officer"])("sends a %s to the access denied page", async (role) => {
    mockApi(routes(role));
    renderApp("/accounts");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });
});
