import { describe, expect, it } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ACCOUNTS, currentLocation, mockApi, renderApp, sessionRoutes } from "../test/server";
import { SHARED_PAGES, signInHref } from "../auth/redirect";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { cwd } from "node:process";
import { AUDIT_ACTIONS } from "../audit";
import { AUDIT_ROWS, FLAGGED_TITLE, RANKED_AGENTS } from "./platformExcerpts";
import { CARDS, COPYRIGHT, HEADLINE, SECURITY_POINTS, SUBLINE, TAGLINE } from "./landingContent";

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

  it("has SalesMesh, the shared pages, then Sign in and the theme menu in the header", async () => {
    await open();
    const header = screen.getByRole("banner");
    expect(within(header).getByText("SalesMesh")).toBeInTheDocument();
    const controls = [...header.querySelectorAll("a, button")].map((el) => el.textContent || el.getAttribute("aria-label"));
    expect(controls).toEqual(["Overview", "Threat intelligence", "Analytics", "How the model works", "Open navigation", "Sign in", expect.stringMatching(/^Theme: /)]);
    await userEvent.tab();
    expect(within(header).getByRole("link", { name: "Overview" })).toHaveFocus();
  });

  it("links every shared page to sign in, remembering the page, while signed out", async () => {
    await open();
    const nav = screen.getByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((a) => a.textContent)).toEqual(SHARED_PAGES.map((page) => page.label));
    expect(links.map((a) => a.getAttribute("href"))).toEqual(SHARED_PAGES.map((page) => signInHref(page.path)));
    expect(within(nav).getByRole("link", { name: "Analytics" })).toHaveAttribute("href", "/sign-in?next=%2Fanalytics");
  });

  it("collapses the pages into a menu button with an accessible list", async () => {
    await open(360);
    const button = within(screen.getByRole("banner")).getByRole("button", { name: "Open navigation" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    const list = screen.getByRole("menu", { name: "Main" });
    expect(document.getElementById(button.getAttribute("aria-controls"))).toContainElement(list);
    const items = within(list).getAllByRole("menuitem");
    expect(items.map((item) => item.textContent)).toEqual(SHARED_PAGES.map((page) => page.label));
    expect(items[1]).toHaveAttribute("href", "/sign-in?next=%2Fthreat-intelligence");
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(button).toHaveAttribute("aria-expanded", "false"));
  });

  it("explains the platform in four flat cards, each with a short excerpt of the real interface", async () => {
    await open();
    const section = screen.getByRole("region", { name: "What the platform does" });
    const cards = within(section).getAllByRole("listitem");
    expect(cards).toHaveLength(4);
    expect(within(section).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Detection", "Review", "Investigation", "Accountability"]);
    for (const [i, [title, text]] of CARDS.entries()) {
      expect(within(cards[i]).getByRole("heading", { name: title })).toBeInTheDocument();
      expect(within(cards[i]).getByText(text)).toBeInTheDocument();
      // One illustration per card, described in one sentence, so no fake table reaches a screen reader.
      const excerpt = within(cards[i]).getByRole("img");
      expect(excerpt.getAttribute("aria-label")).toMatch(/^Example of /);
    }
    expect(within(section).queryByRole("table")).not.toBeInTheDocument();
    expect(within(section).queryByRole("article")).not.toBeInTheDocument();
    // Not interactive, so no tab stops, and no drawings: the only SVGs are the app's own chip icons.
    expect(section.querySelectorAll("[tabindex]")).toHaveLength(0);
    expect(section.querySelector("[data-testid^=drawing-]")).toBeNull();
    for (const svg of section.querySelectorAll("svg")) expect(svg.closest(".MuiChip-root")).not.toBeNull();
    // The app's own vocabulary.
    expect(within(cards[0]).getByText("Model and rule")).toBeInTheDocument();
    expect(within(cards[0]).getAllByText("Rule only").length).toBeGreaterThan(0);
    expect(within(cards[0]).getByText(FLAGGED_TITLE)).toBeInTheDocument();
    expect(within(cards[0]).getAllByText("Not reviewed").length).toBeGreaterThan(0);
    expect(within(cards[1]).getByText("Proposed by fraud analyst")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Agreed by compliance officer")).toBeInTheDocument();
    expect(within(cards[1]).getByText("Confirmed fraud")).toBeInTheDocument();
    for (const { action } of AUDIT_ROWS) expect(within(cards[3]).getByText(action)).toBeInTheDocument();
    expect(section.textContent).not.toMatch(/%|accura|precision|recall/i);
  });

  it("uses only audit actions that the server records and the audit log page knows", () => {
    const backend = readdirSync(resolve(cwd(), "..", "backend", "src")).filter((name) => name.endsWith(".py"))
      .map((name) => readFileSync(resolve(cwd(), "..", "backend", "src", name), "utf-8")).join("\n");
    for (const { action } of AUDIT_ROWS) {
      expect(backend, action).toMatch(new RegExp(`["']${action}["']`));
      expect(Object.keys(AUDIT_ACTIONS), action).toContain(action);
    }
    expect(RANKED_AGENTS.every((a) => /^A\d{5}$/.test(a.agent_id))).toBe(true);
  });

  it("has a footer with the name, a short line, link groups, the security points and a plain bottom bar", async () => {
    await open();
    const footer = screen.getByRole("contentinfo");
    expect(within(footer).getByText("SalesMesh")).toBeInTheDocument();
    expect(within(footer).getByText(TAGLINE)).toBeInTheDocument();
    const platform = within(footer).getByRole("navigation", { name: "Platform" });
    expect(within(platform).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")]))
      .toEqual(SHARED_PAGES.map((page) => [page.label, signInHref(page.path)]));
    expect(within(footer).queryByRole("navigation", { name: "Access" })).not.toBeInTheDocument();
    expect(within(footer).getAllByRole("heading").map((h) => h.textContent)).toEqual(["Platform", "Security"]);
    // The only links in the footer are the Platform pages: no Sign in link anywhere in it.
    expect(within(footer).getAllByRole("link")).toHaveLength(SHARED_PAGES.length);
    expect(within(footer).queryByRole("link", { name: "Sign in" })).not.toBeInTheDocument();
    const security = within(footer).getByRole("heading", { name: "Security" }).parentElement;
    expect(within(security).getAllByRole("listitem").map((li) => li.textContent)).toEqual(SECURITY_POINTS);
    expect(within(security).queryByRole("link")).not.toBeInTheDocument();
    // The bottom bar: copyright on the left, the city on the right, and no Sign in link.
    const bar = within(footer).getByText(COPYRIGHT).parentElement;
    expect([...bar.children].map((el) => el.textContent)).toEqual(["2026 SalesMesh", "Nairobi, Kenya"]);
    expect(within(bar).queryByRole("link")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Security design" })).not.toBeInTheDocument();
  });

  it("no longer has the diagram, the signals, the sequence, the role table or the footer columns", async () => {
    await open();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(document.querySelector("dl, ol")).toBeNull();
    for (const gone of [/How a flag is made/, /What it looks at/, /From flag to decision/, /Who can do what/, /ICS Project/, /supervis/i, /\bAI\b/, /Claude|Anthropic/]) {
      expect(document.body.textContent).not.toMatch(gone);
    }
    expect(screen.getAllByRole("heading").map((h) => h.textContent)).toEqual([HEADLINE, "What the platform does",
      "Detection", "Review", "Investigation", "Accountability", "Platform", "Security"]);
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

  it("signs in from a page link and lands on that page", async () => {
    mockApi({ ...sessionRoutes(null), "POST /api/login": { message: "Login successful", ...ACCOUNTS.compliance_officer } });
    renderApp("/");
    const nav = await screen.findByRole("navigation", { name: "Main" });
    await userEvent.click(within(nav).getByRole("link", { name: "How the model works" }));
    expect(currentLocation()).toBe("/sign-in?next=%2Fhow-it-works");
    await userEvent.type(await screen.findByLabelText("Username"), "compliance_01");
    await userEvent.type(screen.getByLabelText("Password"), "test-only-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(currentLocation()).toBe("/how-it-works"));
    expect(await screen.findByRole("heading", { name: "How the model works" })).toBeInTheDocument();
  });

  it.each([["an external", "https%3A%2F%2Fevil.example"], ["a protocol-relative", "%2F%2Fevil.example"], ["an unknown", "%2Fnowhere"]])(
    "ignores %s target and opens the usual home page", async (_, next) => {
      mockApi({ ...sessionRoutes(null), "POST /api/login": { message: "Login successful", ...ACCOUNTS.fraud_analyst } });
      renderApp(`/sign-in?next=${next}`);
      await userEvent.type(await screen.findByLabelText("Username"), "analyst_01");
      await userEvent.type(screen.getByLabelText("Password"), "test-only-password");
      await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
      expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
      expect(currentLocation()).toBe("/");
    });

  it("opens the remembered page at once when already signed in", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/sign-in?next=%2Fanalytics");
    await waitFor(() => expect(currentLocation()).toBe("/analytics"));
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
