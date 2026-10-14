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

## Chips

- `size="small"` and `variant="outlined"`.
- Status: `error` for flagged or confirmed fraud, `success` for clear or legitimate.
- Risk: `RiskBadge` only (label and icon, coloured by `palette.risk`).

## Sidebar

- 240px wide drawer on `background.paper`, with a 1px `divider` right border and 24px padding.
- "SalesMesh" in `h6` above "Fraud Detection" in `caption`, `text.secondary`, with 32px below.
- Menu items: outlined icons with 36px minimum icon width, label in `body2`, radius 4px, 4px apart. The active item has an `action.selected` background with `primary.dark` text and icon.
- Footer: a divider, "Signed in as" with the username and role in `caption`, the dark mode toggle and the "Sign out" text button.
- **From `md` up** the drawer is permanent. **Below `md`** it is a temporary drawer opened by a menu button in a top bar.

## Charts

- **Donut cards:** 140px chart, inner radius 44, outer radius 64, 2px padding between slices (none for a single slice), no stroke. The total sits in the centre in `h5` mono. A legend beside the chart lists a 10px dot, the name, the count in mono and the share in `caption` mono. With no data the ring is a single `divider` slice.
- **Bar charts:** in a `ResponsiveContainer` 220px high, dashed grid in `chart.grid`, axes in `chart.axis` at 12px, integer y ticks, bar radius `[3, 3, 0, 0]`.
- **Tooltips:** `background.paper` background, 1px `divider` border, `text.primary` text.

## States

- **Loading:** a skeleton shaped like the content (title, cards, table rows), not a spinner.
- **Empty:** a short sentence in `text.secondary` saying what is missing.
- **Error:** what went wrong and a "Try again" button.
- **Access denied:** shown on a 403 and on `/403`.

## Layout and touch

- Content padding: 40px from `md` up, 16px below.
- Rows of filters and cards wrap; nothing scrolls sideways at 360px.
- On touch screens (`pointer: coarse`) buttons, icon buttons, menu items and list items are at least 44px high. With a mouse they keep their compact size.

## Accessibility

- Text meets WCAG AA (4.5:1) on `background.default` and `background.paper` in both modes. Graphics and chart series meet 3:1, or carry their meaning in a text label or legend (the amber region colour does this).
- `frontend/src/theme.test.js` checks the text contrast ratios.
- Colour never carries meaning alone: risk, status and decision chips always have a text label.

## Branding

Only the SalesMesh name and its own mark (`public/favicon.svg`) appear. No third-party product name, logo or branding is used in the interface or its assets.
