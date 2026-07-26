"""FastAPI + Ariadne ASGI app with token auth middleware.

- POST /graphql : the Linear-compatible endpoint clinear talks to.
- Auth: raw token in Authorization header (with or without 'Bearer').
  Unknown/revoked token → HTTP 401 + {errors:[{message}]}.
- Never emits 429. GraphQL errors → HTTP 200 + {errors:[...], data:null}.
- Optional OFFLINE mode: if CLINEAR_SERVER_OPEN=1, any token maps to the only
  seeded identity in an unambiguous SQLite database.
"""
from __future__ import annotations

import os

from ariadne import graphql
from sqlalchemy import text
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from clinear_server.db import (
    make_engine,
    resolve_database_target,
    resolve_token_identity,
    schema_is_current,
)
from clinear_server.resolvers import build_schema
from clinear_server.store import Store
from clinear_server.writer import Writer

_schema = build_schema()


def _first_identity(engine):
    """Offline convenience for an unambiguous isolated SQLite database."""
    if engine.dialect.name != "sqlite":
        return None, None
    try:
        return resolve_token_identity(engine)
    except ValueError:
        return None, None


def create_app(
    db_path: str | None = None,
    *,
    database_url: str | None = None,
    tenant: str = "default",
    open_mode: bool | None = None,
) -> Starlette:
    target = resolve_database_target(
        database_url=database_url, db_path=db_path, tenant=tenant
    )
    engine = make_engine(target)
    store = Store(engine)
    writer = Writer(engine)
    if open_mode is None:
        open_mode = os.environ.get("CLINEAR_SERVER_OPEN", "0") == "1"

    def _auth(request: Request):
        raw = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
        token = raw[7:].strip() if raw.lower().startswith("bearer ") else raw.strip()
        if token:
            key = store.resolve_token(token)
            if key:
                return key["user_id"], key["organization_id"]
        if open_mode:
            uid, org = _first_identity(engine)
            if uid:
                return uid, org
        return None, None

    async def graphql_server(request: Request):
        uid, org = _auth(request)
        if not uid:
            return JSONResponse(
                {"errors": [{"message": "Authentication required",
                             "extensions": {"code": "AUTHENTICATION_ERROR"}}]},
                status_code=401,
            )
        data = await request.json()
        context = {"request": request, "store": store, "writer": writer,
                   "org_id": org, "user_id": uid}
        _success, result = await graphql(
            _schema, data, context_value=context,
            debug=os.environ.get("CLINEAR_SERVER_DEBUG") == "1",
        )
        return JSONResponse(result, status_code=200)

    async def health(request: Request):
        return JSONResponse({"status": "ok", "open_mode": open_mode})

    async def ready(request: Request):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1")).scalar_one()
            if not schema_is_current(engine):
                return JSONResponse(
                    {"status": "unavailable", "reason": "schema_outdated"},
                    status_code=503,
                )
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return JSONResponse({"status": "ready"})

    return Starlette(routes=[
        Route("/graphql", graphql_server, methods=["POST", "GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/ready", ready, methods=["GET"]),
    ])
