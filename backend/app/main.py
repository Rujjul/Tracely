"""Local API foundation. Persistence and authentication come in later phases."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Tracely API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    storage = "not_configured"
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        import psycopg

        try:
            with psycopg.connect(database_url, connect_timeout=3) as connection:
                connection.execute("SELECT 1").fetchone()
            storage = "connected"
        except psycopg.Error:
            raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok", "service": "tracely-api", "version": "0.1.0", "storage": storage}
