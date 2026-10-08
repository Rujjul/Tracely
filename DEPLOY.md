Deploy the current Tracely application without changing or refactoring the existing working codebase.

Current stack:
- Frontend: React + TypeScript + Vite
- Backend: FastAPI
- Database: PostgreSQL
- Docker is already used in the project

Goal:
Make the current MVP deployable while preserving all existing functionality and architecture.

Strict rules:
1. Do NOT refactor existing frontend or backend logic.
2. Do NOT rename, move, or delete existing files unless absolutely required for deployment.
3. Do NOT modify database models, schemas, API contracts, authentication logic, project ownership, ingestion-key logic, or event-ingestion behavior.
4. Do NOT add new product features.
5. Do NOT replace existing dependencies or frameworks.
6. Do NOT change UI design or dashboard behavior.
7. Do NOT remove sample/mock functionality that is currently intentional.
8. Keep local development working exactly as it does now.
9. Make only the minimum deployment-related changes required.
10. Before changing an existing application file, verify that the change is necessary for deployment.

Deployment work may include only:
- production environment-variable configuration
- frontend API base URL configuration
- CORS configuration using environment variables
- production-safe backend startup command
- Docker/deployment configuration
- PostgreSQL connection configuration through DATABASE_URL
- health-check configuration
- build/start scripts if required
- .gitignore/.dockerignore updates
- deployment documentation
- platform configuration files if required

All secrets must come from environment variables. Never hard-code credentials, API keys, database URLs, or secret keys.

Use separate development and production configuration so local development is unaffected.

Expected production flow:

React frontend
    ↓ HTTPS
FastAPI backend
    ↓
PostgreSQL

Preserve the existing API routes and behavior.

After making changes:
1. Confirm the frontend still builds.
2. Confirm the backend starts successfully.
3. Confirm the health endpoint works.
4. Confirm authentication still works.
5. Confirm project creation still works.
6. Confirm ingestion-key creation still works.
7. Confirm events can still be ingested.
8. Confirm the dashboard can communicate with the backend.

Do not implement unfinished Tracely features such as detection, investigation, alerts, email delivery, retention systems, or advanced rate limiting during this task.

If deployment requires a potentially destructive architectural/code change, do not make it. Instead document what would be required.

Keep the patch small, reversible, and deployment-focused.