"""`clinear-serve` entry point.

Subcommands:
  serve   Start the local GraphQL backend (FastAPI + Ariadne + SQLite).
  seed    Create/seed a tenant DB (org, user, team, states, token) and print the token.
  token   Mint a new API token for an existing tenant.
"""
from __future__ import annotations

import argparse
import sys

from clinear_server import __version__
from clinear_server.db import (
    api_key,
    db_path_for,
    gen_token,
    make_engine,
    migrate,
    new_id,
    now_iso,
    seed_tenant,
    token_hash,
    user,
)


def _cmd_serve(args):
    import uvicorn
    from clinear_server.app import create_app
    db_path = args.db or str(db_path_for(args.tenant))
    app = create_app(db_path, open_mode=args.open)
    print(f"clinear-serve v{__version__}")
    print(f"  tenant : {args.tenant}")
    print(f"  db     : {db_path}")
    print(f"  url    : http://{args.host}:{args.port}/graphql")
    print(f"  open   : {args.open}")
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


def _cmd_seed(args):
    db_path = args.db or str(db_path_for(args.tenant))
    engine = make_engine(db_path)
    migrate(engine)
    info = seed_tenant(
        engine, org_name=args.org, team_key=args.team_key, team_name=args.team_name,
        user_name=args.user, user_email=args.email,
        token=args.token, demo_issues=not args.no_demo,
    )
    print(f"Seeded tenant '{args.tenant}' at {db_path}")
    print(f"  org      : {args.org}")
    print(f"  team     : {info['team_key']}")
    print(f"  user     : {args.user} <{args.email}>")
    print(f"  TOKEN    : {info['token']}")
    print()
    print("Use it with clinear:")
    print(f"  export LINEAR_TOKEN='{info['token']}'")
    print(f"  clinear --token '{info['token']}' me   # (after wiring base_url)")


def _cmd_token(args):
    db_path = args.db or str(db_path_for(args.tenant))
    engine = make_engine(db_path)
    from sqlalchemy import select
    with engine.begin() as conn:
        row = conn.execute(select(user.c.id, user.c.organization_id)
                           .order_by(user.c.created_at).limit(1)).first()
        if not row:
            print("No user found — run 'clinear-serve seed' first.", file=sys.stderr)
            sys.exit(1)
        tok = args.token or gen_token()
        conn.execute(api_key.insert().values(
            id=new_id(), token_hash=token_hash(tok), label=args.label,
            user_id=row[0], organization_id=row[1], created_at=now_iso()))
    print(tok)


def main(argv=None):
    p = argparse.ArgumentParser(prog="clinear-serve", description="clinear local backend")
    p.add_argument("--version", action="version", version=f"clinear-serve {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="start the GraphQL server")
    s.add_argument("--tenant", default="default")
    s.add_argument("--db", default=None, help="explicit DB path (overrides tenant)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--open", action="store_true", help="offline open mode: any token → first identity")
    s.add_argument("--log-level", default="warning")
    s.set_defaults(func=_cmd_serve)

    sd = sub.add_parser("seed", help="seed a tenant DB")
    sd.add_argument("--tenant", default="default")
    sd.add_argument("--db", default=None)
    sd.add_argument("--org", default="Local")
    sd.add_argument("--team-key", default="ENG")
    sd.add_argument("--team-name", default="Engineering")
    sd.add_argument("--user", default="Local User")
    sd.add_argument("--email", default="you@local")
    sd.add_argument("--token", default=None, help="use a specific token instead of random")
    sd.add_argument("--no-demo", action="store_true", help="don't create demo issues")
    sd.set_defaults(func=_cmd_seed)

    t = sub.add_parser("token", help="mint a new token for a tenant")
    t.add_argument("--tenant", default="default")
    t.add_argument("--db", default=None)
    t.add_argument("--token", default=None)
    t.add_argument("--label", default="cli")
    t.set_defaults(func=_cmd_token)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
