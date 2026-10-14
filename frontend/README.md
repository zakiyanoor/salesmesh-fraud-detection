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
| `npm run lint` | ESLint |
| `npm test` | Unit and component tests (Vitest, jsdom) |

## Configuration

`VITE_API_BASE` sets the API base URL (default `/api`, which the development proxy forwards). The backend only accepts browser requests from `http://localhost:5173`, with credentials.

## Fonts and assets

IBM Plex Sans, IBM Plex Mono and Space Grotesk are bundled from npm packages, so the app makes no requests to third-party servers.

## Reference

- `docs/API.md`: every endpoint, role and payload.
- `docs/FRONTEND.md`: the style guide (tokens, fonts, cards, tables, chips, sidebar, charts). Every page follows it.
