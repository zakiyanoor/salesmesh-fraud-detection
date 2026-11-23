// Signed-out navigation (issue #28): links from the landing page go to sign in, and every sign in opens the home page.
import { ADMIN, COMPLIANCE_OFFICER, FRAUD_ANALYST, PAGES } from "./roles";

export const SIGN_IN_PATH = "/sign-in";
export const DEFAULT_PATH = "/";
const ALL_ROLES = [FRAUD_ANALYST, COMPLIANCE_OFFICER, ADMIN];

/** Menu pages that every role may open, in menu order: the landing page's navigation. */
export const SHARED_PAGES = PAGES.filter((page) => page.menu && ALL_ROLES.every((role) => page.roles.includes(role)));
