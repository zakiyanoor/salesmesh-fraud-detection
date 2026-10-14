import { describe, expect, it, vi } from "vitest";
import { ApiError, api, setUnauthorizedHandler } from "./api";
import { mockApi, reply } from "./test/server";

describe("request helper", () => {
  it("calls the default base /api with the session cookie", async () => {
    const { calls } = mockApi({ "GET /api/all-agents": { count: 0, agents: [] } });
    await expect(api.getAllAgents()).resolves.toEqual({ count: 0, agents: [] });
    expect(calls[0].url).toBe("/api/all-agents");
    expect(calls[0].init.credentials).toBe("include");
  });

  it("throws an ApiError with the status and the server's message", async () => {
    mockApi({ "GET /api/agents/NOPE": reply(404, { error: "Agent not found" }) });
    const error = await api.getAgentDetail("NOPE").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 404, message: "Agent not found" });
  });

  it("uses a readable message when the server sends none, and status 0 when it is unreachable", async () => {
    mockApi({ "GET /api/analytics": reply(500, {}), "GET /api/all-agents": new TypeError("Failed to fetch") });
    await expect(api.getAnalytics()).rejects.toMatchObject({ status: 500, message: "The server had a problem. Try again." });
    await expect(api.getAllAgents()).rejects.toMatchObject({ status: 0 });
  });

  it("calls the unauthorized handler on a 401 only", async () => {
    const handler = vi.fn();
    const unregister = setUnauthorizedHandler(handler);
    mockApi({
      "GET /api/analytics": reply(401, { error: "Account is deactivated" }),
      "GET /api/all-agents": reply(403, { error: "Forbidden" }),
    });
    await expect(api.getAnalytics()).rejects.toMatchObject({ status: 401 });
    await expect(api.getAllAgents()).rejects.toMatchObject({ status: 403 });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0][0]).toMatchObject({ status: 401, message: "Account is deactivated" });
    unregister();
  });

  it("does not treat a 401 from login, logout or /me as a session that ended", async () => {
    const handler = vi.fn();
    const unregister = setUnauthorizedHandler(handler);
    mockApi({
      "POST /api/login": reply(401, { error: "Invalid username or password" }),
      "GET /api/me": reply(401, { error: "Authentication required" }),
      "POST /api/logout": reply(401, {}),
    });
    await expect(api.login("x", "y")).rejects.toMatchObject({ status: 401 });
    await expect(api.me()).rejects.toMatchObject({ status: 401 });
    await expect(api.logout()).rejects.toMatchObject({ status: 401 });
    expect(handler).not.toHaveBeenCalled();
    unregister();
  });

  it("sends notes with a proposed decision and builds query strings", async () => {
    const { calls } = mockApi({ "POST /api/review-decisions": reply(201, {}), "GET /api/audit-log": { entries: [] } });
    await api.proposeDecision({ flagId: "FL1", decisionOutcome: "legitimate", notes: "Checked." });
    expect(calls[0].body).toEqual({ flag_id: "FL1", decision_outcome: "legitimate", notes: "Checked." });
    await api.getAuditLog({ category: "review", actor: "", limit: 50 });
    expect(calls[1].url).toBe("/api/audit-log?category=review&limit=50");
  });
});
