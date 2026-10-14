import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockApi, renderApp, reply, sessionRoutes } from "../test/server";

function file(body, filename, type) {
  return () => new Response(body, { status: 200, headers: { "Content-Type": type, "Content-Disposition": `attachment; filename="${filename}"` } });
}

let saved;
beforeEach(() => {
  saved = [];
  // jsdom has no object URLs; these stand in and are removed after each test.
  URL.createObjectURL = vi.fn(() => "blob:report");
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function click() {
    saved.push({ href: this.getAttribute("href"), download: this.download });
  });
});

afterEach(() => {
  delete URL.createObjectURL;
  delete URL.revokeObjectURL;
});

const card = (name) => screen.findByRole("region", { name });

describe("Reports", () => {
  it("offers each report the backend has, in its own format", async () => {
    mockApi(sessionRoutes("admin"));
    renderApp("/reports");
    expect(within(await card("Flagged agents")).getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
    expect(within(await card("Audit log")).getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
    expect(within(await card("Detection summary")).getByRole("button", { name: "Download PDF" })).toBeInTheDocument();
    expect(document.title).toBe("Reports · SalesMesh Fraud Detection");
  });

  it("downloads with credentials and saves under the file name from the response header", async () => {
    const { calls } = mockApi({
      ...sessionRoutes("admin"),
      "GET /api/reports/detection-summary.pdf": file("%PDF-1.4", "detection-summary_2026-10-13.pdf", "application/pdf"),
    });
    renderApp("/reports");
    const pdf = await card("Detection summary");
    await userEvent.click(within(pdf).getByRole("button", { name: "Download PDF" }));
    expect(await within(pdf).findByText("Downloaded detection-summary_2026-10-13.pdf")).toBeInTheDocument();
    expect(saved).toEqual([{ href: "blob:report", download: "detection-summary_2026-10-13.pdf" }]);
    const call = calls.find((c) => c.path === "/api/reports/detection-summary.pdf");
    expect(call.init.credentials).toBe("include");
    await waitFor(() => expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:report"));
  });

  it("shows a loading state while the file is prepared", async () => {
    let finish;
    mockApi({
      ...sessionRoutes("admin"),
      "GET /api/reports/flagged-agents.csv": () => new Promise((resolve) => { finish = resolve; }),
    });
    renderApp("/reports");
    const csv = await card("Flagged agents");
    await userEvent.click(within(csv).getByRole("button", { name: "Download CSV" }));
    const busy = within(csv).getByRole("button", { name: "Preparing…" });
    expect(busy).toBeDisabled();
    finish(file("agent_id\n", "flagged-agents_2026-10-13.csv", "text/csv")());
    expect(await within(csv).findByText("Downloaded flagged-agents_2026-10-13.csv")).toBeInTheDocument();
    expect(within(csv).getByRole("button", { name: "Download CSV" })).toBeEnabled();
  });

  it("explains a failed download and saves nothing", async () => {
    mockApi({ ...sessionRoutes("admin"), "GET /api/reports/flagged-agents.csv": reply(404, { error: "No successful detection run yet" }) });
    renderApp("/reports");
    const csv = await card("Flagged agents");
    await userEvent.click(within(csv).getByRole("button", { name: "Download CSV" }));
    expect(await within(csv).findByRole("alert")).toHaveTextContent("Download failed: No successful detection run yet");
    expect(saved).toEqual([]);
  });

  it("sends the audit report filters", async () => {
    const { calls } = mockApi({
      ...sessionRoutes("admin"),
      "GET /api/reports/audit-log.csv": file("timestamp\n", "audit-log_2026-10-13.csv", "text/csv"),
    });
    renderApp("/reports");
    const audit = await card("Audit log");
    await userEvent.click(within(audit).getByRole("combobox", { name: "Category" }));
    await userEvent.click(screen.getByRole("option", { name: "Review" }));
    await userEvent.type(within(audit).getByLabelText("From"), "2026-10-01");
    await userEvent.click(within(audit).getByRole("button", { name: "Download CSV" }));
    await within(audit).findByText("Downloaded audit-log_2026-10-13.csv");
    const url = calls.find((c) => c.path === "/api/reports/audit-log.csv").url;
    expect(url).toBe("/api/reports/audit-log.csv?category=review&date_from=2026-10-01");
  });

  it.each(["fraud_analyst", "compliance_officer"])("sends a %s to the access denied page", async (role) => {
    mockApi(sessionRoutes(role));
    renderApp("/reports");
    expect(await screen.findByRole("heading", { name: "Access denied", level: 1 })).toBeInTheDocument();
  });
});
