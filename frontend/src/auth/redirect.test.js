import { describe, expect, it } from "vitest";
import { ADMIN, COMPLIANCE_OFFICER, FRAUD_ANALYST, menuFor } from "./roles";
import { SHARED_PAGES } from "./redirect";

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
});
