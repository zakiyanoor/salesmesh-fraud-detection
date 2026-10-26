import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ACCOUNTS, currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";
import { HEADLINE, SECURITY_POINTS, SUBLINE } from "./landingContent";

async function open(width = 1280) {
  window.innerWidth = width;
  const api = mockApi(sessionRoutes(null));
  renderApp("/");
  await screen.findByRole("heading", { level: 1, name: HEADLINE });
  return api;
}

describe("Landing page", () => {
  it("has the headline, one line under it and a Sign in button", async () => {
    await open();
    await waitFor(() => expect(document.title).toBe("SalesMesh Fraud Detection"));
    expect(HEADLINE).toBe("Fraud detection for sales agent networks.");
    expect(screen.getByText(SUBLINE)).toBeInTheDocument();
    expect(SUBLINE).toBe("Every flag is reviewed by two people, and every decision is recorded.");
    const main = screen.getByRole("main");
    expect(within(main).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  });

  it("has SalesMesh on the left of the header and Sign in, then the theme menu, on the right", async () => {
    await open();
    const header = screen.getByRole("banner");
    expect(within(header).getByText("SalesMesh")).toBeInTheDocument();
    const controls = [...header.querySelectorAll("a, button")].map((el) => el.textContent || el.getAttribute("aria-label"));
    expect(controls[0]).toBe("Sign in");
    expect(controls[1]).toMatch(/^Theme: /);
    await userEvent.tab();
    expect(within(header).getByRole("link", { name: "Sign in" })).toHaveFocus();
  });

  it("names the four security points in one plain row, each in at most 8 words", async () => {
    await open();
    const row = screen.getByRole("region", { name: "Security design" });
    const items = within(row).getAllByRole("listitem").map((li) => li.textContent);
    expect(items).toEqual(SECURITY_POINTS);
    expect(items).toEqual(["Role based access", "Two person review of every decision", "An append only audit log", "Secure sessions"]);
    for (const item of items) expect(item.split(" ").length).toBeLessThanOrEqual(8);
    expect(row.textContent).not.toMatch(/mask/i);
  });

  it("has a footer with the name and a Sign in link, and nothing else", async () => {
    await open();
    const footer = screen.getByRole("contentinfo");
    expect(footer.textContent).toBe("SalesMesh Fraud DetectionSign in");
    expect(within(footer).getAllByRole("link")).toHaveLength(1);
    expect(within(footer).getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/sign-in");
  });

  it("no longer has the diagram, the signals, the sequence, the role table or the footer columns", async () => {
    await open();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(document.querySelector("dl, ol")).toBeNull();
    for (const gone of [/How a flag is made/, /What it looks at/, /From flag to decision/, /Who can do what/, /ICS Project/]) {
      expect(document.body.textContent).not.toMatch(gone);
    }
    expect(screen.getAllByRole("heading")).toHaveLength(2);
  });

  it("reserves the globe's space at once, then shows the globe as decoration only", async () => {
    await open();
    expect(screen.getByTestId("globe-space")).toBeInTheDocument();
    const globe = await screen.findByTestId("kenya-globe");
    expect(globe).toHaveAttribute("aria-hidden", "true");
    // jsdom has no WebGL, so the still drawing stands in for the globe.
    expect(within(globe).getByTestId("globe-fallback")).toBeInTheDocument();
  });

  it("follows the copy rules", async () => {
    await open();
    const text = document.body.textContent;
    const banned = [/synthetic/i, /%/, /percent/i, /probab/i, /accura/i, /real[ -]time/i, /\blive\b/i, /updated/i,
      /demo/i, /password/i, /analyst_01|admin_01/, /—/, / · /, /→|->/, /©/, /@/];
    for (const pattern of banned) expect(text).not.toMatch(pattern);
  });

  it("makes no request of its own", async () => {
    const { calls } = await open();
    await screen.findByTestId("kenya-globe");
    expect(calls.map((c) => c.path)).toEqual(["/api/me"]);
  });

  it("switches to the dark scheme from its own theme menu", async () => {
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
