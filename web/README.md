# Vmix Monitor Web (Vite + React + TypeScript)

## Development

```bash
pnpm install
pnpm dev
```

App runs at local Vite URL and reads backend from `.env`.

## Environment Variables

Create `.env` from `.env.example` and set:

```dotenv
VITE_BACKEND_BASE_URL=http://localhost:8000
VITE_REQUEST_TIMEOUT_MS=30000
# VITE_BACKEND_WS_URL=wss://tooldiscordvmix.onrender.com/ws
```

Notes:
- Variables must start with `VITE_`.
- For production, set the same values in Vercel Project Settings -> Environment Variables.

## Build

```bash
pnpm build
pnpm preview
```

## Deploy to Vercel

This project includes `vercel.json` with:
- Vite framework build settings
- output folder `dist`
- SPA routing rewrite to `index.html` so routes like `/login` and `/dashboard` work after refresh

Quick deploy steps:
1. Push repository to GitHub.
2. Import project in Vercel.
3. Root Directory: `web`
4. Build Command: `pnpm build`
5. Output Directory: `dist`
6. Add env vars:
   - `VITE_BACKEND_BASE_URL=http://localhost:8000`
   - `VITE_REQUEST_TIMEOUT_MS=30000`
   - optional `VITE_BACKEND_WS_URL=wss://tooldiscordvmix.onrender.com/ws`
7. Deploy.

If login request returns `401`, that means backend rejected credentials (not frontend deploy failure).
