"""SQLAlchemy Core storage, engine configuration, migration, and seeding."""
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
    func,
    inspect,
    select,
)
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError

metadata = MetaData()
CURRENT_SCHEMA_REVISION = 4


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
    Column("url_key", String, nullable=False, unique=True),
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

schema_revision = Table(
    "schema_revision", metadata,
    Column("revision", Integer, primary_key=True),
    Column("applied_at", String, nullable=False),
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

attachment = Table(
    "attachment", metadata,
    Column("id", String, primary_key=True),
    Column("organization_id", String, ForeignKey("organization.id"), index=True),
    Column("issue_id", String, ForeignKey("issue.id"), index=True),
    Column("creator_id", String, ForeignKey("user.id")),
    Column("url", String, nullable=False),
    Column("title", String, nullable=False),
    Column("subtitle", String),
    Column("created_at", String),
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

project_team = Table(
    "project_team", metadata,
    Column("project_id", String, ForeignKey("project.id"), primary_key=True),
    Column("team_id", String, ForeignKey("team.id"), primary_key=True),
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


def resolve_database_target(
    *,
    database_url: str | None = None,
    db_path: str | Path | None = None,
    tenant: str = "default",
) -> str:
    """Resolve explicit URL, environment URL, then the SQLite path fallback."""
    if database_url:
        return database_url
    if env_url := os.environ.get("CLINEAR_DATABASE_URL"):
        return env_url
    return str(db_path if db_path is not None else db_path_for(tenant))


def _as_sqlalchemy_url(target: str | Path) -> str:
    value = os.fspath(target)
    if value.startswith("postgres://"):
        return f"postgresql+psycopg://{value.removeprefix('postgres://')}"
    if value.startswith("postgresql://"):
        return f"postgresql+psycopg://{value.removeprefix('postgresql://')}"
    if "://" in value or value.startswith("sqlite:"):
        return value
    return f"sqlite:///{value}"


def display_database_target(target: str | Path) -> str:
    """Return a target safe for logs, hiding URL passwords."""
    value = os.fspath(target)
    if "://" not in value and not value.startswith("sqlite:"):
        return value
    return make_url(value).render_as_string(hide_password=True)


def make_engine(target: str | Path) -> Engine:
    url = _as_sqlalchemy_url(target)
    backend = make_url(url).get_backend_name()
    kwargs = {"future": True}
    if backend == "postgresql":
        kwargs["pool_pre_ping"] = True
    eng = create_engine(url, **kwargs)

    if backend == "sqlite":
        @event.listens_for(eng, "connect")
        def _set_pragma(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return eng


def _apply_token_hash_uniqueness(conn) -> None:
    duplicate = conn.execute(
        select(api_key.c.token_hash, func.count())
        .group_by(api_key.c.token_hash)
        .having(func.count() > 1)
        .limit(1)
    ).first()
    if duplicate:
        raise RuntimeError(
            "Cannot apply schema revision 2: duplicate API token hashes exist. "
            "Revoke duplicate keys before migrating."
        )
    indexes = inspect(conn).get_indexes(api_key.name)
    if not any(index["name"] == "uq_api_key_token_hash" for index in indexes):
        conn.exec_driver_sql(
            "CREATE UNIQUE INDEX uq_api_key_token_hash ON api_key (token_hash)"
        )


_MIGRATIONS = {
    1: lambda _conn: None,
    2: _apply_token_hash_uniqueness,
    3: lambda conn: project_team.create(conn, checkfirst=True),
    4: lambda conn: attachment.create(conn, checkfirst=True),
}


def applied_schema_revision(engine: Engine) -> int:
    """Return the latest recorded revision, or zero for an unmigrated database."""
    if not inspect(engine).has_table(schema_revision.name):
        return 0
    with engine.connect() as conn:
        revisions = list(
            conn.execute(
                select(schema_revision.c.revision).order_by(schema_revision.c.revision)
            ).scalars()
        )
    if revisions != list(range(1, len(revisions) + 1)):
        raise RuntimeError("Schema revision ledger is not a contiguous prefix.")
    return revisions[-1] if revisions else 0


def schema_is_current(engine: Engine) -> bool:
    return applied_schema_revision(engine) == CURRENT_SCHEMA_REVISION


def migrate(engine: Engine) -> None:
    """Create a fresh schema and apply every outstanding ordered revision."""
    current = applied_schema_revision(engine)
    if current == 0:
        metadata.create_all(engine)
    if current > CURRENT_SCHEMA_REVISION:
        raise RuntimeError(
            f"Database revision {current} is newer than this server supports "
            f"({CURRENT_SCHEMA_REVISION})."
        )
    for revision in range(current + 1, CURRENT_SCHEMA_REVISION + 1):
        with engine.begin() as conn:
            _MIGRATIONS[revision](conn)
            conn.execute(
                schema_revision.insert().values(revision=revision, applied_at=now_iso())
            )


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


def app_url() -> str:
    """Browser-facing application base URL for generated entity links."""
    return os.environ.get("CLINEAR_APP_URL", "http://localhost:8787").rstrip("/")


def entity_url(org_url_key: str, kind: str, entity_key: str) -> str:
    return f"{app_url()}/{org_url_key}/{kind}/{entity_key}"


def _default_org_url_key(org_name: str) -> str:
    key = "-".join(org_name.lower().split())
    if not key:
        raise ValueError("Organization name must produce a non-empty URL key.")
    return key


def seed_tenant(engine: Engine, *, org_name: str = "Local",
                org_url_key: str | None = None, team_key: str = "ENG",
                team_name: str = "Engineering", user_name: str = "Local User",
                user_email: str = "you@local", token: str | None = None,
                demo_issues: bool = True) -> dict:
    """Create one org, one admin user, one team (seeded states), an API token.
    Idempotent-ish: if the org already exists, returns existing token info is NOT
    possible (hash is one-way), so this is intended for fresh DBs.
    """
    token = token or gen_token()
    org_url_key = org_url_key or _default_org_url_key(org_name)
    ts = now_iso()
    try:
        with engine.begin() as conn:
            existing = conn.execute(
                select(organization.c.id).where(organization.c.url_key == org_url_key)
            ).first()
            if existing:
                raise ValueError(
                    f"Organization URL key '{org_url_key}' already exists; "
                    "choose a unique --org-key."
                )
            org_id = new_id()
            conn.execute(organization.insert().values(
                id=org_id, name=org_name, url_key=org_url_key,
                created_at=ts, updated_at=ts,
            ))
            uid = new_id()
            conn.execute(user.insert().values(
                id=uid, organization_id=org_id, name=user_name, display_name=user_name,
                email=user_email, active=True, admin=True,
                url=entity_url(org_url_key, "profiles", uid),
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
            conn.execute(
                team.update().where(team.c.id == tid).values(default_state_id=default_state_id)
            )

            if demo_issues:
                _seed_demo_issues(
                    conn, org_id, tid, team_key.upper(), uid, default_state_id, org_url_key
                )
    except IntegrityError as exc:
        if "token_hash" in str(exc).lower() or "uq_api_key_token_hash" in str(exc):
            raise ValueError("API token already exists; choose a different token.") from exc
        raise ValueError(
            f"Organization URL key '{org_url_key}' already exists; choose a unique --org-key."
        ) from exc

    return {"token": token, "org_id": org_id, "user_id": uid, "team_id": tid, "team_key": team_key.upper()}


def _seed_demo_issues(conn, org_id, team_id, team_key, uid, state_id, org_url_key):
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
            url=entity_url(org_url_key, "issue", ident),
            branch_name=f"{uid[:8]}/{ident.lower()}-{title.lower().replace(' ', '-')[:20]}",
            created_at=ts, updated_at=ts,
        ))
    conn.execute(team.update().where(team.c.id == team_id).values(issue_counter=n))


def resolve_token_identity(
    engine: Engine,
    *,
    organization_ref: str | None = None,
    user_ref: str | None = None,
    email: str | None = None,
) -> tuple[str, str]:
    """Resolve the exact (user, organization) for a newly minted token."""
    if user_ref and email:
        raise ValueError("Choose either --user or --email, not both.")
    shared_database = engine.dialect.name != "sqlite"
    if shared_database and not organization_ref:
        raise ValueError("--organization is required for a shared database.")
    if shared_database and not (user_ref or email):
        raise ValueError("--user or --email is required for a shared database.")

    with engine.connect() as conn:
        if organization_ref:
            org_rows = conn.execute(
                select(organization.c.id).where(
                    (organization.c.id == organization_ref)
                    | (organization.c.url_key == organization_ref)
                ).limit(2)
            ).all()
        else:
            org_rows = conn.execute(select(organization.c.id).limit(2)).all()
        if not org_rows:
            raise ValueError("No matching organization found; run 'clinear-serve seed' first.")
        if len(org_rows) != 1:
            raise ValueError("Multiple organizations found; specify --organization.")
        org_id = org_rows[0][0]

        query = select(user.c.id).where(user.c.organization_id == org_id)
        if user_ref:
            query = query.where(user.c.id == user_ref)
        elif email:
            query = query.where(user.c.email == email)
        user_rows = conn.execute(query.limit(2)).all()
        if not user_rows:
            raise ValueError("No matching user found in the selected organization.")
        if len(user_rows) != 1:
            raise ValueError("Multiple users found; specify --user or --email.")
        return user_rows[0][0], org_id
