// Landing page copy (issue #28), kept apart from the component so tests can check it.

export { SIGN_IN_PATH } from "../auth/redirect";

export const HEADLINE = "Fraud detection for sales agent networks.";
export const SUBLINE = "Every flag is reviewed by two people, and every decision is recorded.";
export const TAGLINE = "Fraud detection for sales agent networks.";

// What the platform does. Checked against the product: an analyst proposes and a compliance officer
// decides; corrections sit beside final decisions; ring graphs are on Threat intelligence; only customer
// views (not every view) are audited.
// The platform cards: heading, paragraph, label chip and one link. Every link is to a page all three roles may
// open (auth/redirect.js SHARED_PAGES; a test checks it): the confirm queue and the audit log are not, so Review
// links to Analytics (it holds Review outcomes) and Accountability to Overview.
export const CARDS = [
  {
    title: "Detection", chip: "Scoring", link: "Read the detection guide", path: "/detection-guide",
    text: "A frozen statistical model and a duplicate activation rule score every sales agent on a schedule and rank agents for review.",
  },
  {
    title: "Review", chip: "Decisions", link: "Open analytics", path: "/analytics",
    text: "An analyst proposes an outcome for each flag and a compliance officer agrees or overrules it. Decisions are never overwritten; a correction is recorded beside the original.",
  },
  {
    title: "Investigation", chip: "Analysis", link: "Open threat intelligence", path: "/threat-intelligence",
    text: "Open an agent to see why it was flagged, its daily activity and the customers behind the evidence, and follow linked agent rings by county.",
  },
  {
    title: "Accountability", chip: "Records", link: "Open the overview", path: "/",
    text: "Sign-ins, refused requests, customer views and every review decision are written to an append only audit log, and access is limited by role.",
  },
];

// Plain lines in the footer; docs/FRONTEND.md names the file that proves each.
// Masked identifiers are not listed: that change is not in main.
export const SECURITY_POINTS = ["Role based access", "Two person review", "Append only audit log", "Secure sessions"];

export const LOCATION = "Nairobi, Kenya";
export const COPYRIGHT = "2026 SalesMesh";
