"""Focused, token-free tests for the self-hosted backend."""

from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("starlette")

from sqlalchemy import inspect, select
from starlette.testclient import TestClient

from cliniar_server.app import create_app
from cliniar_server.db import (
    CURRENT_SCHEMA_REVISION,
    api_key,
    applied_schema_revision,
    attachment,
    cycle,
    display_database_target,
    issue,
    global_identity,
    identity_credential,
    make_engine,
    metadata,
    migrate,
    new_id,
    now_iso,
    project,
    project_team,
    organization_membership,
    resolve_database_target,
    resolve_token_identity,
    schema_revision,
    seed_tenant,
    team,
    team_member,
    token_hash,
    workflow_state,
)
from cliniar_server.store import Store
from cliniar_server.writer import InvalidReferenceError, Writer


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
    monkeypatch.setenv("CLINIAR_DATABASE_URL", "sqlite:///environment.db")

    assert resolve_database_target(
        database_url="sqlite:///explicit.db",
        db_path=sqlite_path,
        tenant="ignored",
    ) == "sqlite:///explicit.db"
    assert resolve_database_target(db_path=sqlite_path) == "sqlite:///environment.db"

    monkeypatch.delenv("CLINIAR_DATABASE_URL")
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
        attachment.drop(conn)
        project_team.drop(conn)
        conn.execute(schema_revision.insert().values(revision=1, applied_at=now_iso()))

    migrate(engine)

    assert applied_schema_revision(engine) == CURRENT_SCHEMA_REVISION
    assert inspect(engine).has_table(attachment.name)
    assert inspect(engine).has_table(project_team.name)
    indexes = inspect(engine).get_indexes(api_key.name)
    assert any(
        index["name"] == "uq_api_key_token_hash" and index["unique"]
        for index in indexes
    )


def test_identity_membership_migration_preserves_duplicate_email_profiles(tmp_path) -> None:
    engine = make_engine(tmp_path / "identity-migration.db")
    migrate(engine)
    first = seed_tenant(engine, org_name="First", org_url_key="identity-first",
                        user_name="Same Person One", user_email="same@example.test", demo_issues=False)
    second = seed_tenant(engine, org_name="Second", org_url_key="identity-second",
                         user_name="Same Person Two", user_email="same@example.test", demo_issues=False)
    with engine.begin() as conn:
        organization_membership.drop(conn)
        global_identity.drop(conn)
        conn.execute(schema_revision.delete().where(schema_revision.c.revision >= 6))
    with engine.begin() as conn:
        # Simulate a revision-5 database retaining the old password hashes.
        from cliniar_server.db import password_credential
        for seeded in (first, second):
            conn.execute(password_credential.insert().values(
                user_id=seeded["user_id"], password_hash=f"legacy-hash-{seeded['user_id']}",
                created_at=now_iso(), updated_at=now_iso()))
    migrate(engine)
    with engine.connect() as conn:
        rows = conn.execute(select(organization_membership.c.identity_id,
                                   organization_membership.c.organization_id,
                                   organization_membership.c.profile_user_id)).all()
        credentials = conn.execute(select(identity_credential.c.password_hash)).scalars().all()
    assert applied_schema_revision(engine) == CURRENT_SCHEMA_REVISION
    mapped = {row.profile_user_id: (row.identity_id, row.organization_id) for row in rows}
    assert mapped[first["user_id"]][1] == first["org_id"]
    assert mapped[second["user_id"]][1] == second["org_id"]
    assert mapped[first["user_id"]][0] != mapped[second["user_id"]][0]
    assert sorted(credentials) == sorted([
        f"legacy-hash-{first['user_id']}", f"legacy-hash-{second['user_id']}"])


def test_migrate_rejects_unsafe_duplicate_legacy_tokens(tmp_path) -> None:
    engine = make_engine(tmp_path / "duplicate-legacy-token.db")
    metadata.create_all(engine)
    with engine.begin() as conn:
        attachment.drop(conn)
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
    assert writer.attachment_create(
        alpha["org_id"],
        alpha["user_id"],
        {
            "issueId": beta_parent,
            "url": "https://example.test/foreign",
            "title": "Foreign issue",
        },
    ) is None
    with pytest.raises(InvalidReferenceError) as unsafe_url:
        writer.attachment_create(
            alpha["org_id"],
            alpha["user_id"],
            {
                "issueId": alpha_issue,
                "url": "javascript:alert(1)",
                "title": "Unsafe URL",
            },
        )
    assert unsafe_url.value.extensions["field"] == "url"


def test_cycle_and_boolean_issue_filters_do_not_broaden_results(tmp_path) -> None:
    engine = make_engine(tmp_path / "cycle-filters.db")
    migrate(engine)
    seeded = _seed(engine, name="Filters", key="filters", email="filters@example.test")
    writer = Writer(engine)
    with engine.begin() as conn:
        current_cycle = new_id()
        next_cycle = new_id()
        for cycle_id, number, name in (
            (current_cycle, 1, "Current Cycle"),
            (next_cycle, 2, "Next Cycle"),
        ):
            conn.execute(
                cycle.insert().values(
                    id=cycle_id,
                    organization_id=seeded["org_id"],
                    team_id=seeded["team_id"],
                    number=number,
                    name=name,
                    created_at=now_iso(),
                    updated_at=now_iso(),
                )
            )
        conn.execute(
            team.update()
            .where(team.c.id == seeded["team_id"])
            .values(active_cycle_id=current_cycle)
        )
    writer.issue_create(
        seeded["org_id"],
        seeded["user_id"],
        {
            "teamId": seeded["team_id"],
            "title": "Current urgent",
            "cycleId": current_cycle,
            "priority": 1,
        },
    )
    writer.issue_create(
        seeded["org_id"],
        seeded["user_id"],
        {
            "teamId": seeded["team_id"],
            "title": "Next low",
            "cycleId": next_cycle,
            "priority": 4,
        },
    )
    store = Store(engine)

    current = store.issues(
        seeded["org_id"],
        seeded["user_id"],
        {"cycle": {"isActive": {"eq": True}}},
    )
    upcoming = store.issues(
        seeded["org_id"],
        seeded["user_id"],
        {"cycle": {"isNext": {"eq": True}}},
    )
    combined = store.issues(
        seeded["org_id"],
        seeded["user_id"],
        {
            "and": [
                {"title": {"contains": "Current"}},
                {"priority": {"eq": 1}},
            ]
        },
    )
    alternatives = store.issues(
        seeded["org_id"],
        seeded["user_id"],
        {
            "or": [
                {"title": {"eq": "Current urgent"}},
                {"title": {"eq": "Next low"}},
            ]
        },
    )

    assert [row["title"] for row in current] == ["Current urgent"]
    assert [row["title"] for row in upcoming] == ["Next low"]
    assert [row["title"] for row in combined] == ["Current urgent"]
    assert {row["title"] for row in alternatives} == {"Current urgent", "Next low"}


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
    monkeypatch.setenv("CLINIAR_APP_URL", "https://issues.example.test/root/")
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


def test_team_create_graphql_admin_success_and_duplicate_key(tmp_path) -> None:
    db_path = tmp_path / "team-create.db"
    engine = make_engine(db_path)
    migrate(engine)
    seeded = seed_tenant(engine, org_name="Create Team", org_url_key="create-team",
                         user_email="create@example.test", token="create-team-token",
                         demo_issues=False)
    app = create_app(str(db_path), open_mode=False)
    query = "mutation($input: TeamCreateInput!) { teamCreate(input: $input) { success team { id name key description states { nodes { name type } } } } }"
    with TestClient(app) as client:
        headers = {"Authorization": f"Bearer {seeded['token']}"}
        result = client.post("/graphql", headers=headers, json={
            "query": query,
            "variables": {"input": {"name": "Product Team", "key": "prd", "description": "Product"}},
        }).json()
        payload = result["data"]["teamCreate"]
        assert payload["success"] is True
        assert payload["team"]["name"] == "Product Team"
        assert payload["team"]["key"] == "PRD"
        assert payload["team"]["states"]["nodes"]

        duplicate = client.post("/graphql", headers=headers, json={
            "query": query,
            "variables": {"input": {"name": "Another team", "key": "prd"}},
        }).json()
        assert duplicate["errors"][0]["extensions"]["code"] == "BAD_USER_INPUT"


def test_health_stays_available_when_schema_is_unmigrated(tmp_path) -> None:
    app = create_app(str(tmp_path / "unmigrated.db"), open_mode=False)

    with TestClient(app) as client:
        health = client.get("/health")
        ready = client.get("/ready")

    assert health.status_code == 200
    assert ready.status_code == 503
    assert ready.json() == {"status": "unavailable", "reason": "schema_outdated"}


def test_cloverops_graphql_operation_contract(tmp_path) -> None:
    target = os.environ.get("CLINIAR_TEST_POSTGRES_URL") or (
        tmp_path / "cloverops-contract.db"
    )
    suffix = uuid.uuid4().hex[:12]
    contract_token = f"clinear_test_cloverops_contract_{suffix}"
    engine = make_engine(target)
    migrate(engine)
    seeded = seed_tenant(
        engine,
        org_name="Contract Organization",
        org_url_key=f"contract-{suffix}",
        team_key="ENG",
        user_name="Contract User",
        user_email="contract@example.test",
        token=contract_token,
        demo_issues=False,
    )
    writer = Writer(engine)
    project_id = writer.project_create(
        seeded["org_id"],
        seeded["user_id"],
        {"name": "Contract Project", "teamIds": [seeded["team_id"]]},
    )
    issue_id = writer.issue_create(
        seeded["org_id"],
        seeded["user_id"],
        {
            "teamId": seeded["team_id"],
            "title": "Contract issue",
            "projectId": project_id,
        },
    )
    with engine.begin() as conn:
        cycle_id = new_id()
        conn.execute(
            cycle.insert().values(
                id=cycle_id,
                organization_id=seeded["org_id"],
                team_id=seeded["team_id"],
                number=1,
                name="Contract Cycle",
                created_at=now_iso(),
                updated_at=now_iso(),
            )
        )
    engine.dispose()

    app = create_app(database_url=str(target), open_mode=False)
    headers = {"Authorization": contract_token}

    def execute(client, query: str, variables: dict | None = None) -> dict:
        response = client.post(
            "/graphql",
            headers=headers,
            json={"query": query, "variables": variables or {}},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "errors" not in payload, payload.get("errors")
        return payload["data"]

    with TestClient(app) as client:
        bootstrap = execute(
            client,
            """query Bootstrap($first: Int!) {
              t: teams { nodes { id name key description icon color } }
              p: projects(first: $first) { nodes {
                id name slugId description icon color state progress startDate targetDate
                lead { id name } teams { nodes { id name key } } health url
              } }
              s: workflowStates { nodes {
                id name type color description position team { id key }
              } }
            }""",
            {"first": 100},
        )
        assert bootstrap["t"]["nodes"][0]["key"] == "ENG"
        assert bootstrap["p"]["nodes"][0]["teams"]["nodes"][0]["key"] == "ENG"
        assert bootstrap["s"]["nodes"][0]["team"]["key"] == "ENG"

        cycles_data = execute(
            client,
            """query ListCycles($filter: CycleFilter) {
              cycles(filter: $filter) {
                nodes { id name number startsAt endsAt progress team { id key } }
              }
            }""",
            {"filter": {"team": {"id": {"eq": seeded["team_id"]}}}},
        )
        assert cycles_data["cycles"]["nodes"][0]["id"] == cycle_id
        assert cycles_data["cycles"]["nodes"][0]["team"]["key"] == "ENG"

        issues_data = execute(
            client,
            """query FindIssue($filter: IssueFilter!) {
              issues(filter: $filter) { nodes { id } }
            }""",
            {"filter": {"identifier": {"eq": "ENG-1"}}},
        )
        assert issues_data["issues"]["nodes"][0]["id"] == issue_id

        create_data = execute(
            client,
            """mutation CreateIssue($input: IssueCreateInput!) {
              issueCreate(input: $input) {
                success issue {
                  id identifier title state { name type color }
                  priority team { id key } url
                }
              }
            }""",
            {
                "input": {
                    "teamId": seeded["team_id"],
                    "title": "Created by CloverOps",
                    "projectId": project_id,
                    "priority": 2,
                }
            },
        )
        created_id = create_data["issueCreate"]["issue"]["id"]
        assert create_data["issueCreate"]["success"] is True

        states_data = execute(
            client,
            """query GetStartedStates {
              workflowStates(filter: { type: { eq: "started" } }) {
                nodes { id name }
              }
            }""",
        )
        started_id = states_data["workflowStates"]["nodes"][0]["id"]
        execute(
            client,
            """mutation MoveIssue($id: String!, $sid: String!) {
              issueUpdate(id: $id, input: { stateId: $sid }) { success }
            }""",
            {"id": created_id, "sid": started_id},
        )
        execute(
            client,
            """mutation Comment($iid: String!, $b: String!) {
              commentCreate(input: {issueId: $iid, body: $b}) { success }
            }""",
            {"iid": created_id, "b": "Contract comment"},
        )
        attachment_data = execute(
            client,
            """mutation Attach(
              $iid: String!, $url: String!, $t: String!, $st: String
            ) {
              attachmentCreate(input: {
                issueId: $iid, url: $url, title: $t, subtitle: $st
              }) { success }
            }""",
            {
                "iid": created_id,
                "url": "https://example.test/change/1",
                "t": "Contract attachment",
                "st": "Created by the contract test",
            },
        )
        assert attachment_data["attachmentCreate"]["success"] is True

    verification_engine = make_engine(target)
    with verification_engine.connect() as conn:
        assert conn.execute(
            select(attachment.c.id).where(attachment.c.issue_id == created_id)
        ).scalar_one()
    verification_engine.dispose()


def test_browser_password_session_setup_login_graphql_and_logout(tmp_path) -> None:
    from starlette.testclient import TestClient

    db_path = tmp_path / "browser-auth.db"
    engine = make_engine(db_path)
    migrate(engine)
    seeded = seed_tenant(engine, org_name="Auth Workspace", org_url_key="auth-test",
                         user_name="Browser User", user_email="browser@example.test",
                         demo_issues=False)
    client = TestClient(create_app(str(db_path), open_mode=False))
    weak = client.post("/auth/setup", json={"token": seeded["token"], "password": "short"})
    assert weak.status_code == 400
    setup = client.post("/auth/setup", json={"token": seeded["token"], "password": "correct horse battery"})
    assert setup.status_code == 201
    bad = client.post("/auth/login", json={"email": "browser@example.test", "password": "wrong password"})
    assert bad.status_code == 401
    login = client.post("/auth/login", json={"email": "browser@example.test", "password": "correct horse battery"})
    assert login.status_code == 200
    assert "hoja_session" in login.cookies
    assert "httponly" in login.headers.get("set-cookie", "").lower()
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["organizationId"] == seeded["org_id"]
    graph = client.post("/graphql", json={"query": "{ viewer { email } }"})
    assert graph.status_code == 200
    assert graph.json()["data"]["viewer"]["email"] == "browser@example.test"
    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert client.post("/graphql", json={"query": "{ viewer { id } }"}).status_code == 401


def test_browser_password_login_accepts_api_key_and_rejects_invalid_password(tmp_path) -> None:
    from starlette.testclient import TestClient

    db_path = tmp_path / "browser-api-key-login.db"
    engine = make_engine(db_path)
    migrate(engine)
    seeded = seed_tenant(engine, org_name="API Key Workspace", org_url_key="api-key-login",
                         user_name="API Key User", user_email="api-key-login@example.test",
                         demo_issues=False)
    client = TestClient(create_app(str(db_path), open_mode=False))
    assert client.post("/auth/setup", json={"token": seeded["token"],
        "password": "correct horse battery"}).status_code == 201

    login = client.post("/auth/login", json={"apiKey": seeded["token"]})
    assert login.status_code == 200
    assert "hoja_session" in login.cookies
    assert client.get("/auth/me").json()["organizationId"] == seeded["org_id"]

    client.post("/auth/logout")
    invalid = client.post("/auth/login", json={"apiKey": "invalid-token"})
    assert invalid.status_code == 401
    assert "hoja_session" not in invalid.cookies


def test_api_key_login_skips_workspace_lookup_on_outdated_schema(tmp_path) -> None:
    db_path = tmp_path / "browser-api-key-outdated.db"
    engine = make_engine(db_path)
    migrate(engine)
    seeded = seed_tenant(engine, org_name="Outdated Workspace", org_url_key="outdated-login",
                         user_name="API Key User", user_email="outdated@example.test",
                         demo_issues=False)
    organization_membership.drop(engine)
    global_identity.drop(engine)
    client = TestClient(create_app(str(db_path), open_mode=False))

    login = client.post("/auth/login", json={"apiKey": seeded["token"]})
    assert login.status_code == 200
    assert "hoja_session" in login.cookies

    invalid = client.post("/auth/login", json={"apiKey": "invalid-token"})
    assert invalid.status_code == 401
    assert "hoja_session" not in invalid.cookies

    email_login = client.post("/auth/login", json={
        "email": "outdated@example.test", "password": "irrelevant",
    })
    assert email_login.status_code == 503
    assert "migrated" in email_login.json()["error"]


def test_global_identity_can_switch_only_to_its_explicit_memberships(tmp_path) -> None:
    db_path = tmp_path / "identity-switch.db"
    engine = make_engine(db_path)
    migrate(engine)
    one = seed_tenant(engine, org_name="Switch One", org_url_key="switch-one",
                      user_name="Shared Person One", user_email="shared-switch@example.test",
                      demo_issues=False)
    two = seed_tenant(engine, org_name="Switch Two", org_url_key="switch-two",
                      user_name="Shared Person Two", user_email="shared-switch@example.test",
                      demo_issues=False)
    outsider = seed_tenant(engine, org_name="Outsider", org_url_key="switch-outsider",
                           user_name="Other Person", user_email="other-switch@example.test",
                           demo_issues=False)
    client = TestClient(create_app(str(db_path), open_mode=False))
    for seeded in (one, two, outsider):
        assert client.post("/auth/setup", json={"token": seeded["token"],
            "password": "correct horse battery"}).status_code == 201

    need_choice = client.post("/auth/login", json={"email": "shared-switch@example.test",
                              "password": "correct horse battery"})
    assert need_choice.status_code == 409
    available = client.post("/auth/workspaces", json={"email": "shared-switch@example.test"}).json()
    assert {w["organizationId"] for w in available["workspaces"]} == {one["org_id"], two["org_id"]}
    login = client.post("/auth/login", json={"email": "shared-switch@example.test",
        "password": "correct horse battery", "organizationId": one["org_id"]})
    assert login.status_code == 200
    assert client.get("/auth/me").json()["organizationId"] == one["org_id"]

    switched = client.post("/graphql", json={"query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success organization{name}}}",
                                                   "variables": {"id": two["org_id"]}})
    assert switched.json()["data"]["workspaceSwitch"]["success"] is False
    assert client.get("/auth/me").json()["organizationId"] == one["org_id"]
    denied = client.post("/graphql", json={"query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success}}",
                                                 "variables": {"id": outsider["org_id"]}})
    assert denied.json()["data"]["workspaceSwitch"]["success"] is False
    assert client.get("/auth/me").json()["organizationId"] == one["org_id"]

    # Explicitly add the second org profile to the same identity; an active membership enables switching.
    from cliniar_server.db import organization_membership
    with engine.begin() as conn:
        identity_id = conn.execute(select(organization_membership.c.identity_id).where(
            organization_membership.c.profile_user_id == one["user_id"])).scalar_one()
        conn.execute(organization_membership.update().where(
            organization_membership.c.profile_user_id == two["user_id"]).values(identity_id=identity_id))
    allowed = client.post("/graphql", json={"query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success organization{name}}}",
                                               "variables": {"id": two["org_id"]}})
    assert allowed.json()["data"]["workspaceSwitch"]["success"] is True
    assert client.get("/auth/me").json()["organizationId"] == two["org_id"]
    # API keys remain pinned to their organization even when the browser session switches.
    api_client = TestClient(create_app(str(db_path), open_mode=False))
    api_key = api_client.post("/graphql", headers={"Authorization": two["token"]}, json={
        "query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success}}",
        "variables": {"id": one["org_id"]}})
    assert api_key.json()["data"]["workspaceSwitch"]["success"] is False


def test_cross_identity_workspace_link_requires_verified_invitation(tmp_path) -> None:
    db_path = tmp_path / "identity-link.db"
    engine = make_engine(db_path)
    migrate(engine)
    one = seed_tenant(engine, org_name="Link One", org_url_key="link-one",
                      user_name="Person One", user_email="link@example.test", demo_issues=False)
    two = seed_tenant(engine, org_name="Link Two", org_url_key="link-two",
                      user_name="Person Two", user_email="link@example.test", demo_issues=False)
    app = create_app(str(db_path), open_mode=False)
    client_a, client_b = TestClient(app), TestClient(app)
    assert client_a.post("/auth/setup", json={"token": one["token"], "password": "correct horse battery"}).status_code == 201
    assert client_b.post("/auth/setup", json={"token": two["token"], "password": "another secure password"}).status_code == 201
    assert client_a.post("/auth/login", json={"email": "link@example.test", "password": "correct horse battery",
                                               "organizationId": one["org_id"]}).status_code == 200
    assert client_b.post("/auth/login", json={"email": "link@example.test", "password": "another secure password",
                                               "organizationId": two["org_id"]}).status_code == 200
    denied = client_a.post("/graphql", json={"query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success}}",
                                             "variables": {"id": two["org_id"]}})
    assert denied.json()["data"]["workspaceSwitch"]["success"] is False
    create = client_b.post("/graphql", json={"query": "mutation($id:String!){membershipInvitationCreate(userId:$id){success inviteCode}}",
                                              "variables": {"id": two["user_id"]}}).json()["data"]["membershipInvitationCreate"]
    assert create["success"] is True
    mismatch = client_a.post("/graphql", json={"query": "mutation($code:String!,$pw:String!){membershipInvitationAccept(code:$code,inviteePassword:$pw){success}}",
                                                "variables": {"code": create["inviteCode"], "pw": "correct horse battery"}})
    assert mismatch.json()["data"]["membershipInvitationAccept"]["success"] is False
    accepted = client_a.post("/graphql", json={"query": "mutation($code:String!,$pw:String!){membershipInvitationAccept(code:$code,inviteePassword:$pw){success}}",
                                                "variables": {"code": create["inviteCode"], "pw": "another secure password"}})
    assert accepted.json()["data"]["membershipInvitationAccept"]["success"] is True
    switched = client_b.post("/graphql", json={"query": "mutation($id:String!){workspaceSwitch(organizationId:$id){success}}",
                                                "variables": {"id": one["org_id"]}})
    assert switched.json()["data"]["workspaceSwitch"]["success"] is True


def test_workspace_members_and_admin_update_are_org_scoped(tmp_path) -> None:
    suffix = uuid.uuid4().hex[:8]
    engine = make_engine(tmp_path / "workspace-admin.db")
    migrate(engine)
    one = seed_tenant(engine, org_name="One", org_url_key=f"one-{suffix}",
                      user_name="Admin One", user_email=f"admin1-{suffix}@example.test",
                      demo_issues=False)
    two = seed_tenant(engine, org_name="Two", org_url_key=f"two-{suffix}",
                      user_name="Admin Two", user_email=f"admin2-{suffix}@example.test",
                      demo_issues=False)
    app = create_app(str(tmp_path / "workspace-admin.db"), open_mode=False)
    client = TestClient(app)

    def gql(token, query, variables=None):
        return client.post("/graphql", headers={"Authorization": token},
                           json={"query": query, "variables": variables or {}}).json()

    members = gql(one["token"], "{ organizationMembers { nodes { email admin } } workspace { id name urlKey } }")
    assert "errors" not in members
    assert [m["email"] for m in members["data"]["organizationMembers"]["nodes"]] == [f"admin1-{suffix}@example.test"]
    assert members["data"]["workspace"]["name"] == "One"
    updated = gql(one["token"], "mutation($input: WorkspaceUpdateInput!){workspaceUpdate(input:$input){success organization{name urlKey}}}",
                  {"input": {"name": "Renamed One", "urlKey": f"renamed-{suffix}"}})
    assert "errors" not in updated
    assert updated["data"]["workspaceUpdate"]["organization"]["name"] == "Renamed One"
    still_two = gql(two["token"], "{ workspace { name urlKey } organizationMembers { nodes { email } } }")
    assert still_two["data"]["workspace"]["name"] == "Two"
    assert still_two["data"]["organizationMembers"]["nodes"][0]["email"] == f"admin2-{suffix}@example.test"
    outsider_role = gql(one["token"], "mutation($id:String!){memberRoleUpdate(userId:$id,admin:true){success user{id}}}",
                        {"id": two["user_id"]})
    assert outsider_role["data"]["memberRoleUpdate"]["success"] is False
    second_admin = new_id()
    from cliniar_server.db import user as user_table
    with engine.begin() as conn:
        conn.execute(user_table.insert().values(id=second_admin, organization_id=one["org_id"],
                     name="Second Admin", email=f"second-{suffix}@example.test", active=True,
                     admin=True, created_at=now_iso(), updated_at=now_iso()))
    granted = gql(one["token"], "mutation($id:String!){memberRoleUpdate(userId:$id,admin:false){success user{id admin}}}",
                  {"id": second_admin})
    assert granted["data"]["memberRoleUpdate"]["success"] is True
    assert granted["data"]["memberRoleUpdate"]["user"]["admin"] is False
    invited = gql(one["token"], "mutation($input:MemberInviteInput!){memberInvite(input:$input){success user{id email admin} apiKey}}",
                  {"input": {"name": "New teammate", "email": f"new-{suffix}@example.test"}})
    invited_user = invited["data"]["memberInvite"]
    assert invited_user["success"] is True
    assert invited_user["user"]["email"] == f"new-{suffix}@example.test"
    assert invited_user["apiKey"].startswith("lin_api_")
    duplicate = gql(one["token"], "mutation($input:MemberInviteInput!){memberInvite(input:$input){success}}",
                    {"input": {"name": "Duplicate", "email": f"new-{suffix}@example.test"}})
    assert duplicate["data"]["memberInvite"]["success"] is False
    denied_invite = gql(two["token"], "mutation($input:MemberInviteInput!){memberInvite(input:$input){success}}",
                        {"input": {"name": "No admin", "email": f"not-admin-{suffix}@example.test"}})
    assert denied_invite["data"]["memberInvite"]["success"] is True

    with engine.begin() as conn:
        conn.execute(user_table.update().where(user_table.c.id == one["user_id"]).values(admin=False))
    denied = gql(one["token"], "mutation($input: WorkspaceUpdateInput!){workspaceUpdate(input:$input){success organization{name}}}",
                 {"input": {"name": "Unauthorized"}})
    assert "errors" not in denied
    assert denied["data"]["workspaceUpdate"]["success"] is False
    denied_invite = gql(one["token"], "mutation($input:MemberInviteInput!){memberInvite(input:$input){success apiKey}}",
                        {"input": {"name": "No admin", "email": f"not-admin-{suffix}@example.test"}})
    assert denied_invite["data"]["memberInvite"]["success"] is False
    assert denied_invite["data"]["memberInvite"]["apiKey"] is None
    assert gql(one["token"], "{ workspace { name } }")["data"]["workspace"]["name"] == "Renamed One"
