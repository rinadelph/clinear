"""FastAPI + Ariadne ASGI app with token auth middleware.

- POST /graphql : the Linear-compatible endpoint the CLI talks to.
- Auth: raw token in Authorization header (with or without 'Bearer').
  Unknown/revoked token → HTTP 401 + {errors:[{message}]}.
- Never emits 429. GraphQL errors → HTTP 200 + {errors:[...], data:null}.
- Optional OFFLINE mode: if CLINIAR_SERVER_OPEN=1, any token maps to the only
  seeded identity in an unambiguous SQLite database.
"""
from __future__ import annotations

from ariadne import graphql
from sqlalchemy import text
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.responses import FileResponse
from starlette.routing import Route
from pathlib import Path
import os

from cliniar_server.db import (
    make_engine,
    resolve_database_target,
    resolve_token_identity,
    schema_is_current,
)
from cliniar_server.resolvers import build_schema
from cliniar_server.store import Store
from cliniar_server.writer import Writer

_schema = build_schema()
_WEB_ROOT = Path(os.environ.get("CLINIAR_WEB_ROOT", Path(__file__).resolve().parent.parent / "frontend" / "dist"))


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
        open_mode = os.environ.get("CLINIAR_SERVER_OPEN", "0") == "1"

    def _auth(request: Request):
        raw = request.headers.get("authorization", "") or request.headers.get("Authorization", "")
        token = raw[7:].strip() if raw.lower().startswith("bearer ") else raw.strip()
        session_token = request.cookies.get("hoja_session")
        if session_token:
            session = store.resolve_browser_session(session_token)
            if session:
                member = store.membership_for_profile(session["organization_id"], session["user_id"])
                return session["user_id"], session["organization_id"], (member or {}).get("identity_id"), True
        if token:
            key = store.resolve_token(token)
            if key:
                return key["user_id"], key["organization_id"], None, False
        if open_mode:
            uid, org = _first_identity(engine)
            if uid:
                return uid, org, None, False
        return None, None, None, False

    async def graphql_server(request: Request):
        uid, org, identity_id, is_browser_session = _auth(request)
        if not uid:
            return JSONResponse(
                {"errors": [{"message": "Authentication required",
                             "extensions": {"code": "AUTHENTICATION_ERROR"}}]},
                status_code=401,
            )
        data = await request.json()
        context = {"request": request, "store": store, "writer": writer,
                   "org_id": org, "user_id": uid, "identity_id": identity_id,
                   "browser_session": is_browser_session}
        _success, result = await graphql(
            _schema, data, context_value=context,
            debug=(
                os.environ.get("CLINIAR_SERVER_DEBUG", "0") == "1"
            ),
        )
        target = context.get("switch_target")
        if target:
            session_token, _details = store.create_session_for_membership(
                target.get("identity_id", identity_id), target["user_id"], target["organization_id"])
            if not session_token:
                return JSONResponse({"errors": [{"message": "Workspace access revoked"}]}, status_code=403)
            raw = request.cookies.get("hoja_session")
            if raw:
                store.revoke_browser_session(raw)
            response = JSONResponse(result, status_code=200)
            response.set_cookie("hoja_session", session_token, httponly=True,
                                secure=request.url.scheme == "https", samesite="lax",
                                max_age=14 * 24 * 60 * 60, path="/")
            return response
        return JSONResponse(result, status_code=200)

    async def auth_setup(request: Request):
        if request.method == "GET":
            return JSONResponse({"setup": True, "message": "Set a password using a valid local API token."})
        body = await request.json()
        try:
            ok = store.set_password(str(body.get("token", "")), str(body.get("password", "")))
        except ValueError as exc:
            return JSONResponse({"error": str(exc)}, status_code=400)
        if not ok:
            return JSONResponse({"error": "Invalid API token"}, status_code=401)
        return JSONResponse({"status": "password_set"}, status_code=201)

    async def auth_login(request: Request):
        body = await request.json()
        email = str(body.get("email", ""))
        password = str(body.get("password", ""))
        organization_ref = body.get("organizationId")
        api_key_value = str(body.get("apiKey", ""))
        if not api_key_value and not organization_ref:
            try:
                matches = store.matching_login_workspaces(email)
            except Exception as exc:
                # Old databases may not have the identity/membership schema yet.
                # Do not disguise unrelated database errors as invalid credentials.
                from sqlalchemy.exc import OperationalError

                if not isinstance(exc, OperationalError) or "organization_membership" not in str(exc):
                    raise
                return JSONResponse(
                    {"error": "Workspace sign-in is unavailable until the database schema is migrated."},
                    status_code=503,
                )
            if len(matches) > 1:
                return JSONResponse({"error": "Choose a workspace", "workspaces": matches}, status_code=409)
            if len(matches) == 1:
                organization_ref = matches[0]["organizationId"]
        if api_key_value:
            identity = store.resolve_token(api_key_value)
            if not identity:
                return JSONResponse({"error": "Invalid API key"}, status_code=401)
            # When this identity belongs to several workspaces, an API key is
            # scoped to only one of them. Honor an explicit workspace selection
            # rather than silently creating a session in the key's workspace.
            if organization_ref:
                member = store.membership_for_profile(
                    identity["organization_id"], identity["user_id"]
                )
                selected = store.switch_membership(
                    member.get("identity_id") if member else None, organization_ref
                )
                if selected:
                    session_token, _details = store.create_session_for_membership(
                        member["identity_id"], selected["user_id"],
                        selected["organization_id"]
                    )
                    result = (session_token, selected) if session_token else None
                else:
                    result = None
            else:
                result = store.create_browser_session_for_token(api_key_value)
        else:
            result = store.create_browser_session(email, password, organization_ref=organization_ref)
        if not result:
            return JSONResponse({"error": "Invalid credentials"}, status_code=401)
        session_token, identity = result
        response = JSONResponse({"status": "authenticated", "expiresAt": identity["expires_at"]})
        response.set_cookie("hoja_session", session_token, httponly=True, secure=request.url.scheme == "https",
                            samesite="lax", max_age=14 * 24 * 60 * 60, path="/")
        return response

    async def auth_workspaces(request: Request):
        body = await request.json()
        return JSONResponse({"workspaces": store.matching_login_workspaces(
            str(body.get("email", "")))})

    async def auth_logout(request: Request):
        session_token = request.cookies.get("hoja_session")
        if session_token:
            store.revoke_browser_session(session_token)
        response = JSONResponse({"status": "logged_out"})
        response.delete_cookie("hoja_session", path="/")
        return response

    async def auth_me(request: Request):
        uid, org, _identity_id, _browser_session = _auth(request)
        if not uid:
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        return JSONResponse({"userId": uid, "organizationId": org})

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

    async def web_index(request: Request):
        index = _WEB_ROOT / "index.html"
        if not index.is_file():
            return JSONResponse({"error": "Web UI has not been built"}, status_code=503)
        return FileResponse(index)

    async def web_asset(request: Request):
        name = request.path_params["name"]
        asset = (_WEB_ROOT / "assets" / name).resolve()
        if _WEB_ROOT not in asset.parents or not asset.is_file():
            return JSONResponse({"error": "Not found"}, status_code=404)
        return FileResponse(asset)

    async def web_fallback(request: Request):
        index = _WEB_ROOT / "index.html"
        if not index.is_file():
            return JSONResponse({"error": "Web UI has not been built"}, status_code=503)
        return FileResponse(index)

    app = Starlette(routes=[
        Route("/graphql", graphql_server, methods=["POST", "GET"]),
        Route("/auth/setup", auth_setup, methods=["GET", "POST"]),
        Route("/auth/login", auth_login, methods=["POST"]),
        Route("/auth/workspaces", auth_workspaces, methods=["POST"]),
        Route("/auth/logout", auth_logout, methods=["POST"]),
        Route("/auth/me", auth_me, methods=["GET"]),
        Route("/health", health, methods=["GET"]),
        Route("/ready", ready, methods=["GET"]),
        Route("/", web_index, methods=["GET"]),
        Route("/assets/{name:path}", web_asset, methods=["GET"]),
        Route("/{path:path}", web_fallback, methods=["GET"]),
    ])
    return app
