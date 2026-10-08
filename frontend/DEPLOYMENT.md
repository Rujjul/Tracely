# Frontend-only Vercel deployment

Deploy this `frontend` directory, not the repository root. Use Vercel's free Hobby plan for personal/non-commercial use. No backend, database, local environment files, or credentials are uploaded.

`vercel.json` builds Vite with `VITE_API_BASE_URL=/` only on Vercel. This prevents deployed browsers from contacting localhost or port 8000. API paths return an explicit unavailable response until a backend is deployed. The landing page and its labeled sample preview work; authentication and live data are unavailable. Existing application logic and local development settings are unchanged.

From this directory:

```powershell
npx vercel login
npx vercel --prod
```

Use `frontend` as the Root Directory if importing the GitHub repository through Vercel instead. Do not add backend secrets or a DATABASE_URL to this project.

Later, replace the `/api/(.*)` unavailable route with a rewrite to the hosted API, preserving the `/api/` path. Configure the backend's FRONTEND_URL, CORS_ORIGINS, secure cookies, and Google callback for the public HTTPS origin. Remove the unavailable JSON asset when it is no longer needed. This future backend integration is not part of the frontend-only deployment.

## Published deployment

Published on 2026-10-08: https://tracely-nu.vercel.app (Vercel project `rujj/tracely`). Frontend production build and unauthenticated public HTTP checks passed. GET/POST API calls return the explicit 503 preview response. Backend files and services were not changed.

Deployment used the CLI. GitHub auto-deploy was not connected because Vercel could not access the repository; future source updates need another CLI deployment until that integration is configured.
