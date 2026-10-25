import { describe, expect, it } from "vitest";
import { AUDIT_ACTIONS, auditResult } from "./audit";

describe("audit labels (issue #28)", () => {
  it("names every review action, including older confirmations", () => {
    for (const action of ["propose_decision", "withdraw_decision", "agree_decision", "overrule_decision", "correct_decision", "review_refused", "confirm_decision", "customer_viewed"]) {
      expect(AUDIT_ACTIONS[action]).toBeTruthy();
    }
    expect(AUDIT_ACTIONS.confirm_decision).toBe("Decision confirmed (agreed)");
  });

  it("shows a refused review action as refused", () => {
    expect(auditResult({ action: "review_refused" })).toBe("refused");
    expect(auditResult({ action: "overrule_decision" })).toBe("ok");
  });
});
