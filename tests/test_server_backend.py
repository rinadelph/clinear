"""Focused, token-free tests for the self-hosted backend."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("starlette")

from sqlalchemy import inspect, select
from starlette.testclient import TestClient

from clinear_server.app import create_app
from clinear_server.db import (
    CURRENT_SCHEMA_REVISION,
    api_key,
    applied_schema_revision,
    cycle,
    display_database_target,
    issue,
    make_engine,
    metadata,
    migrate,
    new_id,
    now_iso,
    project,
    project_team,
    resolve_database_target,
    resolve_token_identity,
    schema_revision,
    seed_tenant,
    team,
    team_member,
    token_hash,
    workflow_state,
)
from clinear_server.store import Store
from clinear_server.writer import InvalidReferenceError, Writer


def _seed(
    engine,
    *,
    name: str,
    key: str,
    email: str,
    team_key: str = "ENG",
) -> dict:
    return seed_tenant(
        engine,
        org_name=name,
        org_url_key=key,
        team_key=team_key,
        user_name=f"{name} User",
        user_email=email,
        demo_issues=False,
    )


def test_database_target_precedence(monkeypatch, tmp_path) -> None:
    sqlite_path = tmp_path / "fallback.db"
    monkeypatch.setenv("CLINEAR_DATABASE_URL", "sqlite:///environment.db")

    assert resolve_database_target(
        database_url="sqlite:///explicit.db",
        db_path=sqlite_path,
        tenant="ignored",
    ) == "sqlite:///explicit.db"
    assert resolve_database_target(db_path=sqlite_path) == "sqlite:///environment.db"

    monkeypatch.delenv("CLINEAR_DATABASE_URL")
    assert resolve_database_target(db_path=sqlite_path) == str(sqlite_path)


@pytest.mark.parametrize("target", ["database.db", "sqlite:///:memory:"])
def test_make_engine_accepts_path_or_url(target) -> None:
    engine = make_engine(target)
    try:
        assert engine.dialect.name == "sqlite"
    finally:
        engine.dispose()


def test_make_engine_uses_psycopg3_and_redacts_passwords() -> None:
    pytest.importorskip("psycopg")
    engine = make_engine("postgresql://user:secret@db.example.test/clinear")
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
        assert engine.pool._pre_ping is True
    finally:
        engine.dispose()
    assert display_database_target(
        "postgresql://user:secret@db.example.test/clinear"
    ) == "postgresql://user:***@db.example.test/clinear"


def test_migrate_upgrades_a_recorded_prior_schema(tmp_path) -> None:
    engine = make_engine(tmp_path / "prior-schema.db")
    metadata.create_all(engine)
    with engine.begin() as conn:
        project_team.drop(conn)
        conn.execute(schema_revision.insert().values(revision=1, applied_at=now_iso()))

    migrate(engine)

    assert applied_schema_revision(engine) == CURRENT_SCHEMA_REVISION
    assert inspect(engine).has_table(project_team.name)
    indexes = inspect(engine).get_indexes(api_key.name)
    assert any(
        index["name"] == "uq_api_key_token_hash" and index["unique"]
        for index in indexes
    )


def test_migrate_rejects_unsafe_duplicate_legacy_tokens(tmp_path) -> None:
    engine = make_engine(tmp_path / "duplicate-legacy-token.db")
    metadata.create_all(engine)
    with engine.begin() as conn:
        project_team.drop(conn)
        conn.execute(schema_revision.insert().values(revision=1, applied_at=now_iso()))
    seeded = _seed(engine, name="Alpha", key="alpha", email="alpha@example.test")
    with engine.begin() as conn:
        existing_hash = conn.execute(select(api_key.c.token_hash)).scalar_one()
        conn.execute(
            api_key.insert().values(
                id=new_id(),
                token_hash=existing_hash,
                user_id=seeded["user_id"],
                organization_id=seeded["org_id"],
                created_at=now_iso(),
            )
        )

    with pytest.raises(RuntimeError, match="duplicate API token hashes"):
        migrate(engine)
    assert applied_schema_revision(engine) == 1


def test_migrate_rejects_a_gapped_revision_ledger(tmp_path) -> None:
    engine = make_engine(tmp_path / "gapped-revisions.db")
    metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            schema_revision.insert(),
            [
                {"revision": 1, "applied_at": now_iso()},
                {"revision": 3, "applied_at": now_iso()},
            ],
        )

    with pytest.raises(RuntimeError, match="not a contiguous prefix"):
        applied_schema_revision(engine)
    with pytest.raises(RuntimeError, match="not a contiguous prefix"):
        migrate(engine)


def test_shared_schema_isolates_organizations_and_rejects_duplicate_key(tmp_path) -> None:
    engine = make_engine(tmp_path / "shared.db")
    migrate(engine)
    alpha = _seed(engine, name="Alpha", key="alpha", email="alpha@example.test")
    beta = _seed(engine, name="Beta", key="beta", email="beta@example.test")
    writer = Writer(engine)
    store = Store(engine)

    alpha_issue = writer.issue_create(
        alpha["org_id"], alpha["user_id"], {"teamId": "ENG", "title": "Alpha only"}
    )
    beta_issue = writer.issue_create(
        beta["org_id"], beta["user_id"], {"teamId": "ENG", "title": "Beta only"}
    )

    assert alpha_issue is not None
    assert beta_issue is not None
    assert store.issue_by_id_or_identifier(alpha["org_id"], "ENG-1")["title"] == "Alpha only"
    assert store.issue_by_id_or_identifier(beta["org_id"], "ENG-1")["title"] == "Beta only"
    assert store.issue_by_id_or_identifier(alpha["org_id"], beta_issue) is None
    with pytest.raises(ValueError, match="already exists"):
        _seed(engine, name="Duplicate", key="alpha", email="other@example.test")


def test_api_tokens_are_globally_unique_and_identity_consistent(tmp_path) -> None:
    engine = make_engine(tmp_path / "token-constraints.db")
    migrate(engine)
    shared_token = "clinear_test_shared_token"
    alpha = seed_tenant(
        engine,
        org_name="Alpha",
        org_url_key="alpha",
        user_email="alpha@example.test",
        token=shared_token,
        demo_issues=False,
    )
    with pytest.raises(ValueError, match="API token already exists"):
        seed_tenant(
            engine,
            org_name="Beta",
            org_url_key="beta",
            user_email="beta@example.test",
            token=shared_token,
            demo_issues=False,
        )

    beta = _seed(engine, name="Beta", key="beta", email="beta@example.test")
    inconsistent_token = "clinear_test_inconsistent_identity"
    with engine.begin() as conn:
        conn.execute(
            api_key.insert().values(
                id=new_id(),
                token_hash=token_hash(inconsistent_token),
                user_id=beta["user_id"],
                organization_id=alpha["org_id"],
                created_at=now_iso(),
            )
        )
    assert Store(engine).resolve_token(inconsistent_token) is None


def test_issue_references_cannot_cross_organization_boundaries(tmp_path) -> None:
    engine = make_engine(tmp_path / "reference-isolation.db")
    migrate(engine)
    alpha = _seed(engine, name="Alpha", key="alpha", email="alpha@example.test")
    beta = _seed(engine, name="Beta", key="beta", email="beta@example.test")
    writer = Writer(engine)

    beta_project = writer.project_create(
        beta["org_id"], beta["user_id"], {"name": "Beta project"}
    )
    beta_parent = writer.issue_create(
        beta["org_id"], beta["user_id"], {"teamId": "ENG", "title": "Beta parent"}
    )
    beta_label = writer.label_create(beta["org_id"], {"name": "Beta label"})
    with engine.begin() as conn:
        beta_state = conn.execute(
            select(workflow_state.c.id).where(
                workflow_state.c.organization_id == beta["org_id"]
            )
        ).scalars().first()
        beta_cycle = new_id()
        conn.execute(
            cycle.insert().values(
                id=beta_cycle,
                organization_id=beta["org_id"],
                team_id=beta["team_id"],
                number=1,
                name="Beta cycle",
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )

    foreign_inputs = {
        "stateId": beta_state,
        "assigneeId": beta["user_id"],
        "projectId": beta_project,
        "cycleId": beta_cycle,
        "parentId": beta_parent,
        "labelIds": [beta_label],
    }
    for field, value in foreign_inputs.items():
        with pytest.raises(InvalidReferenceError) as exc_info:
            writer.issue_create(
                alpha["org_id"],
                alpha["user_id"],
                {"teamId": "ENG", "title": f"Reject {field}", field: value},
            )
        assert exc_info.value.extensions == {
            "code": "BAD_USER_INPUT",
            "field": field,
        }

    alpha_issue = writer.issue_create(
        alpha["org_id"], alpha["user_id"], {"teamId": "ENG", "title": "Alpha issue"}
    )
    for field, value in foreign_inputs.items():
        with pytest.raises(InvalidReferenceError):
            writer.issue_update(alpha["org_id"], alpha_issue, {field: value})

    with engine.connect() as conn:
        counter = conn.execute(
            select(team.c.issue_counter).where(team.c.id == alpha["team_id"])
        ).scalar_one()
        title = conn.execute(
            select(issue.c.title).where(issue.c.id == alpha_issue)
        ).scalar_one()
    assert counter == 1
    assert title == "Alpha issue"


def test_project_and_label_references_are_organization_scoped(tmp_path) -> None:
    engine = make_engine(tmp_path / "project-reference-isolation.db")
    migrate(engine)
    alpha = _seed(engine, name="Alpha", key="alpha", email="alpha@example.test")
    beta = _seed(engine, name="Beta", key="beta", email="beta@example.test")
    writer = Writer(engine)
    second_team_id = new_id()
    with engine.begin() as conn:
        conn.execute(
            team.insert().values(
                id=second_team_id,
                organization_id=alpha["org_id"],
                key="TWO",
                name="Second team",
                issue_counter=0,
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
        conn.execute(
            team_member.insert().values(
                team_id=second_team_id,
                user_id=alpha["user_id"],
            )
        )

    with pytest.raises(InvalidReferenceError) as lead_error:
        writer.project_create(
            alpha["org_id"],
            alpha["user_id"],
            {"name": "Invalid lead", "leadId": beta["user_id"]},
        )
    assert lead_error.value.extensions["field"] == "leadId"

    with pytest.raises(InvalidReferenceError) as teams_error:
        writer.project_create(
            alpha["org_id"],
            alpha["user_id"],
            {"name": "Invalid team", "teamIds": [beta["team_id"]]},
        )
    assert teams_error.value.extensions["field"] == "teamIds"

    restricted_project = writer.project_create(
        alpha["org_id"],
        alpha["user_id"],
        {"name": "Second team project", "teamIds": [second_team_id]},
    )
    with pytest.raises(InvalidReferenceError) as project_error:
        writer.issue_create(
            alpha["org_id"],
            alpha["user_id"],
            {
                "teamId": alpha["team_id"],
                "title": "Wrong project team",
                "projectId": restricted_project,
            },
        )
    assert project_error.value.extensions["field"] == "projectId"

    org_wide_project = writer.project_create(
        alpha["org_id"], alpha["user_id"], {"name": "Organization-wide project"}
    )
    org_wide_issue = writer.issue_create(
        alpha["org_id"],
        alpha["user_id"],
        {
            "teamId": alpha["team_id"],
            "title": "Organization-wide project issue",
            "projectId": org_wide_project,
        },
    )
    assert org_wide_issue
    with pytest.raises(InvalidReferenceError):
        writer.issue_update(
            alpha["org_id"],
            org_wide_issue,
            {"projectId": restricted_project},
        )

    with pytest.raises(InvalidReferenceError) as label_error:
        writer.label_create(
            alpha["org_id"], {"name": "Invalid label", "teamId": beta["team_id"]}
        )
    assert label_error.value.extensions["field"] == "teamId"


def test_token_identity_requires_unambiguous_selection_in_sqlite(tmp_path) -> None:
    engine = make_engine(tmp_path / "tokens.db")
    migrate(engine)
    alpha = _seed(engine, name="Alpha", key="alpha", email="alpha@example.test")

    assert resolve_token_identity(engine) == (alpha["user_id"], alpha["org_id"])

    beta = _seed(engine, name="Beta", key="beta", email="beta@example.test")
    with pytest.raises(ValueError, match="Multiple organizations"):
        resolve_token_identity(engine)
    assert resolve_token_identity(
        engine, organization_ref="beta", email="beta@example.test"
    ) == (beta["user_id"], beta["org_id"])
    with pytest.raises(ValueError, match="No matching user"):
        resolve_token_identity(
            engine, organization_ref="alpha", email="beta@example.test"
        )


def test_generated_urls_use_configured_application_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CLINEAR_APP_URL", "https://issues.example.test/root/")
    engine = make_engine(tmp_path / "urls.db")
    migrate(engine)
    seeded = _seed(engine, name="Example", key="example", email="user@example.test")
    writer = Writer(engine)

    issue_id = writer.issue_create(
        seeded["org_id"], seeded["user_id"], {"teamId": "ENG", "title": "Hosted issue"}
    )
    project_id = writer.project_create(
        seeded["org_id"], seeded["user_id"], {"name": "Hosted project"}
    )

    with engine.connect() as conn:
        issue_url = conn.execute(select(issue.c.url).where(issue.c.id == issue_id)).scalar_one()
        project_url = conn.execute(
            select(project.c.url).where(project.c.id == project_id)
        ).scalar_one()
    assert issue_url == "https://issues.example.test/root/example/issue/ENG-1"
    assert project_url == (
        "https://issues.example.test/root/example/project/hosted-project"
    )
    assert "linear.app" not in issue_url
    assert "linear.app" not in project_url


def test_concurrent_issue_identifiers_are_atomic_and_monotonic(tmp_path) -> None:
    engine = make_engine(tmp_path / "concurrent.db")
    migrate(engine)
    seeded = _seed(engine, name="Concurrent", key="concurrent", email="user@example.test")
    writer = Writer(engine)

    def create(number: int) -> str | None:
        return writer.issue_create(
            seeded["org_id"],
            seeded["user_id"],
            {"teamId": "ENG", "title": f"Issue {number}"},
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(create, range(20)))

    assert all(ids)
    with engine.connect() as conn:
        rows = conn.execute(
            select(issue.c.number, issue.c.identifier)
            .where(issue.c.organization_id == seeded["org_id"])
            .order_by(issue.c.number)
        ).all()
    assert rows == [(number, f"ENG-{number}") for number in range(1, 21)]


def test_health_and_readiness(tmp_path) -> None:
    db_path = tmp_path / "health.db"
    engine = make_engine(db_path)
    migrate(engine)
    engine.dispose()
    app = create_app(str(db_path), open_mode=False)

    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "open_mode": False}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}


def test_health_stays_available_when_schema_is_unmigrated(tmp_path) -> None:
    app = create_app(str(tmp_path / "unmigrated.db"), open_mode=False)

    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable", "reason": "schema_outdated"}
