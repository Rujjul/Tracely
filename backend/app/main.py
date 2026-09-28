"""Tracely API and Phase 2 account authentication."""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import psycopg
from app.auth import router

app = FastAPI(title="Tracely API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exception):
    # Do not echo submitted passwords or other credential input in validation errors.
    return JSONResponse(status_code=422, content={'detail': [
        {'loc': error['loc'], 'msg': error['msg'], 'type': error['type']}
        for error in exception.errors()
    ]})


@app.middleware('http')
async def private_auth_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/v1/auth'):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@app.exception_handler(psycopg.Error)
async def database_error(request, exception):
    return JSONResponse(status_code=503, content={'detail': 'Database unavailable. Check setup and migrations.'})


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
