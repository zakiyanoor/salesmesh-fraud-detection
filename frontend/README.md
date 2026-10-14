# SalesMesh fraud detection: web dashboard

The browser client for the SalesMesh fraud detection API (`backend/`). Fraud analysts review flagged agents and propose decisions, compliance officers confirm them, and admins manage accounts and reports. The server enforces every permission; the client only hides what a role cannot use.

## Run

```
npm install
npm run dev        # http://localhost:5173, /api is proxied to the backend on 127.0.0.1:5000
```

Start the backend first (`python -m src.api` from `backend/`).

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Development server with the `/api` proxy |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serves the build locally |
| `npm run lint` | Lint the source |
| `npm test` | Unit and component tests |

## Configuration

`VITE_API_BASE` sets the API base URL (default `/api`, which the development proxy forwards; see `.env.example`). The backend only accepts browser requests from `http://localhost:5173`, with credentials.

## Pages and roles

The menu shows only what the signed-in role can use, and the routes are guarded the same way (`src/auth/roles.js`). The server still checks every request.

| Role | Menu |
|---|---|
| Fraud analyst | Overview, Flagged agents, All agents, Threat intelligence, Analytics, Review history |
| Compliance officer | The analyst menu, plus Confirm queue |
| Admin | Overview, Threat intelligence, Analytics, Audit log, Reports, Accounts |

- **Session:** restored on reload with `GET /api/me`. Only the username and role are kept, in memory; nothing about the session is written to browser storage.
- **Errors:** a 401 from any request signs the user out with the reason (for example "Account is deactivated"). A 403 shows Access denied, and other errors show a message with "Try again".

## Fonts and assets

IBM Plex Sans, IBM Plex Mono and Space Grotesk are bundled from npm packages, so the app makes no requests to third-party servers.

## Reference

- `docs/API.md`: every endpoint, role and payload.
- `docs/FRONTEND.md`: the style guide (tokens, fonts, cards, tables, chips, sidebar, charts). Every page follows it.
