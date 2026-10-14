# Frontend style guide

This is the visual identity of the SalesMesh fraud detection dashboard, written down from the look it already had. **Every new page follows it.** All values below live as tokens in `frontend/src/theme.js`; components never hard-code a colour or font.

The light theme is the default. Dark mode is optional, behind a toggle, and is derived from the same palette.

## Palette tokens

| Token | Light (default) | Dark | Use |
|---|---|---|---|
| `background.default` | `#F5F7FA` | `#0F141A` | Page background |
| `background.paper` | `#FFFFFF` | `#171D24` | Cards, drawer, tables, tooltips |
| `divider` | `#E0E4E8` | `#2A333D` | Card borders, table rules, chart grid |
| `text.primary` | `#1A1D21` | `#E6E9ED` | Body text, numbers |
| `text.secondary` | `#6B7280` | `#9AA4B1` | Captions, overlines, column hints |
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
- Decision status: `DecisionStatusChip`. Proposed is `warning` with an hourglass, Confirmed is `success` with a check, and Not reviewed is neutral.
- Decision outcome: `OutcomeChip`. Confirmed fraud is `error` with a gavel, and Legitimate is `success` with a check.

## Sidebar

- 240px wide drawer on `background.paper`, with a 1px `divider` right border and 24px padding.
- "SalesMesh" in `h6` above "Fraud Detection" in `caption`, `text.secondary`, with 32px below.
- Menu items: outlined icons with 36px minimum icon width, label in `body2`, radius 4px, 4px apart. The active item has an `action.selected` background with `primary.dark` text and icon.
- Footer: a divider, "Signed in as" with the username and role in `caption`, the dark mode toggle and the "Sign out" text button.
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
- **Confirm dialogs:** confirming a decision and changing an account both open a small dialog that says what will happen. The server's refusal (your own proposal, your own account, the last admin) appears inside it as an error alert, and the row stays as it was.

## Footer

Every signed-in page ends with one line in `caption`, `text.secondary`, above a 1px `divider` rule: "Model lof_v3_4f · Last detection run <time>". The run status is added when the run did not succeed. Without a run it says so.

## Layout and touch

- Content padding: 40px from `md` up, 16px below.
- Rows of filters and cards wrap; nothing scrolls sideways at 360px.
- On touch screens (`pointer: coarse`) buttons, icon buttons, menu items and list items are at least 44px high. With a mouse they keep their compact size.

## Accessibility

- Text meets WCAG AA (4.5:1) on `background.default` and `background.paper` in both modes. Graphics and chart series meet 3:1, or carry their meaning in a text label or legend (the amber region colour does this).
- `frontend/src/theme.test.js` checks the text contrast ratios.
- Colour never carries meaning alone: risk, status and decision chips always have a text label.

## Review wording

A decision has no effect until a compliance officer other than the proposer confirms it. All wording comes from `frontend/src/review.js`:

| Moment | Text |
|---|---|
| After proposing | "Decision proposed. It is waiting for a compliance officer to confirm it and has no effect until then." |
| After confirming | "Decision for <agent> confirmed. It is now final." |
| Status chips | Proposed, Confirmed |

A proposal is never called saved, recorded or final; tests check this.

**Notes:**
- Required, 1 to 1000 characters after trimming.
- A live counter shows the length.
- The hint says that runs of 7 or more digits are masked when saved.
- Older decisions without notes say so instead of showing a blank.

## Pages

| Route | Page | Roles | Endpoints |
|---|---|---|---|
| `/` | Overview: summary cards, flag source donut, risk band bars, needs attention | all | `/api/threat-intelligence/summary`, `/api/detection-runs/latest`, `/api/agent-scores?limit=50` |
| `/flagged` | Flagged agents (model, rule or both) | fraud_analyst, compliance_officer | `/api/all-agents`, `/api/review-decisions` |
| `/all-agents` | All agents, with a "Not flagged" state | fraud_analyst, compliance_officer | `/api/all-agents`, `/api/review-decisions` |
| `/agents/:agentId` | Agent detail, evidence, decision timeline, propose panel (fraud_analyst) | fraud_analyst, compliance_officer | `/api/agents/<id>`, `/api/analytics`, `/api/review-decisions`, `POST /api/review-decisions` |
| `/review/confirm` | Confirm queue | compliance_officer | `/api/review-decisions`, `POST /api/review-decisions/<id>/confirm` |
| `/history` | Review history | fraud_analyst, compliance_officer | `/api/review-decisions` |
| `/analytics` | Analytics: daily activations, score distribution, region rates, averages | all | `/api/analytics`, `/api/threat-intelligence/timeline`, `/api/threat-intelligence/by-region` |
| `/threat-intelligence` | Threat intelligence: summary, flag sources, drivers, timeline, regional rates, top risk agents, connected agents | all | `/api/threat-intelligence/summary`, `/timeline`, `/by-region`, `/customer-sharing`, `/api/agent-scores?limit=10` |
| `/audit-log` | Audit log with server-side filters and paging, details drawer | admin | `/api/audit-log` |
| `/reports` | Report downloads | admin | `/api/reports/flagged-agents.csv`, `/api/reports/audit-log.csv`, `/api/reports/detection-summary.pdf` |
| `/accounts` | Accounts: list, change role, deactivate, reactivate | admin | `/api/admin/accounts`, `PATCH .../role`, `POST .../deactivate`, `POST .../reactivate` |
| every signed-in page | Footer: model version and last detection run | all | `/api/detection-runs/latest` |
| `/403`, any other address | Access denied, Page not found | all | none |

**Notes on what is shown:**
- Agent ids are system codes, not personal data, so they are shown in full.
- Phone and national ID numbers are masked by the server (last 3 digits). Agent detail shortens the name to initials.
- Internal ids (flag, decision and run ids) are never shown.
- Proposer and confirmer are shown as the account ids the API returns. Usernames are not available to these roles.
- **Agent ids for admins:** they cannot open agent detail, so they see agent ids as plain text everywhere: Overview, Threat intelligence and the Audit log (`AgentId` component).
- **Audit log is admin only** in the app. The API also lets compliance officers read it, but the menu and route allow admins only.
- **Audit log filters:** the API offers no action or outcome filter, so the page filters by category, actor, agent id and date range. The Result column (Completed, Refused, Failed) is derived from the action for display only.
- **Accounts:** creating accounts and resetting passwords have no API, so the Accounts page says they are done on the server (`python -m src.manage_accounts reset-password`).
- Rule-only agents have no model flag, so they cannot be reviewed. Their evidence is read-only, with a note saying why.

## Branding

Only the SalesMesh name and its own mark (`public/favicon.svg`) appear. No third-party product name, logo or branding is used in the interface or its assets.
