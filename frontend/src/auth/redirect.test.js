import { describe, expect, it } from "vitest";
import { ADMIN, COMPLIANCE_OFFICER, FRAUD_ANALYST, menuFor } from "./roles";
import { DEFAULT_PATH, SHARED_PAGES, safeTarget, signInHref } from "./redirect";

describe("Signed-out navigation (issue #28)", () => {
  it("lists only the menu pages every role may open", () => {
    expect(SHARED_PAGES.map((page) => page.label)).toEqual(["Overview", "Threat intelligence", "Analytics", "Detection guide"]);
    for (const role of [FRAUD_ANALYST, COMPLIANCE_OFFICER, ADMIN]) {
      const menu = menuFor(role).map((page) => page.key);
      for (const page of SHARED_PAGES) expect(menu, role).toContain(page.key);
    }
    // The agent lists are for reviewers only, so they are not shared.
    expect(SHARED_PAGES.map((page) => page.key)).not.toContain("flagged");
    expect(SHARED_PAGES.map((page) => page.key)).not.toContain("allAgents");
  });

  it("remembers the target in the sign-in address", () => {
    expect(signInHref("/threat-intelligence")).toBe("/sign-in?next=%2Fthreat-intelligence");
  });

  it("accepts a known relative route", () => {
    expect(safeTarget("/analytics")).toBe("/analytics");
    expect(safeTarget("/detection-guide", ADMIN)).toBe("/detection-guide");
    expect(safeTarget("/agents/A10001", FRAUD_ANALYST)).toBe("/agents/A10001");
  });

  it("ignores external, protocol-relative, unknown and malformed targets", () => {
    for (const next of [null, undefined, "", "analytics", "//evil.example", "https://evil.example", "/\\evil.example",
      "/unknown", "/analytics/extra", "/ analytics", "javascript:alert(1)", "/x://y"]) {
      expect(safeTarget(next), String(next)).toBe(DEFAULT_PATH);
    }
  });

  it("ignores a page the role may not open", () => {
    expect(safeTarget("/audit-log", FRAUD_ANALYST)).toBe(DEFAULT_PATH);
    expect(safeTarget("/flagged", ADMIN)).toBe(DEFAULT_PATH);
    expect(safeTarget("/audit-log", ADMIN)).toBe("/audit-log");
  });
});
