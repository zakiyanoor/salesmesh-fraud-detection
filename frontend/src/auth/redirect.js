// Signed-out navigation (issue #28): links from the landing page go to sign in and remember where to go next.
import { matchPath } from "react-router-dom";
import { ADMIN, COMPLIANCE_OFFICER, FRAUD_ANALYST, PAGES } from "./roles";

export const SIGN_IN_PATH = "/sign-in";
export const DEFAULT_PATH = "/";
const ALL_ROLES = [FRAUD_ANALYST, COMPLIANCE_OFFICER, ADMIN];

/** Menu pages that every role may open, in menu order: the landing page's navigation. */
export const SHARED_PAGES = PAGES.filter((page) => page.menu && ALL_ROLES.every((role) => page.roles.includes(role)));

/** The sign-in address that remembers a target page. */
export function signInHref(path) {
  return `${SIGN_IN_PATH}?next=${encodeURIComponent(path)}`;
}

/**
 * The page to open after signing in. Only a relative path with a single leading slash that matches a known
 * route the role may open is accepted; anything else (an external address, "//host", an unknown page) falls
 * back to DEFAULT_PATH, so the parameter cannot redirect anywhere else.
 */
export function safeTarget(next, role) {
  if (typeof next !== "string" || !next.startsWith("/") || next.startsWith("//") || /[\\\s]|:\/\//.test(next)) {
    return DEFAULT_PATH;
  }
  const page = PAGES.find((p) => matchPath({ path: p.path, end: true }, next));
  return page && (!role || page.roles.includes(role)) ? next : DEFAULT_PATH;
}
