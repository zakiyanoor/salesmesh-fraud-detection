# Frontend style guide

This is the visual identity of the SalesMesh fraud detection dashboard, written down from the look it already had. **Every new page follows it.** All values below live as tokens in `frontend/src/theme.js`; components never hard-code a colour or font.

Light and dark are both full colour schemes (MUI `colorSchemes`, issue #28), built from the palettes below. The default is light, whatever the device prefers. The theme menu (Light, Dark) is in the landing header, on the sign-in page and in the signed-in header (the sidebar on desktop, the top bar on phones); MUI remembers the choice under `salesmesh.colorMode`, with storage access wrapped in try and catch, so blocked storage only means the choice is not remembered. A stored value other than light or dark (such as "system" from an earlier version) is switched to light through MUI before the first paint (a layout effect in `ColorModeProvider`), and MUI stores light; no app code touches storage. A small first-party script in `index.html` paints dark only when dark is stored, light otherwise, so there is no flash of the wrong scheme; `theme.test.js` checks its colours match the palettes. CSS variables are off, so every colour that charts and SVG drawings read from the theme is the active scheme's real value.

## Palette tokens

| Token | Light (default) | Dark | Use |
|---|---|---|---|
| `background.default` | `#F5F7FA` | `#0F141A` | Page background |
| `background.paper` | `#FFFFFF` | `#171D24` | Cards, drawer, tables, tooltips |
| `divider` | `#D9DEE5` | `#2A333D` | Card borders, table rules, chart grid |
| `text.primary` | `#14171C` | `#E6E9ED` | Body text, numbers |
| `text.secondary` | `#4B5563` | `#9AA4B1` | Captions, overlines, column hints |
| `primary.main` | `#1976D2` | `#64A8F0` | Contained buttons, focus, the score figure, primary bars |
| `primary.dark` | `#1565C0` | `#8DC0F5` | Primary-coloured **text** on page or tinted backgrounds (text buttons, active menu item) |
| `primary.contrastText` | `#FFFFFF` | `#0F141A` | Text on contained primary buttons |
| `error.main` | `#D32F2F` | `#F28B82` | Flagged, confirmed fraud, risk `high` |
| `warning.main` | `#B45309` | `#F0A848` | Risk `review` |
| `success.main` | `#2E7D4F` | `#5FC48B` | Clear, legitimate, risk `low` |
| `action.selected` | `rgba(25, 118, 210, 0.08)` | `rgba(100, 168, 240, 0.16)` | Active menu item background |

**Risk band tokens** (`palette.risk`). Each band is always shown with a text label **and** an icon (`RiskBadge`), never colour alone.

| Band | Colour token | Label | Icon |
|---|---|---|---|
| `high` | `error.main` | High risk | Report (octagon) |
| `review` | `warning.main` | Review | Warning (triangle) |
| `low` | `success.main` | Low risk | Check circle |
| none (`null`) | `text.secondary` | Not scored | Help circle |

**Chart tokens** (`palette.chart`):

| Token | Light | Dark | Use |
|---|---|---|---|
| `chart.grid` | `divider` | `divider` | Cartesian grid lines (dashed `3 3`) |
| `chart.axis` | `text.secondary` | `text.secondary` | Axis lines and tick labels (12px) |
| `chart.neutral` | `#8A9199` | `#6E7A87` | Context bars (for example "total" beside "flagged") |
| `chart.region` | `#1976D2`, `#00897B`, `#F59E0B`, `#8E24AA`, `#546E7A` | `#64A8F0`, `#26A69A`, `#F59E0B`, `#BA68C8`, `#90A4AE` | Categorical series such as regions. Kept apart from red, amber and green, which mean status and risk |

## Typography

| Role | Font | Weights | Fallback |
|---|---|---|---|
| Body, buttons, tables | IBM Plex Sans | 400, 500 | system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif |
| Headings h1 to h6 | Space Grotesk | 600 (500 and 700 loaded) | same as body |
| Ids, scores, counts, timestamps in tables | IBM Plex Mono | 400, 500, 600 | ui-monospace, SFMono-Regular, Menlo, Consolas, monospace |

- Fonts are bundled from `@fontsource` packages, so no font requests leave the app.
- Use the `mono` style from `theme.js` (`sx={mono}`) for every agent id, score and count. Do not repeat the font name.
- Buttons are not upper-cased (`textTransform: none`, weight 500).
- Page title: `h4`. Page subtitle: `body2` in `text.secondary`, 32px below. Section label: `overline` in `text.secondary`.

## Shape and surfaces

- **Border radius:** 4px (`shape.borderRadius`).
- **Cards:** `Paper` on `background.paper`, a 1px `divider` border, no shadow and no background image. Padding 24px (`p: 3`); KPI cards use 20px (`p: 2.5`).
- **Buttons:** flat, with no shadow, including on hover. Primary actions are `contained`; secondary actions are text buttons.

## Tables

- `Table size="small"` inside a `TableContainer`, so a wide table scrolls inside itself and never makes the page scroll sideways.
- Ids, scores and numbers in `mono`; scores show 3 decimals; a missing value shows a dash.
- Rows are `hover`. An empty result is one full-width row in `text.secondary`, 32px vertical padding.
- A `Divider` (16px below) separates the filters from the table.
- **Lists use `DataTable`** (`components/DataTable.jsx`):
  - Sortable columns use `TableSortLabel`. Missing values sort last.
  - Paging is 25 rows by default (10, 25, 50 or 100).
  - **Below `md`** each row becomes a card: the title column at the top, the other columns as label and value pairs, and action buttons at the bottom.
- **Filters, sort and page live in the URL query string** (`hooks/useQueryParams.js`), so a refresh or Back restores them. A value equal to its default is left out of the URL. "Clear filters" appears once any filter is set.
- An agent id is a link to agent detail (in `primary.dark`) wherever the role may open it, and plain text otherwise.

## Chips

- `size="small"` and `variant="outlined"`.
- Status: `error` for flagged or confirmed fraud, `success` for clear or legitimate.
- Risk: `RiskBadge` only (label and icon, coloured by `palette.risk`).
- Flag source: `FlagSourceChip`. Model, Model and rule, and Rule only are neutral; "Not flagged" is `success` with a check icon.
- Decision status: `DecisionStatusChip`. Proposed is `warning` with an hourglass, Agreed is `success` with a check, Overruled is `info` with swapped arrows, Withdrawn is neutral with an undo arrow, and Not reviewed is neutral.
- Review markers: `OverdueChip` (`error`, clock) for a proposal waiting more than 3 days, `NoLongerFlaggedChip` (flag) when the agent is not flagged in the latest run, and `CorrectedChip` (note) for a corrected decision.
- Decision outcome: `OutcomeChip`. Confirmed fraud is `error` with a gavel, and Legitimate is `success` with a check.

## Sidebar

- 240px wide drawer on `background.paper`, with a 1px `divider` right border and 24px padding.
- "SalesMesh" in `h6` above "Fraud Detection" in `caption`, `text.secondary`, with 32px below.
- Menu items: outlined icons with 36px minimum icon width, label in `body2`, radius 4px, 4px apart. The active item has an `action.selected` background with `primary.dark` text and icon.
- Header: the brand, with the theme menu beside it on desktop (on phones the top bar has it).
- Footer: a divider, "Signed in as" with the username and role in `caption`, and the "Sign out" text button.
- **From `md` up** the drawer is permanent. **Below `md`** it is a temporary drawer opened by a menu button in a top bar.

## Charts

- **Donut cards:** 140px chart, inner radius 44, outer radius 64, 2px padding between slices (none for a single slice), no stroke. The total sits in the centre in `h5` mono. A legend beside the chart lists a 10px dot, the name, the count in mono and the share in `caption` mono. With no data the ring is a single `divider` slice.
- **Bar charts:** in a `ResponsiveContainer` 220px high, dashed grid in `chart.grid`, axes in `chart.axis` at 12px, integer y ticks, bar radius `[3, 3, 0, 0]`.
  - Horizontal bars use radius `[0, 3, 3, 0]`.
  - A bar per risk band takes its colour from `palette.risk`, with the band name on the axis.
- **Line charts:** the same grid, axes and height, 2px lines and no dots. A second series is dashed, so the lines differ by more than colour.
- **Legends:** 12px in `text.secondary`, on any chart with more than one series.
- **Tooltips:** `background.paper` background, 1px `divider` border, `text.primary` text.

## States

- **Loading:** a skeleton shaped like the content (title, cards, table rows), not a spinner.
- **Empty:** a short sentence in `text.secondary` saying what is missing.
- **Error:** what went wrong and a "Try again" button.
- **Access denied:** shown on a 403 and on `/403`.
- **Pages with several sources** give each card its own state (`SectionCard`), so one failed request leaves the other cards working, and each failed card has its own "Try again".
- **Downloads** (`ReportCard` on Reports):
  - while the file is prepared, the button reads "Preparing…" with a small spinner and is disabled;
  - a failure shows "Download failed:" with the server's reason;
  - a success names the saved file.
  - The file name always comes from the response's `Content-Disposition` header.

## Drawers and dialogs

- **Details drawer** (`AuditDrawer`):
  - opens from the right, 440px wide from `sm` up and full width below;
  - opened by clicking a row or its "Details" button;
  - as a modal it traps focus, closes with Esc or the close button, and returns focus to the row or button that opened it;
  - details are shown as label and value pairs, and any key that looks like a secret (`password`, `hash`, `secret`, `token`, `cookie`, `session`) is left out.
- **Confirm dialogs:** every review action and every account change opens a small dialog that says what will happen. Review actions use `NoteDialog`: withdraw (note required), agree (note optional), overrule and correct (the other outcome preset, note required). The server's refusal (your own proposal, your own account, the last admin, an outdated correction) appears inside it as an error alert, and the row stays as it was. A proposal that was closed meanwhile (`409`) leaves the queue with a message saying so.

## Footer

Every signed-in page ends with one line in `caption`, `text.secondary`, above a 1px `divider` rule: "Model lof_v3_4f · Last detection run <time>". The run status is added when the run did not succeed. Without a run it says so.

## Responsive rules

Checked at 360, 768 and 1280 px by `npm run screenshots` (see "Screenshots" below), which fails on any sideways scroll or small touch target.

**Layout:**
- **Navigation:** a permanent 240px drawer from `md` (900px) up. Below `md`, a top bar with a menu button opens a temporary drawer, which closes after each choice.
- **Content padding:** 40px from `md` up, 16px below.
- **Rows** of filters, summary cards and chart cards wrap. Summary cards are at least 160px wide, so five fit on one row at 1280px. The Overview uses one instrument bar instead (see Overview below), five cells on one row from 900px and two columns below.
- **Nothing scrolls sideways** at any width. Tables below `md` become cards (`DataTable`); fixed tables (evidence, chart data) scroll inside their own `TableContainer`.
- **Filter fields** are full width on phones and a fixed width from `sm` up.
- **The audit details drawer** is 440px wide from `sm` up and full width on phones.

**Touch** (`pointer: coarse`): buttons, icon buttons, menu and list items, small text fields, selects and the rows-per-page select are at least 44px high. With a mouse they keep their compact size. Radio buttons are exempt, because their label is the target; links inside table cells and text are exempt as inline targets.

## Accessibility rules

Checked by `frontend/src/test/a11y.test.jsx` (axe on every page for its roles, the landing page at 360 and 1280 px and the sign-in page in both schemes, a signed-in page with charts and the ring graph in the dark scheme, the phone menu, the audit drawer, the agree and overrule dialogs, the customer dialog, the ring graph with a selected agent and a chart's table view) and `frontend/src/theme.test.js` (contrast).

- **Structure:**
  - one `h1` per page (the page title); section titles are `h2`;
  - no heading used only for its size (figures such as the donut total are paragraphs).
- **Landmarks:**
  - a header (the brand on desktop, the top bar on phones);
  - the main menu as `nav`;
  - the page in `main`;
  - the footer as `footer`.
- **Skip link:** "Skip to content" is the first Tab stop, hidden until focused, and moves focus to `main`.
- **Focus:**
  - every focusable element shows a 2px `primary.main` ring on keyboard focus (3:1 against page and card);
  - dialogs and the drawer trap focus, close with Esc, and return focus to what opened them.
- **Labels:** every input has a visible label, or an `aria-label` where the field has an icon and a placeholder (search).
- **Live regions:**
  - loading states are `role="status"` with `aria-busy` and visually hidden "Loading…" text;
  - results are announced: proposal and confirmation messages and download results are `status`, and errors are `alert`.
- **Charts:**
  - every chart card names its chart (`role="img"`);
  - each has a "Show as table" toggle (`aria-pressed`) that shows the same numbers as a table.
- **Colour:**
  - never the only signal: risk bands, decision status, outcomes, flag sources and audit results always have a text label and an icon;
  - the second series in line charts is dashed.
- **Contrast:**
  - text meets WCAG AA (4.5:1) on `background.default` and `background.paper` in both modes, which covers every chip colour (`error`, `warning`, `success`, `primary.dark`);
  - graphics and chart series meet 3:1, or carry their meaning in a text label or legend (the amber region colour does this).

## Client security rules

Checked by `frontend/src/test/security.test.jsx`.

- **No HTML injection:** there is no `dangerouslySetInnerHTML`, `innerHTML` or `eval`. All user text (notes, usernames, audit details) is rendered as text.
- **Storage:** only `salesmesh.colorMode` is stored in the browser. The username and role live in memory, and the session is the server's HTTP-only cookie.
- **Requests:** only `src/api.js` calls `fetch`, and only it sends credentials, to `VITE_API_BASE` (default `/api`) and nowhere else. File downloads use the same path.
- **Session end:**
  - a 401 from any request returns to the sign-in page once, with no request loop;
  - signing out clears the client state even when the server cannot be reached.

## Screenshots

`docs/screenshots/` holds 74 screenshots of every page for each role at 360, 768 and 1280 px, named `<role>-<page>-<width>.png`.
- **How they were made:** `npm run screenshots`, against the production build with fictional mocked data. Agent ids, regions, masked numbers and notes are made up, and there is no real personal data.
- **Capture:** full page, except open drawers and menus, which are captured at viewport size.
- **`report.json`:** records, for each screenshot, sideways scroll (all 0) and touch targets under 44px (none).

| Screen | Widths |
|---|---|
| `signin` | [360](screenshots/signin-360.png), [768](screenshots/signin-768.png), [1280](screenshots/signin-1280.png) |
| `analyst-agent-detail` | [360](screenshots/analyst-agent-detail-360.png), [768](screenshots/analyst-agent-detail-768.png), [1280](screenshots/analyst-agent-detail-1280.png) |
| `analyst-all-agents` | [360](screenshots/analyst-all-agents-360.png), [768](screenshots/analyst-all-agents-768.png), [1280](screenshots/analyst-all-agents-1280.png) |
| `analyst-analytics` | [360](screenshots/analyst-analytics-360.png), [768](screenshots/analyst-analytics-768.png), [1280](screenshots/analyst-analytics-1280.png) |
| `analyst-flagged-agents` | [360](screenshots/analyst-flagged-agents-360.png), [768](screenshots/analyst-flagged-agents-768.png), [1280](screenshots/analyst-flagged-agents-1280.png) |
| `analyst-menu-open` | [360](screenshots/analyst-menu-open-360.png), [768](screenshots/analyst-menu-open-768.png) |
| `analyst-overview` | [360](screenshots/analyst-overview-360.png), [768](screenshots/analyst-overview-768.png), [1280](screenshots/analyst-overview-1280.png) |
| `analyst-review-history` | [360](screenshots/analyst-review-history-360.png), [768](screenshots/analyst-review-history-768.png), [1280](screenshots/analyst-review-history-1280.png) |
| `analyst-threat-intelligence` | [360](screenshots/analyst-threat-intelligence-360.png), [768](screenshots/analyst-threat-intelligence-768.png), [1280](screenshots/analyst-threat-intelligence-1280.png) |
| `compliance-agent-detail` | [360](screenshots/compliance-agent-detail-360.png), [768](screenshots/compliance-agent-detail-768.png), [1280](screenshots/compliance-agent-detail-1280.png) |
| `compliance-all-agents` | [360](screenshots/compliance-all-agents-360.png), [768](screenshots/compliance-all-agents-768.png), [1280](screenshots/compliance-all-agents-1280.png) |
| `compliance-analytics` | [360](screenshots/compliance-analytics-360.png), [768](screenshots/compliance-analytics-768.png), [1280](screenshots/compliance-analytics-1280.png) |
| `compliance-confirm-queue` | [360](screenshots/compliance-confirm-queue-360.png), [768](screenshots/compliance-confirm-queue-768.png), [1280](screenshots/compliance-confirm-queue-1280.png) |
| `compliance-flagged-agents` | [360](screenshots/compliance-flagged-agents-360.png), [768](screenshots/compliance-flagged-agents-768.png), [1280](screenshots/compliance-flagged-agents-1280.png) |
| `compliance-overview` | [360](screenshots/compliance-overview-360.png), [768](screenshots/compliance-overview-768.png), [1280](screenshots/compliance-overview-1280.png) |
| `compliance-review-history` | [360](screenshots/compliance-review-history-360.png), [768](screenshots/compliance-review-history-768.png), [1280](screenshots/compliance-review-history-1280.png) |
| `compliance-threat-intelligence` | [360](screenshots/compliance-threat-intelligence-360.png), [768](screenshots/compliance-threat-intelligence-768.png), [1280](screenshots/compliance-threat-intelligence-1280.png) |
| `admin-access-denied` | [360](screenshots/admin-access-denied-360.png), [768](screenshots/admin-access-denied-768.png), [1280](screenshots/admin-access-denied-1280.png) |
| `admin-accounts` | [360](screenshots/admin-accounts-360.png), [768](screenshots/admin-accounts-768.png), [1280](screenshots/admin-accounts-1280.png) |
| `admin-analytics` | [360](screenshots/admin-analytics-360.png), [768](screenshots/admin-analytics-768.png), [1280](screenshots/admin-analytics-1280.png) |
| `admin-audit-log` | [360](screenshots/admin-audit-log-360.png), [768](screenshots/admin-audit-log-768.png), [1280](screenshots/admin-audit-log-1280.png) |
| `admin-audit-log-drawer` | [360](screenshots/admin-audit-log-drawer-360.png), [768](screenshots/admin-audit-log-drawer-768.png), [1280](screenshots/admin-audit-log-drawer-1280.png) |
| `admin-overview` | [360](screenshots/admin-overview-360.png), [768](screenshots/admin-overview-768.png), [1280](screenshots/admin-overview-1280.png) |
| `admin-reports` | [360](screenshots/admin-reports-360.png), [768](screenshots/admin-reports-768.png), [1280](screenshots/admin-reports-1280.png) |
| `admin-threat-intelligence` | [360](screenshots/admin-threat-intelligence-360.png), [768](screenshots/admin-threat-intelligence-768.png), [1280](screenshots/admin-threat-intelligence-1280.png) |

## Known limitations

- **Compliance officers and the audit log:** the API (`GET /api/audit-log`) also lets compliance officers read the audit log. The app hides the menu item and guards the route for them, but the server would answer them.
- **No "You" marker in review history and the confirm queue:** proposer and officer show as account ids. Marking your own decisions needs your account id, and `GET /api/me` returns only the username and role. Agent detail knows whether an open proposal is yours from `review.open_is_mine`.
- **Accounts:** creating accounts and resetting passwords happen on the server (`python -m src.auth` for the demo accounts, `python -m src.manage_accounts reset-password`). There is no API for either, so the Accounts page only lists accounts, changes roles and deactivates or reactivates them.
- **Audit log filters:** the API offers no action or outcome filter, so the page filters by category, actor, agent id and date range. The Result column is derived from the action.

## Review wording

A proposal has no effect until a compliance officer other than the proposer agrees or overrules it (issue #28). All wording comes from `frontend/src/review.js`:

| Moment | Text |
|---|---|
| After proposing | "Decision proposed. It is waiting for a compliance officer to confirm it and has no effect until then." |
| After withdrawing | "Proposal withdrawn. You can propose again on this flag." |
| After agreeing or overruling | "Proposal for <agent> agreed." or "... overruled.", then "The final outcome is <outcome>." |
| After a correction | "Correction recorded for <agent>. The outcome in force is now <outcome>; the history keeps the original decision." |
| Status chips | Proposed, Withdrawn, Agreed, Overruled |

A proposal is never called saved, recorded or final; tests check this.

**Notes:**
- Required, 1 to 1000 characters after trimming.
- A live counter shows the length.
- The hint says that runs of 7 or more digits are masked when saved.
- Older decisions without notes say so instead of showing a blank.
- The same rules apply to every review note; only an agreement's note is optional.

**Decision timeline** (agent detail, and "History" in review history): the proposal, then its withdrawal, agreement or overrule, then each correction, each with who, when, the outcomes and the note, and the outcome in force when a correction exists.

## Pages

| Route | Page | Roles | Endpoints |
|---|---|---|---|
| `/` | Overview: instrument bar of five figures, flag source ring, risk band bars, needs attention with score bars | all | `/api/threat-intelligence/summary`, `/api/detection-runs/latest`, `/api/agent-scores?limit=50`, `/api/model-info` |
| `/flagged` | Flagged agents (model, rule or both) | fraud_analyst, compliance_officer | `/api/all-agents`, `/api/review-decisions` |
| `/all-agents` | All agents, with a "Not flagged" state | fraud_analyst, compliance_officer | `/api/all-agents`, `/api/review-decisions` |
| `/agents/:agentId` | Agent detail, evidence (customers open the customer dialog), daily activity and activations by hour of day, decision timeline; propose and withdraw (fraud_analyst), record a correction (compliance_officer) | fraud_analyst, compliance_officer | `/api/agents/<id>`, `/api/agents/<id>/activity`, `/api/analytics`, `/api/review-decisions`, `/api/customers/<ref>`, `POST /api/review-decisions`, `POST .../withdraw`, `POST .../corrections` |
| `/review/confirm` | Confirm queue: agree or overrule, overdue and "no longer flagged" markers | compliance_officer | `/api/review-decisions`, `POST /api/review-decisions/<id>/agree`, `POST .../overrule` |
| `/history` | Review history: status, outcome in force, who closed it, each decision's timeline | fraud_analyst, compliance_officer | `/api/review-decisions` |
| `/analytics` | Analytics: daily activations, score distribution, region rates, review outcomes and overrule rate, averages | all | `/api/analytics`, `/api/threat-intelligence/timeline`, `/api/threat-intelligence/by-region` |
| `/threat-intelligence` | Threat intelligence: summary, flag sources, drivers, timeline, regional rates, top risk agents, ring candidates with a ring graph and group activity, connected agents | all | `/api/threat-intelligence/summary`, `/timeline`, `/by-region`, `/customer-sharing`, `/ring-candidates`, `/ring-candidates/<id>`, `/api/agent-scores?limit=10` |
| `/audit-log` | Audit log with server-side filters and paging, details drawer | admin | `/api/audit-log` |
| `/how-it-works` | How the model works: what the system does, the four signals, the rule, flag sources and risk bands, scores and the cutoff, test results, glossary | all | `/api/model-info` |
| `/reports` | Report downloads | admin | `/api/reports/flagged-agents.csv`, `/api/reports/audit-log.csv`, `/api/reports/detection-summary.pdf` |
| `/accounts` | Accounts: list, change role, deactivate, reactivate | admin | `/api/admin/accounts`, `PATCH .../role`, `POST .../deactivate`, `POST .../reactivate` |
| every signed-in page | Footer: model version and last detection run | all | `/api/detection-runs/latest` |
| `/` (signed out) | Landing page: navigation, headline, Sign in, a globe centred on Kenya, four cards, footer | anyone | none (the session check that runs before any page is the only request) |
| `/sign-in` | The sign-in form; once signed in it opens the page in `?next=` if it is safe and the role may open it, otherwise the usual home page (`/`) | anyone | `POST /api/login` |
| `/403`, any other address | Access denied, Page not found | all | none |

**Notes on what is shown:**
- **Dates and times:** one shared format on every page and in the footer, `formatDate` and `formatDateTime` in `format.js`: day, short month name, year and 24 hour time in Nairobi time, for example "13 Oct 2026, 17:26" (`Intl.DateTimeFormat`, en-GB, `Africa/Nairobi`). No page shows a month first date or the browser's own zone. The API sends times without a zone: system events (detection runs, review decisions, corrections, audit entries) are stored in UTC and are converted; activation data (activation records, customer first and last seen, agent registration) is stored as recorded in Nairobi time and is shown unchanged (`{ recorded: true }`).
- Agent ids are system codes, not personal data, so they are shown in full.
- Phone and national ID numbers are masked by the server (last 3 digits). Agent detail shortens the name to initials.
- Internal ids (flag, decision and run ids) are never shown.
- **Overview** (issue #28, `pages/Dashboard.jsx`): the console look for the analyst, flat panels with a 1px border and an 8px radius, no icons or shadows.
  - Under the title, when the latest run is more than 48 hours old, a plain secondary line: "The latest detection run is N days old. The figures below describe that run."
  - Instrument bar ("Summary"): one bordered panel with five cells split by hairlines: Agents scored, Flagged (high risk), Review band, Rule-only flags and Last detection run. Each cell has a 13px label over a figure in the display font with tabular numerals (32px; 40px for Flagged). Only Flagged and Review have a 3px status edge (danger, amber); the figures stay in the text colour. Under Flagged: "Flagged by the model. Rule only flags are counted separately." Last detection run shows a small solid status dot, the status and the date. Two columns below 900px, the last cell across both.
  - Flag sources: a slim ring (12px, 2 degree gaps) with the total in the centre, one blue family for Model, Model and rule and Rule only, and neutral grey for Not flagged; the legend keeps counts and percentages, and sits under the ring on phones. Risk bands: horizontal bars with the count at the end of each bar, no value axis, hairline grid; High risk danger, Review amber, Low risk neutral grey (never green). Both keep "Show as table". Panel headings are 16px semibold in sentence case with a 13px subtitle (`SectionCard` with `panel`); the Risk bands subtitle is its three definitions on three lines.
  - Needs attention: tight rows with hairline rules, the agent ID in monospace, tabular numerals and Flagged by as a chip. Under each score a thin bar of the score against the model cutoff, with a tick at the cutoff; the cutoff comes from `GET /api/model-info` (as on How the model works), and the bar's text value for screen readers is "At or above the model cutoff of 1.445" or "Below ...". Below 600px the table becomes a compact list.
  - Under the table: "See all flagged agents" (for roles that may open Flagged agents), then "These figures include agents the model learned from. Accuracy figures come only from the T test agents.", with T the test set size from `/api/model-info`; without it only the first sentence shows. The page makes no other accuracy claim.
- **Landing page** (issue #28, `pages/Landing.jsx`, copy in `pages/landingContent.js`):
  - Signed out at the site root, the landing page opens; any other address still shows the sign-in form and opens that address after signing in. If the sign-in form has a message (for example a deactivated account or an unreachable server), the root shows the form with it instead.
  - Content: a header with "SalesMesh", the navigation, Sign in and the theme menu; the hero with the headline "Fraud detection for sales agent networks.", one line under it, a Sign in button and the globe; four cards under "What the platform does" (Detection, Review, Investigation, Accountability); a footer. A signed-in user at the root sees the usual home page, Overview.
  - Navigation (`auth/redirect.js`): the menu pages every role may open, read from `PAGES` in `auth/roles.js` (`SHARED_PAGES`): Overview, Threat intelligence, Analytics and How the model works. The agent lists are for reviewers only, so they are not in it. Signed out, each link goes to `/sign-in?next=<page>`; after signing in, `/sign-in` (`auth/AfterSignIn.jsx`) opens that page. `safeTarget` accepts only a path with a single leading slash, no backslash, space or scheme, that matches a known route the role may open; anything else opens Overview, so the parameter cannot redirect elsewhere. Below 900px the links collapse into a menu button (`aria-expanded`, `aria-controls`) with a list labelled "Main".
  - Footer: "SalesMesh" and "Fraud detection for sales agent networks."; a wide brand block on the left, then Platform (the same pages as the navigation, through sign in) and Security (plain lines naming the four security points) side by side; a bottom bar with "2026 SalesMesh" and "Nairobi, Kenya", and no link.
  - Look (`pages/surfaces.js`, shared with the sign-in page): light is the main face and is designed on its own terms. A cool off-white page, a near black headline in the display font, deep slate secondary text, and one accent: in light the deeper blue (`primary.dark`, 5.75:1 with white, 5.35:1 on the page), in dark the lighter blue. Depth comes from structure: crisp visible rules, a lightly tinted hero band with a fine dot texture at very low contrast, white cards on a faintly tinted section with a very faint grid, and a white footer. No shadows except the globe's soft contact shadow. Buttons, links and the menu have hover, pressed and focus states in both schemes; the cards change only their border and left edge on hover. Headline 40, 52 or 64px, the line under it 18 or 20px, cards 15px, footer 14px; a 6px radius (8px on the cards). Two columns in the hero from 900px (text left, globe right); below that the globe sits under the hero and is smaller.
  - Cards (`pages/PlatformCards.jsx`, content in `CARDS` in `pages/landingContent.js`): four equal cards in a two by two grid from 900px, one column below, with a generous gap. Each card, top to bottom: a small label chip (monospace 12px, thin border, 4px radius, normal case: Scoring, Decisions, Analysis, Records), the heading in the display font at 22px, the paragraph in the secondary colour at about 55 characters a line, and one text link. The links go to pages all three roles may open, through sign in while signed out like the navigation: Detection to How the model works, Review to Analytics ("Open analytics", which holds Review outcomes; the confirm queue is for compliance officers only), Investigation to Threat intelligence, Accountability to Overview ("Open the overview"; the audit log is for admins only). A test checks every card link is in `SHARED_PAGES`. Surfaces are flat: a thin border, an 8px radius, padding 32px, no shadow, gradient or glow; the card is a little lighter than the section (white in light, the deep blue grey paper in dark, with a low contrast blue grey border). On hover, or while the link has focus, the border turns to the accent and a 2px accent edge shows down the left side. The chip is a pale accent tint with the deeper accent text in light, a dark fill with a subtle border and muted accent text in dark. The card is not a tab stop; only its link is. The section behind the cards has a very faint 32px grid.
  - Sign-in page (`pages/Login.jsx`): the hero's tinted, dotted surface behind a white card with a visible border, the name, the product line and the accent Sign in button.
  - The globe (`components/globe/KenyaGlobe.jsx`, with a soft contact shadow under it on the page, the npm package `cobe`, bundled by Vite in its own chunk, no outside request): a dark sphere in both schemes (`components/globe/sphereColours.js`, the dark palette), with a thin accent ring, zoomed in (scale 12) so Kenya fills about two thirds of its width, swaying 0.6 degrees either side over 18 seconds, with one accent dot for each of the 47 counties at its headquarters town (`components/globe/kenyaCounties.js`, the county names of `ml/data_generation.py`) over a finer neutral dot grid. No text on the globe.
    - It mounts after the first paint, in a space reserved from the start, so the headline and Sign in appear at once and nothing moves.
    - It pauses while the tab is hidden or the globe is off screen. With reduced motion it is one still image facing Kenya: cobe loads its map asynchronously and does not redraw when it arrives, so that same image is repainted for about a second while the map loads, then nothing more is drawn.
    - Without WebGL, a still SVG drawing stands in (`components/globe/GlobeFallback.jsx`): the same dark sphere with Kenya's outline, its dot grid and the counties, at the same size.
    - The pixel ratio is capped at 2, the canvas follows its container, and everything is released on unmount.
    - It is decorative (`aria-hidden`); the text carries the meaning.
  - It makes no API calls of its own, loads no third-party script or font, and has no tracking.
  - Checked at 360, 768, 1000 and 1280 px in Chrome in both schemes: no horizontal scroll, the first Tab stop is the first navigation link (the menu button on narrow screens). The globe drew with WebGL in headless Chrome without a software GL flag.
  - Masked identifiers are not listed: the change that would mask customer IDs is on hold and not in `main`.
  - The four security points, each backed by code:
    - role based access: `backend/src/auth.py` (`role_required`, `refresh_session`);
    - two person review of every decision: `backend/src/review.py` (the proposer can never agree, overrule or correct) and the write-once triggers in `backend/src/db.py`;
    - an append only audit log: `backend/src/audit.py` and the trigger in `backend/src/db.py`;
    - secure sessions: `backend/src/config.py` (HttpOnly always, Secure and SameSite, a set lifetime) and `refresh_session` in `backend/src/auth.py`.
- **How the model works** (issue #28): a menu entry for every role, last in the menu. Plain words for a non-technical reader. The cutoff and the test results come from `GET /api/model-info`, which reads the frozen results files; the page states they were measured on the 150 held-out test agents and are not a promise for other data, and that detection runs on a schedule, not live. The system's (model or rule) PR AUC and ROC AUC are shown as "not comparable", because they come from a yes or no flag.
- **Ring graph** (issue #28): the ring candidates card shows the first candidate as a graph, and each row has a "Show" button for its own. The graph is plain SVG with no graph library. Agents sit on a circle in agent ID order, the first at the top (`components/ringLayout.js`, deterministic). An edge means two agents share customers and is labelled only with the count; solid red edges reach the rule's 3 shared customers, dashed grey ones do not. Each agent is a button: Tab moves between agents, Enter or Space highlights its pairs, Escape clears, and a live line names the agents it shares customers with. Beside it, a table lists the same pairs and a members table gives each agent's county, flag source and activations, with the number of distinct counties and a note that county is information only. A "Group activity" bar chart shows the members' activations per day, with "Show as table".
- **Daily activity** (issue #28): agent detail ends with a table of the agent's activations and completed activations for every day of the data window, with a "Duplicate evidence on this day" chip on days that hold a record in the agent's duplicate evidence, and a bar chart of activations by hour of day (0 to 23) with "Show as table". Both say that days and hours are as recorded in the data, and that the flag applies to the agent for the whole run. Dates are shown as recorded, without time-zone conversion.
- **Customer dialog** (issue #28): each customer in the evidence table is a button that opens `CustomerDialog`. It fetches `GET /api/customers/<customer_ref>?from_agent=<agent>` on every open (every open is audited by the server) and shows the customer ID as the table does, the agents who used it (linked, with their flag source), the client count and IDs, first and last dates, and the latest activations, saying "Showing the latest N of M activations" when the list is capped. A note says that opening the view is recorded in the audit log. The request uses the reference, so the customer ID never appears in a URL.
- Proposer and officer are shown as the account ids the API returns. Usernames are not available to these roles.
- **Agent ids for admins:** they cannot open agent detail, so they see agent ids as plain text everywhere: Overview, Threat intelligence and the Audit log (`AgentId` component).
- **Audit log is admin only** in the app. The API also lets compliance officers read it, but the menu and route allow admins only.
- **Audit log filters:** the API offers no action or outcome filter, so the page filters by category, actor, agent id and date range. The Result column (Completed, Refused, Failed) is derived from the action for display only.
- **Accounts:** creating accounts and resetting passwords have no API, so the Accounts page says they are done on the server (`python -m src.manage_accounts reset-password`).
- Any flagged agent can be reviewed, whether the model, the rule or both flagged it (issue #28). The review section follows the API's `review` block; an agent nobody flagged shows why there is nothing to review.

## Branding

Only the SalesMesh name and its own mark (`public/favicon.svg`) appear. No third-party product name, logo or branding is used in the interface or its assets.
