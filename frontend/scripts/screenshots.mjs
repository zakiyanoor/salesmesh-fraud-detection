// Screenshots and responsive checks of every page, for every role, at 360, 768 and 1280 px.
// Uses the installed Chrome through playwright-core (no browser download) and the production build
// served by `vite preview`. Every /api call is answered with fictional data below; no backend is
// needed and no real personal data appears.
//
//   npm run build && npm run screenshots
//   CHROME_PATH=... to point at another Chromium-based browser.

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { spawn } from "node:child_process";
import { chromium } from "playwright-core";

const OUT = join(import.meta.dirname, "..", "..", "docs", "screenshots");
const PORT = 4179;
const BASE = `http://127.0.0.1:${PORT}`;
const CHROME = process.env.CHROME_PATH || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const WIDTHS = [
  { width: 360, height: 780, touch: true },
  { width: 768, height: 1024, touch: true },
  { width: 1280, height: 900, touch: false },
];

// ---- Fictional data (ids, regions and masked numbers are made up) ----
const REGIONS = ["Nairobi", "Kisumu", "Mombasa", "Nakuru", "Eldoret", "Lamu"];
const SOURCES = ["Both", "ML", "Rule", "None"];
const agents = Array.from({ length: 40 }, (_, i) => {
  const source = i < 6 ? SOURCES[i % 3] : i < 9 ? "Rule" : "None";
  const score = source === "None" ? 1 + (i % 7) / 30 : source === "Rule" ? 1.2 + (i % 3) / 20 : 6 - i / 3;
  return {
    agent_id: `A${10001 + i * 137}`, region: REGIONS[i % REGIONS.length], account_status: "active",
    status: ["ML", "Both"].includes(source) ? "flagged" : "clear", flag_source: source,
    risk_band: ["ML", "Both"].includes(source) ? "high" : source === "Rule" || score >= 1.3 ? "review" : "low",
    suspicion_score: Number(score.toFixed(3)), submission_frequency: 12 + (i % 9), time_of_day_dist: 0.7 + (i % 5) / 50,
    customer_similarity: 0.1 + (i % 4) / 100, collusion_score: source === "None" ? 0 : 0.2 + (i % 4) / 10,
  };
});
const decisions = [
  { decision_id: "RD1", agent_id: agents[0].agent_id, reviewer_id: "ADM_ANALYST_01", decision_outcome: "confirmed_fraud", decision_timestamp: "2026-10-13T15:10:00", status: "pending_confirmation", confirmed_by: null, notes: "Shares 14 customers with two other agents in the same week." },
  { decision_id: "RD2", agent_id: agents[1].agent_id, reviewer_id: "ADM_ANALYST_01", decision_outcome: "legitimate", decision_timestamp: "2026-10-12T09:30:00", status: "confirmed", confirmed_by: "ADM_COMPLIANCE_01", notes: "Burst explained by a sales event; customers checked." },
  { decision_id: "RD3", agent_id: agents[2].agent_id, reviewer_id: "ADM_ANALYST_02", decision_outcome: "confirmed_fraud", decision_timestamp: "2026-10-11T11:00:00", status: "confirmed", confirmed_by: "ADM_COMPLIANCE_01", notes: null },
];
const scores = agents.filter((a) => a.flag_source !== "None").sort((a, b) => b.suspicion_score - a.suspicion_score).map((a) => ({
  agent_id: a.agent_id, anomaly_score: a.suspicion_score, threshold: 1.444799, flag_source: a.flag_source, risk_band: a.risk_band,
  top_features: ["collusion_score", "submission_frequency", "customer_similarity"],
}));
const count = (key, value) => agents.filter((a) => a[key] === value).length;
const summary = {
  agents_scored: agents.length, flagged: count("status", "flagged"), flagged_rate: count("status", "flagged") / agents.length, rule_flagged: 6,
  flag_sources: Object.fromEntries(SOURCES.map((s) => [s, count("flag_source", s)])),
  risk_bands: { high: count("risk_band", "high"), review: count("risk_band", "review"), low: count("risk_band", "low") },
  commission_kes: { total: 1000000, flagged_agents: 214000, flagged_share: 0.214 },
  top_features: { as_top_feature: [{ feature: "collusion_score", agents: 3 }, { feature: "customer_similarity", agents: 2 }, { feature: "submission_frequency", agents: 1 }], in_top_three: [] },
};
const days = Array.from({ length: 30 }, (_, i) => ({ date: `2026-08-${String(i + 1).padStart(2, "0")}`, flagged_agents: 300 + ((i * 37) % 120), other_agents: 1200 + ((i * 53) % 300) }));
const audit = [
  { log_id: "AL1", timestamp: "2026-10-13T15:10:00", actor: "ADM_ANALYST_01", actor_type: "user", category: "review", action: "propose_decision", target_agent_id: agents[0].agent_id, request_ip: "10.20.*.*", details: { decision_id: "RD1", decision_outcome: "confirmed_fraud", notes: decisions[0].notes } },
  { log_id: "AL2", timestamp: "2026-10-13T14:02:00", actor: "anonymous", actor_type: "user", category: "authorization", action: "access_denied", target_agent_id: null, request_ip: "10.20.*.*", details: { route: "/api/audit-log", method: "GET", role: null, status: 401, reason: "Authentication required" } },
  { log_id: "AL3", timestamp: "2026-10-13T13:00:00", actor: "system:lof_v3_4f", actor_type: "system", category: "ai_decision", action: "ai_detection_run", target_agent_id: null, request_ip: null, details: { run_id: "RUN1", status: "succeeded", agents_scored: 40, flagged_count: 4 } },
  { log_id: "AL4", timestamp: "2026-10-13T12:00:00", actor: "ADM_ADMIN_01", actor_type: "user", category: "admin", action: "role_change", target_agent_id: null, request_ip: "10.20.*.*", details: { target_admin_id: "ADM_ANALYST_02", target_username: "analyst_02", old_role: "fraud_analyst", new_role: "compliance_officer" } },
];
const ACCOUNTS = {
  fraud_analyst: { username: "analyst_01", role: "fraud_analyst" },
  compliance_officer: { username: "compliance_01", role: "compliance_officer" },
  admin: { username: "admin_01", role: "admin" },
};

function api(role, path) {
  const agentMatch = /^\/api\/agents\/(.+)$/.exec(path);
  if (agentMatch) {
    const a = agents.find((x) => x.agent_id === agentMatch[1]) || agents[0];
    return {
      ...a, registration_timestamp: "2026-06-11T20:56:24",
      identity: { full_name: "Test Agent", phone_number: "**********123", national_id_number: "*****456" },
      features: { submission_frequency: a.submission_frequency, time_of_day_dist: a.time_of_day_dist, customer_similarity: a.customer_similarity, collusion_score: a.collusion_score },
      flag: ["ML", "Both"].includes(a.flag_source) ? { flag_id: "FL1", flag_status: "flagged", model_version: "lof_v3_4f", suspicion_score: a.suspicion_score } : null,
      score: { anomaly_score: a.suspicion_score, threshold: 1.444799, rule_flagged: a.flag_source !== "ML" && a.flag_source !== "None", duplicate_pairs: 3, flag_source: a.flag_source, risk_band: a.risk_band, reasons: "35% of customers also used by other agents vs typical 0%" },
      duplicate_evidence: a.flag_source === "None" ? [] : [{ customer_id: "CUST00000001", client_id: "CL01", other_agent_id: agents[3].agent_id, reason: "shared customer", record_ids: ["R1", "R2"] }],
    };
  }
  const routes = {
    "/api/me": ACCOUNTS[role],
    "/api/all-agents": { count: agents.length, agents },
    "/api/flagged-agents": { count: 4, flagged_agents: agents.filter((a) => a.status === "flagged") },
    "/api/review-decisions": { count: decisions.length, decisions },
    "/api/analytics": {
      cutoff: 1.444799, flag_sources: SOURCES.map((s) => ({ flag_source: s, count: count("flag_source", s) })),
      score_distribution: [{ bucket: "< 1.1", count: 20 }, { bucket: "1.1-1.3", count: 12 }, { bucket: "1.3-cutoff", count: 3 }, { bucket: "cutoff (1.445)-2.0", count: 1 }, { bucket: ">= 2.0", count: 4 }],
      region_breakdown: REGIONS.map((r) => ({ region: r, flagged: agents.filter((a) => a.region === r && a.status === "flagged").length, total: agents.filter((a) => a.region === r).length })),
      platform_averages: { submission_frequency: 15.8, time_of_day_dist: 0.778, customer_similarity: 0.109 },
    },
    "/api/agent-scores": { total: scores.length, count: scores.length, offset: 0, threshold: 1.444799, scores },
    "/api/detection-runs/latest": { run: { run_id: "RUN1", trigger: "scheduler", status: "succeeded", started_at: "2026-10-13T13:00:00", finished_at: "2026-10-13T13:00:09", model_version: "lof_v3_4f", agents_scored: 40, flagged_count: 4 } },
    "/api/threat-intelligence/summary": summary,
    "/api/threat-intelligence/timeline": { first_day: days[0].date, last_day: days.at(-1).date, days },
    "/api/threat-intelligence/by-region": { regions: [], min_agents_for_top: 5, top_by_flagged_rate: REGIONS.map((r, i) => ({ region: r, agents: 7, flagged: 3 - (i % 3), flagged_rate: (3 - (i % 3)) / 7 })) },
    "/api/threat-intelligence/customer-sharing": { shared_customers: 9, clusters_total: 2, clusters: [{ size: 3, agent_ids: agents.slice(0, 3).map((a) => a.agent_id), client_ids: ["CL01", "CL02"], customer_count: 6, flagged_agents: 3 }, { size: 2, agent_ids: agents.slice(6, 8).map((a) => a.agent_id), client_ids: ["CL05"], customer_count: 3, flagged_agents: 0 }] },
    "/api/audit-log": { total: audit.length, count: audit.length, offset: 0, limit: 25, entries: audit },
    "/api/admin/accounts": { count: 4, accounts: [
      { admin_id: "ADM_ADMIN_01", username: "admin_01", role: "admin", is_active: true },
      { admin_id: "ADM_ANALYST_01", username: "analyst_01", role: "fraud_analyst", is_active: true },
      { admin_id: "ADM_COMPLIANCE_01", username: "compliance_01", role: "compliance_officer", is_active: true },
      { admin_id: "ADM_ANALYST_02", username: "analyst_02", role: "fraud_analyst", is_active: false },
    ] },
  };
  return routes[path];
}

const PAGES = {
  fraud_analyst: [["overview", "/"], ["flagged-agents", "/flagged"], ["all-agents", "/all-agents"], ["agent-detail", `/agents/${agents[0].agent_id}`], ["threat-intelligence", "/threat-intelligence"], ["analytics", "/analytics"], ["review-history", "/history"]],
  compliance_officer: [["overview", "/"], ["flagged-agents", "/flagged"], ["all-agents", "/all-agents"], ["agent-detail", `/agents/${agents[0].agent_id}`], ["threat-intelligence", "/threat-intelligence"], ["analytics", "/analytics"], ["review-history", "/history"], ["confirm-queue", "/review/confirm"]],
  admin: [["overview", "/"], ["threat-intelligence", "/threat-intelligence"], ["analytics", "/analytics"], ["audit-log", "/audit-log"], ["reports", "/reports"], ["accounts", "/accounts"], ["access-denied", "/flagged"]],
};

const ROLE_NAMES = { fraud_analyst: "analyst", compliance_officer: "compliance", admin: "admin" };

/** Sideways scroll and touch targets under 44px (inline links in text and table cells are exempt). */
async function measure(page) {
  return page.evaluate(() => {
    const doc = document.documentElement;
    const small = [];
    const coarse = matchMedia("(pointer: coarse)").matches;
    if (coarse) {
      for (const el of document.querySelectorAll("button, [role=button], [role=combobox], input:not([type=hidden]), select, textarea, [role=menuitem], a.MuiListItemButton-root, a.MuiButton-root")) {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0 || el.closest("[aria-hidden=true]")) continue;
        if (el.matches("input[type=radio], input[type=checkbox]")) continue; // the 42px+ label is the target
        if (r.height < 44 - 0.5) small.push(`${el.tagName.toLowerCase()} "${(el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
      }
    }
    return { overflow: doc.scrollWidth - doc.clientWidth, coarse, small };
  });
}

async function settle(page) {
  await page.waitForLoadState("networkidle");
  await page.locator("h1").first().waitFor();
  await page.waitForFunction(() => !document.querySelector("[aria-busy=true]"));
  await page.waitForTimeout(400); // chart animations
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const server = spawn(process.execPath, [join("node_modules", "vite", "bin", "vite.js"), "preview", "--port", String(PORT), "--strictPort", "--host", "127.0.0.1"], { stdio: "ignore" });
  const browser = await chromium.launch({ executablePath: CHROME });
  const report = [];
  try {
    for (let i = 0; i < 50; i += 1) {
      try { await fetch(BASE); break; } catch { await new Promise((r) => setTimeout(r, 200)); }
    }
    // Open drawers and menus are fixed panels, so they are captured at viewport size, not full page.
    const shoot = async (context, page, name, fullPage = true) => {
      const file = `${name}.png`;
      await page.screenshot({ path: join(OUT, file), fullPage });
      const m = await measure(page);
      report.push({ file, ...m });
      process.stdout.write(`${file} overflow=${m.overflow} small=${m.small.length}\n`);
    };

    for (const viewport of WIDTHS) {
      const contextOptions = { viewport: { width: viewport.width, height: viewport.height }, hasTouch: viewport.touch, isMobile: viewport.width < 768, deviceScaleFactor: 1, colorScheme: "light", reducedMotion: "reduce" };

      // Sign-in page (no session).
      {
        const context = await browser.newContext(contextOptions);
        await context.route("**/api/**", (route) => route.fulfill({ status: 401, json: { error: "Authentication required" } }));
        const page = await context.newPage();
        await page.goto(`${BASE}/`);
        await page.getByRole("button", { name: "Sign in" }).waitFor();
        await shoot(context, page, `signin-${viewport.width}`);
        await context.close();
      }

      for (const [role, pages] of Object.entries(PAGES)) {
        const context = await browser.newContext(contextOptions);
        await context.route("**/api/**", (route) => {
          const path = new URL(route.request().url()).pathname;
          const body = api(role, path);
          return body ? route.fulfill({ json: body }) : route.fulfill({ status: 404, json: { error: "Not found" } });
        });
        const page = await context.newPage();
        for (const [name, path] of pages) {
          await page.goto(`${BASE}${path}`);
          await settle(page);
          await shoot(context, page, `${ROLE_NAMES[role]}-${name}-${viewport.width}`);
        }
        if (role === "admin") {
          await page.goto(`${BASE}/audit-log`);
          await settle(page);
          await page.getByRole("button", { name: /^Details of/ }).first().click();
          await page.getByRole("dialog").waitFor();
          await page.waitForTimeout(400);
          await shoot(context, page, `admin-audit-log-drawer-${viewport.width}`, false);
        }
        if (role === "fraud_analyst" && viewport.width < 900) {
          await page.goto(`${BASE}/`);
          await settle(page);
          await page.getByRole("button", { name: "Open menu" }).click();
          await page.getByRole("navigation", { name: "Main menu" }).waitFor();
          await page.waitForTimeout(400);
          await shoot(context, page, `analyst-menu-open-${viewport.width}`, false);
        }
        await context.close();
      }
    }
  } finally {
    await browser.close();
    server.kill();
  }
  writeFileSync(join(OUT, "report.json"), `${JSON.stringify(report, null, 2)}\n`);
  const problems = report.filter((r) => r.overflow > 0 || r.small.length);
  process.stdout.write(`\n${report.length} screenshots, ${problems.length} with problems\n`);
  for (const p of problems) process.stdout.write(`${p.file}: overflow ${p.overflow}px; small targets: ${p.small.join("; ")}\n`);
  process.exitCode = problems.length ? 1 : 0;
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
