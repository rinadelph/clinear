"""SQLite storage layer — SQLAlchemy Core tables, engine, migration, seed.

One DB file per tenant (offline). Multi-tenant-ready: every table carries
organization_id so the same schema works for a shared Postgres DB later.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    select,
)
from sqlalchemy.engine import Engine

metadata = MetaData()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def gen_token() -> str:
    return "lin_api_" + secrets.token_urlsafe(30)


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
organization = Table(
    "organization", metadata,
    Column("id", String, primary_key=True),
    Column("name", String, nullable=False),
    Column("url_key", String),
    Column("created_at", String),
    Column("updated_at", String),
)

api_key = Table(
    "api_key", metadata,
    Column("id", String, primary_key=True),
    Column("token_hash", String, nullable=False, index=True),
    Column("label", String),
    Column("user_id", String, ForeignKey("user.id")),
    Column("organization_id", String, ForeignKey("organization.id")),
    Column("created_at", String),
    Column("revoked_at", String),
)

user = Table(
    "user", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("name", String),
    Column("display_name", String),
    Column("email", String),
    Column("active", Boolean, default=True),
    Column("admin", Boolean, default=False),
    Column("avatar_url", String),
    Column("url", String),
    Column("timezone", String),
    Column("status_emoji", String),
    Column("status_label", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
)

team = Table(
    "team", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("key", String, nullable=False),
    Column("name", String, nullable=False),
    Column("description", String),
    Column("color", String),
    Column("icon", String),
    Column("private", Boolean, default=False),
    Column("timezone", String),
    Column("issue_counter", Integer, default=0),
    Column("active_cycle_id", String),
    Column("default_state_id", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
    UniqueConstraint("organization_id", "key", name="uq_team_org_key"),
)

workflow_state = Table(
    "workflow_state", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("team_id", String, ForeignKey("team.id"), index=True),
    Column("name", String, nullable=False),
    Column("type", String, nullable=False),
    Column("color", String),
    Column("description", String),
    Column("position", Float, default=0),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
)

team_member = Table(
    "team_member", metadata,
    Column("team_id", String, ForeignKey("team.id"), primary_key=True),
    Column("user_id", String, ForeignKey("user.id"), primary_key=True),
)

issue = Table(
    "issue", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("team_id", String, ForeignKey("team.id"), index=True),
    Column("number", Integer),
    Column("identifier", String, index=True),
    Column("title", String, nullable=False),
    Column("description", Text),
    Column("priority", Integer, default=0),
    Column("priority_label", String),
    Column("estimate", Float),
    Column("state_id", String, ForeignKey("workflow_state.id"), index=True),
    Column("assignee_id", String, ForeignKey("user.id"), index=True),
    Column("creator_id", String, ForeignKey("user.id")),
    Column("project_id", String, index=True),
    Column("cycle_id", String),
    Column("parent_id", String),
    Column("url", String),
    Column("branch_name", String),
    Column("due_date", String),
    Column("started_at", String),
    Column("completed_at", String),
    Column("canceled_at", String),
    Column("snoozed_until_at", String),
    Column("created_at", String, index=True),
    Column("updated_at", String, index=True),
    Column("archived_at", String),
    UniqueConstraint("team_id", "number", name="uq_issue_team_number"),
)

issue_label = Table(
    "issue_label", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("team_id", String, ForeignKey("team.id")),
    Column("name", String, nullable=False),
    Column("color", String),
    Column("description", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
)

issue_label_link = Table(
    "issue_label_link", metadata,
    Column("issue_id", String, ForeignKey("issue.id"), primary_key=True),
    Column("label_id", String, ForeignKey("issue_label.id"), primary_key=True),
)

issue_subscriber = Table(
    "issue_subscriber", metadata,
    Column("issue_id", String, ForeignKey("issue.id"), primary_key=True),
    Column("user_id", String, ForeignKey("user.id"), primary_key=True),
)

comment = Table(
    "comment", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("issue_id", String, ForeignKey("issue.id"), index=True),
    Column("body", Text, nullable=False),
    Column("user_id", String, ForeignKey("user.id")),
    Column("url", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
)

project = Table(
    "project", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("name", String, nullable=False),
    Column("description", String),
    Column("slug_id", String),
    Column("icon", String),
    Column("color", String),
    Column("state", String, default="backlog"),
    Column("progress", Float, default=0),
    Column("lead_id", String, ForeignKey("user.id")),
    Column("creator_id", String, ForeignKey("user.id")),
    Column("start_date", String),
    Column("target_date", String),
    Column("url", String),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
)

project_member = Table(
    "project_member", metadata,
    Column("project_id", String, ForeignKey("project.id"), primary_key=True),
    Column("user_id", String, ForeignKey("user.id"), primary_key=True),
)

cycle = Table(
    "cycle", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("team_id", String, ForeignKey("team.id"), index=True),
    Column("number", Integer),
    Column("name", String),
    Column("description", String),
    Column("starts_at", String),
    Column("ends_at", String),
    Column("completed_at", String),
    Column("progress", Float, default=0),
    Column("created_at", String),
    Column("updated_at", String),
    Column("archived_at", String),
    UniqueConstraint("team_id", "number", name="uq_cycle_team_number"),
)


# --------------------------------------------------------------------------
# Seed workflow states (name, type, position)
# --------------------------------------------------------------------------
SEED_STATES = [
    ("Backlog", "backlog", 0, "#bec2c8"),
    ("Todo", "unstarted", 1, "#e2e2e2"),
    ("In Progress", "started", 2, "#f2c94c"),
    ("In Review", "started", 3, "#5e6ad2"),
    ("Done", "completed", 4, "#5e6ad2"),
    ("Canceled", "canceled", 5, "#95a2b3"),
]

PRIORITY_LABELS = {0: "No priority", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}


def default_db_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    d = Path(base) / "clinear"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path_for(tenant: str) -> Path:
    return default_db_dir() / f"{tenant}.db"


def make_engine(db_path: str | Path) -> Engine:
    eng = create_engine(f"sqlite:///{db_path}", future=True)

    @event.listens_for(eng, "connect")
    def _set_pragma(dbapi_conn, _):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return eng


def migrate(engine: Engine) -> None:
    metadata.create_all(engine)


def seed_states_for_team(conn, org_id: str, team_id: str) -> str:
    """Insert seed workflow states; return the default (first unstarted) state id."""
    default_state_id = None
    ts = now_iso()
    for name, stype, pos, color in SEED_STATES:
        sid = new_id()
        conn.execute(workflow_state.insert().values(
            id=sid, organization_id=org_id, team_id=team_id, name=name,
            type=stype, color=color, position=float(pos), created_at=ts, updated_at=ts,
        ))
        if stype == "unstarted" and default_state_id is None:
            default_state_id = sid
    return default_state_id


def seed_tenant(engine: Engine, *, org_name: str = "Local", team_key: str = "ENG",
                team_name: str = "Engineering", user_name: str = "Local User",
                user_email: str = "you@local", token: str | None = None,
                demo_issues: bool = True) -> dict:
    """Create one org, one admin user, one team (seeded states), an API token.
    Idempotent-ish: if the org already exists, returns existing token info is NOT
    possible (hash is one-way), so this is intended for fresh DBs.
    """
    token = token or gen_token()
    ts = now_iso()
    with engine.begin() as conn:
        org_id = new_id()
        conn.execute(organization.insert().values(
            id=org_id, name=org_name, url_key=org_name.lower().replace(" ", "-"),
            created_at=ts, updated_at=ts,
        ))
        uid = new_id()
        conn.execute(user.insert().values(
            id=uid, organization_id=org_id, name=user_name, display_name=user_name,
            email=user_email, active=True, admin=True,
            url=f"https://linear.app/{org_name.lower()}/profiles/{uid}",
            timezone="UTC", created_at=ts, updated_at=ts,
        ))
        conn.execute(api_key.insert().values(
            id=new_id(), token_hash=token_hash(token), label="seed",
            user_id=uid, organization_id=org_id, created_at=ts,
        ))
        tid = new_id()
        conn.execute(team.insert().values(
            id=tid, organization_id=org_id, key=team_key.upper(), name=team_name,
            description=f"{team_name} team", color="#5e6ad2", private=False,
            timezone="UTC", issue_counter=0, created_at=ts, updated_at=ts,
        ))
        conn.execute(team_member.insert().values(team_id=tid, user_id=uid))
        default_state_id = seed_states_for_team(conn, org_id, tid)
        conn.execute(team.update().where(team.c.id == tid).values(default_state_id=default_state_id))

        if demo_issues:
            _seed_demo_issues(conn, org_id, tid, team_key.upper(), uid, default_state_id, org_name)

    return {"token": token, "org_id": org_id, "user_id": uid, "team_id": tid, "team_key": team_key.upper()}


def _seed_demo_issues(conn, org_id, team_id, team_key, uid, state_id, org_name):
    ts = now_iso()
    # bump counter to 2, create ENG-1, ENG-2
    samples = [
        ("Set up local backend", "First seeded issue", 2),
        ("Wire clinear base_url", "Point CLI at local server", 1),
    ]
    n = 0
    for title, desc, prio in samples:
        n += 1
        iid = new_id()
        ident = f"{team_key}-{n}"
        conn.execute(issue.insert().values(
            id=iid, organization_id=org_id, team_id=team_id, number=n, identifier=ident,
            title=title, description=desc, priority=prio, priority_label=PRIORITY_LABELS[prio],
            state_id=state_id, creator_id=uid, assignee_id=uid,
            url=f"https://linear.app/{org_name.lower()}/issue/{ident}",
            branch_name=f"{uid[:8]}/{ident.lower()}-{title.lower().replace(' ', '-')[:20]}",
            created_at=ts, updated_at=ts,
        ))
    conn.execute(team.update().where(team.c.id == team_id).values(issue_counter=n))
