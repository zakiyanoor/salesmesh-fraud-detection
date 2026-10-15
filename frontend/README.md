# SalesMesh fraud detection: web dashboard

The browser client for the SalesMesh fraud detection API (`backend/`).
- **Fraud analysts** review flagged agents and propose decisions.
- **Compliance officers** confirm them.
- **Admins** read the audit log, download reports and manage accounts.

The server enforces every permission; the client only hides what a role cannot use.

## Run

Start the backend first: `python -m src.api` from `backend/`, on port 5000. Then:

```
npm install
npm run dev        # http://localhost:5173; /api is proxied to the backend on 127.0.0.1:5000
```

For a production-like check: `npm run build`, then `npm run preview`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE` | `/api` | API base URL. The default goes through the development proxy. Every request, including file downloads, goes to this base with the session cookie, and to nothing else. See `.env.example`. |

The backend accepts browser requests from `http://localhost:5173` only, with credentials.

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Development server with the `/api` proxy |
| `npm run build` | Production build into `dist/` (every page is its own lazily loaded chunk) |
| `npm run preview` | Serves the build locally |
| `npm run lint` | Lint the source |
| `npm test` | All unit, component, accessibility (axe) and security tests |
| `npx vitest run src/pages/AuditLog.test.jsx` | One test file |
| `npm run screenshots` | After `npm run build`: screenshots of every page for each role at 360, 768 and 1280 px into `docs/screenshots/`, with a responsive report. Uses the installed Chrome (`CHROME_PATH` to change it) and fictional data; no backend needed |

## Roles and routes

The menu shows only what the signed-in role can use, and every route is guarded the same way (`src/auth/roles.js`). Any other role gets `/403`, and an unknown address gets "Page not found".

| Route | Page | Fraud analyst | Compliance officer | Admin |
|---|---|---|---|---|
| `/` | Overview | yes | yes | yes |
| `/flagged` | Flagged agents | yes | yes | |
| `/all-agents` | All agents | yes | yes | |
| `/agents/:agentId` | Agent detail (fraud analysts propose decisions here) | yes | yes | |
| `/threat-intelligence` | Threat intelligence | yes | yes | yes |
| `/analytics` | Analytics | yes | yes | yes |
| `/history` | Review history | yes | yes | |
| `/review/confirm` | Confirm queue | | yes | |
| `/audit-log` | Audit log | | | yes |
| `/reports` | Reports (CSV and PDF downloads) | | | yes |
| `/accounts` | Accounts | | | yes |

- **Session:** restored on reload with `GET /api/me`. Only the username and role are kept, in memory.
- **Browser storage:** only the colour mode preference (`salesmesh.colorMode`) is stored.
- **Errors:**
  - A 401 from any request goes back to the sign-in page with the reason (for example "Account is deactivated"), without retrying.
  - A 403 shows Access denied.
  - Other errors show a message with "Try again".
- **Sign out** clears the client state even if the server cannot be reached.

## Fonts and assets

IBM Plex Sans, IBM Plex Mono and Space Grotesk are bundled from npm packages, so the app makes no requests to third-party servers.

## Reference

- `docs/API.md`: every endpoint, role and payload.
- `docs/FRONTEND.md`: the style guide, the responsive and accessibility rules, the screenshots index and the known limitations. Every page follows it.
