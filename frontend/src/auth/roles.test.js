import { describe, expect, it } from "vitest";
import { canAccess, menuFor } from "./roles";

const labels = (role) => menuFor(role).map((page) => page.label);

describe("menus per role", () => {
  it("fraud analyst", () => {
    expect(labels("fraud_analyst")).toEqual([
      "Overview", "Flagged agents", "All agents", "Threat intelligence", "Analytics", "Review history",
      "How the model works",
    ]);
  });

  it("compliance officer gets the analyst menu plus Confirm queue", () => {
    expect(labels("compliance_officer")).toEqual([
      "Overview", "Flagged agents", "All agents", "Threat intelligence", "Analytics", "Review history",
      "Confirm queue", "How the model works",
    ]);
  });

  it("admin", () => {
    expect(labels("admin")).toEqual([
      "Overview", "Threat intelligence", "Analytics", "Audit log", "Reports", "Accounts", "How the model works",
    ]);
  });

  it("an unknown role gets nothing", () => {
    expect(labels("administrator")).toEqual([]);
    expect(labels(undefined)).toEqual([]);
  });
});

describe("route access", () => {
  it.each([
    ["fraud_analyst", "flagged", true],
    ["fraud_analyst", "agentDetail", true],
    ["fraud_analyst", "confirm", false],
    ["fraud_analyst", "audit", false],
    ["fraud_analyst", "accounts", false],
    ["compliance_officer", "confirm", true],
    ["compliance_officer", "audit", false],
    ["compliance_officer", "reports", false],
    ["admin", "flagged", false],
    ["admin", "howItWorks", true],
    ["fraud_analyst", "howItWorks", true],
    ["compliance_officer", "howItWorks", true],
    ["admin", "agentDetail", false],
    ["admin", "history", false],
    ["admin", "reports", true],
    ["admin", "accounts", true],
    ["admin", "unknown-page", false],
  ])("%s on %s: %s", (role, key, allowed) => {
    expect(canAccess(role, key)).toBe(allowed);
  });
});
