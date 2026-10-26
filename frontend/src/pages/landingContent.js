// Landing page copy (issue #28), kept apart from the component so tests can check it.

export const SIGN_IN_PATH = "/sign-in";

export const HEADLINE = "Fraud detection for sales agent networks.";
export const SUBLINE = "Every flag is reviewed by two people, and every decision is recorded.";

// Names only, each true in the code today; docs/FRONTEND.md names the file that proves each.
// Masked identifiers are not listed: that change is not in main.
export const SECURITY_POINTS = [
  "Role based access",
  "Two person review of every decision",
  "An append only audit log",
  "Secure sessions",
];
