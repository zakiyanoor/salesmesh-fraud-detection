import { describe, expect, it } from "vitest";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

const footer = () => screen.findByRole("contentinfo");

describe("footer", () => {
  it.each([
    ["fraud_analyst", "/history"],
    ["compliance_officer", "/analytics"],
    ["admin", "/"],
  ])("shows the model version and the last run time to a %s on %s", async (role, path) => {
    mockApi(sessionRoutes(role));
    renderApp(path);
    const f = await footer();
    expect(await within(f).findByText(/^Model lof_v3_4f · Last detection run /)).toBeInTheDocument();
    expect(f.textContent).toContain(new Date("2026-10-13T15:07:16").toLocaleString());
  });

  it("names a run that did not succeed", async () => {
    mockApi({
      ...sessionRoutes("fraud_analyst"),
      "GET /api/detection-runs/latest": { run: { model_version: "lof_v3_4f", status: "failed", started_at: "2026-10-13T15:00:00", finished_at: "2026-10-13T15:01:00" } },
    });
    renderApp("/history");
    expect(await within(await footer()).findByText(/\(failed\)$/)).toBeInTheDocument();
  });

  it("handles no run and an unavailable status", async () => {
    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/detection-runs/latest": { run: null } });
    const { unmount } = renderApp("/history");
    expect(await within(await footer()).findByText("No detection run yet")).toBeInTheDocument();
    unmount();

    mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/detection-runs/latest": reply(500, {}) });
    renderApp("/history");
    expect(await within(await footer()).findByText("Detection run status unavailable")).toBeInTheDocument();
  });

  it("refreshes once per page and keeps the previous run on screen meanwhile", async () => {
    const runs = [
      { model_version: "lof_v3_4f", status: "succeeded", started_at: "2026-10-13T15:07:08", finished_at: "2026-10-13T15:07:16" },
      { model_version: "lof_v3_4f", status: "failed", started_at: "2026-10-14T15:00:00", finished_at: "2026-10-14T15:01:00" },
    ];
    let served = 0;
    const { calls } = mockApi({ ...sessionRoutes("fraud_analyst"), "GET /api/detection-runs/latest": () => ({ run: runs[served++] }) });
    renderApp("/history");
    const f = await footer();
    expect(await within(f).findByText(/^Model lof_v3_4f · Last detection run /)).toBeInTheDocument();
    expect(f.textContent).toContain(new Date("2026-10-13T15:07:16").toLocaleString());

    await userEvent.click(within(screen.getByRole("navigation", { name: "Main menu" })).getByRole("link", { name: "Analytics" }));
    expect(f.textContent).not.toContain("Checking");
    expect(await within(f).findByText(/\(failed\)$/)).toBeInTheDocument();
    expect(calls.filter((c) => c.path === "/api/detection-runs/latest")).toHaveLength(2);
  });

  it("is not shown on the sign-in page", async () => {
    mockApi(sessionRoutes(null));
    renderApp("/sign-in");
    await screen.findByRole("button", { name: "Sign in" });
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });
});
