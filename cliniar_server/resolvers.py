"""Ariadne resolver bindings — maps the SDL to Store/Writer.

Auth context (user_id, organization_id) is attached to `info.context` by the
FastAPI middleware in app.py. Every resolver reads ctx and stays org-scoped.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ariadne import (
    MutationType,
    ObjectType,
    QueryType,
    ScalarType,
    make_executable_schema,
)

query = QueryType()
mutation = MutationType()

# Object types needing custom field resolvers
Team = ObjectType("Team")
Issue = ObjectType("Issue")
Project = ObjectType("Project")
Comment = ObjectType("Comment")
WorkflowState = ObjectType("WorkflowState")
Cycle = ObjectType("Cycle")
Attachment = ObjectType("Attachment")

datetime_scalar = ScalarType("DateTime")
timeless_scalar = ScalarType("TimelessDate")
json_scalar = ScalarType("JSON")


@datetime_scalar.serializer
def _ser_dt(value):
    return value  # already ISO strings in the DB


@timeless_scalar.serializer
def _ser_td(value):
    return value


@json_scalar.serializer
def _ser_json(value):
    return value


def _ctx(info):
    return info.context["store"], info.context["writer"], info.context["org_id"], info.context["user_id"]


def _conn(nodes: list) -> dict:
    return {
        "nodes": nodes,
        "pageInfo": {
            "hasNextPage": False, "hasPreviousPage": False,
            "startCursor": None,
            "endCursor": (nodes[-1].get("id") if nodes else None),
        },
    }


# ----------------------------------------------------------------- Query
@query.field("viewer")
def r_viewer(_, info):
    store, _w, org, uid = _ctx(info)
    return store.viewer(org, uid)


@query.field("teams")
def r_teams(_, info, first=50, after=None, filter=None):
    store, _w, org, _uid = _ctx(info)
    key = None
    if filter and "key" in filter and "eq" in filter["key"]:
        key = filter["key"]["eq"]
    return _conn(store.teams(org, key=key)[:first])


@query.field("team")
def r_team(_, info, id):
    store, _w, org, _uid = _ctx(info)
    row = store.team_by_id_or_key(org, id)
    if not row:
        return None
    t = store.ser_team(row)
    t["_active_cycle_id"] = row.get("active_cycle_id")
    return t


@query.field("issues")
def r_issues(_, info, filter=None, first=50, after=None, orderBy="updatedAt"):  # noqa: N803
    store, _w, org, uid = _ctx(info)
    nodes = store.issues(org, uid, filter, order_by=orderBy or "updatedAt")
    return _conn(nodes[:first])


@query.field("issue")
def r_issue(_, info, id):
    store, _w, org, _uid = _ctx(info)
    return store.issue_by_id_or_identifier(org, id)


@query.field("projects")
def r_projects(_, info, filter=None, first=50, after=None):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.projects(org, filter)[:first])


@query.field("project")
def r_project(_, info, id):
    store, _w, org, _uid = _ctx(info)
    return store.project_by_id(org, id)


@query.field("workflowStates")
def r_workflow_states(_, info, filter=None, first=100, after=None):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.workflow_states(org, filter)[:first])


@query.field("cycles")
def r_cycles(_, info, filter=None, first=100, after=None):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.cycles(org, filter)[:first])


@query.field("issueLabels")
def r_labels(_, info, filter=None, first=100, after=None):
    store, _w, org, _uid = _ctx(info)
    team_id = None
    name = None
    if filter:
        if "team" in filter and "id" in filter["team"] and "eq" in filter["team"]["id"]:
            team_id = filter["team"]["id"]["eq"]
        if "name" in filter and "eq" in filter["name"]:
            name = filter["name"]["eq"]
    return _conn(store.labels(org, team_id=team_id, name=name)[:first])


@query.field("searchIssues")
def r_search(_, info, term, first=20):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.search_issues(org, term)[:first])


@query.field("rateLimitStatus")
def r_rate_limit(_, info):
    resets = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    return {
        "identifier": "local", "kind": "unlimited",
        "limit": 1000000, "remaining": 1000000, "requestsPerHour": 1000000,
        "resetsAt": resets,
    }


# ----------------------------------------------------------------- Team fields
@Team.field("states")
def t_states(obj, info, first=100):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.team_states(org, obj["id"])[:first])


@Team.field("members")
def t_members(obj, info, first=100):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.team_members(org, obj["id"])[:first])


@Team.field("cycles")
def t_cycles(obj, info, first=50):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.team_cycles(org, obj["id"])[:first])


@Team.field("activeCycle")
def t_active_cycle(obj, info):
    store, _w, org, _uid = _ctx(info)
    cid = obj.get("_active_cycle_id")
    if not cid:
        return None
    cycles = store.team_cycles(org, obj["id"])
    return next((c for c in cycles if c["id"] == cid), None)


# ----------------------------------------------------------------- State/cycle fields
@WorkflowState.field("team")
@Cycle.field("team")
def reference_team(obj, info):
    store, _w, org, _uid = _ctx(info)
    tid = obj.get("_team_id")
    if not tid:
        return None
    return store.ser_team(store.raw_team(org, tid))


# ----------------------------------------------------------------- Issue fields
@Issue.field("state")
def i_state(obj, info):
    store, _w, org, _uid = _ctx(info)
    return store.state_by_id(org, obj["_state_id"]) if obj.get("_state_id") else None


@Issue.field("assignee")
def i_assignee(obj, info):
    store, _w, org, uid = _ctx(info)
    return store.ser_user(store.get_user(org, obj["_assignee_id"]), uid) if obj.get("_assignee_id") else None


@Issue.field("creator")
def i_creator(obj, info):
    store, _w, org, uid = _ctx(info)
    return store.ser_user(store.get_user(org, obj["_creator_id"]), uid) if obj.get("_creator_id") else None


@Issue.field("team")
def i_team(obj, info):
    store, _w, org, _uid = _ctx(info)
    row = store.raw_team(org, obj["_team_id"]) if obj.get("_team_id") else None
    if not row:
        return None
    t = store.ser_team(row)
    t["_active_cycle_id"] = row.get("active_cycle_id")
    return t


@Issue.field("project")
def i_project(obj, info):
    store, _w, org, _uid = _ctx(info)
    return store.project_by_id(org, obj["_project_id"]) if obj.get("_project_id") else None


@Issue.field("cycle")
def i_cycle(obj, info):
    store, _w, org, _uid = _ctx(info)
    if not obj.get("_cycle_id"):
        return None
    with store.engine.connect() as conn:
        from sqlalchemy import and_, select

        from cliniar_server.db import cycle as cyc
        r = conn.execute(select(cyc).where(and_(cyc.c.organization_id == org, cyc.c.id == obj["_cycle_id"]))).first()
        return store.ser_cycle(dict(r._mapping)) if r else None


@Issue.field("parent")
def i_parent(obj, info):
    store, _w, org, _uid = _ctx(info)
    return store.issue_by_id_or_identifier(org, obj["_parent_id"]) if obj.get("_parent_id") else None


@Issue.field("labels")
def i_labels(obj, info, first=50):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.issue_labels_for(org, obj["id"])[:first])


@Issue.field("subscribers")
def i_subscribers(obj, info, first=50):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.issue_subscribers_for(org, obj["id"])[:first])


@Issue.field("comments")
def i_comments(obj, info, first=50):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.comments_for(org, obj["id"])[:first])


# ----------------------------------------------------------------- Project fields
@Project.field("lead")
def p_lead(obj, info):
    store, _w, org, uid = _ctx(info)
    return store.ser_user(store.get_user(org, obj["_lead_id"]), uid) if obj.get("_lead_id") else None


@Project.field("creator")
def p_creator(obj, info):
    store, _w, org, uid = _ctx(info)
    return store.ser_user(store.get_user(org, obj["_creator_id"]), uid) if obj.get("_creator_id") else None


@Project.field("members")
def p_members(obj, info, first=100):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.project_members(org, obj["id"])[:first])


@Project.field("teams")
def p_teams(obj, info, first=100):
    store, _w, org, _uid = _ctx(info)
    return _conn(store.project_teams(org, obj["id"])[:first])


# ----------------------------------------------------------------- Comment fields
@Comment.field("user")
def c_user(obj, info):
    store, _w, org, uid = _ctx(info)
    return store.ser_user(store.get_user(org, obj["_user_id"]), uid) if obj.get("_user_id") else None


# ----------------------------------------------------------------- Mutations
@mutation.field("issueCreate")
def m_issue_create(_, info, input):
    store, w, org, uid = _ctx(info)
    iid = w.issue_create(org, uid, input)
    if not iid:
        return {"success": False, "issue": None}
    return {"success": True, "issue": store.issue_by_id_or_identifier(org, iid)}


@mutation.field("issueUpdate")
def m_issue_update(_, info, id, input):
    store, w, org, _uid = _ctx(info)
    iid = w.issue_update(org, id, input)
    if not iid:
        return {"success": False, "issue": None}
    return {"success": True, "issue": store.issue_by_id_or_identifier(org, iid)}


@mutation.field("issueDelete")
def m_issue_delete(_, info, id):
    _s, w, org, _uid = _ctx(info)
    return {"success": w.issue_delete(org, id)}


@mutation.field("issueArchive")
def m_issue_archive(_, info, id):
    _s, w, org, _uid = _ctx(info)
    return {"success": w.issue_archive(org, id)}


@mutation.field("commentCreate")
def m_comment_create(_, info, input):
    store, w, org, uid = _ctx(info)
    cid = w.comment_create(org, uid, input)
    if not cid:
        return {"success": False, "comment": None}
    return {"success": True, "comment": _get_comment(store, org, cid)}


@mutation.field("commentUpdate")
def m_comment_update(_, info, id, input):
    store, w, org, _uid = _ctx(info)
    cid = w.comment_update(org, id, input)
    if not cid:
        return {"success": False, "comment": None}
    return {"success": True, "comment": _get_comment(store, org, cid)}


@mutation.field("commentDelete")
def m_comment_delete(_, info, id):
    _s, w, org, _uid = _ctx(info)
    return {"success": w.comment_delete(org, id)}


@mutation.field("issueLabelCreate")
def m_label_create(_, info, input):
    store, w, org, _uid = _ctx(info)
    lid = w.label_create(org, input)
    labels = store.labels(org)
    node = next((label for label in labels if label["id"] == lid), None)
    return {"success": bool(lid), "issueLabel": node}


@mutation.field("issueLabelDelete")
def m_label_delete(_, info, id):
    _s, w, org, _uid = _ctx(info)
    return {"success": w.label_delete(org, id)}


@mutation.field("projectCreate")
def m_project_create(_, info, input):
    store, w, org, uid = _ctx(info)
    pid = w.project_create(org, uid, input)
    return {"success": bool(pid), "project": store.project_by_id(org, pid) if pid else None}


@mutation.field("projectUpdate")
def m_project_update(_, info, id, input):
    store, w, org, _uid = _ctx(info)
    pid = w.project_update(org, id, input)
    return {"success": bool(pid), "project": store.project_by_id(org, pid) if pid else None}


@mutation.field("projectArchive")
def m_project_archive(_, info, id):
    _s, w, org, _uid = _ctx(info)
    return {"success": w.project_archive(org, id)}


@mutation.field("attachmentCreate")
def m_attachment_create(_, info, input):
    _store, w, org, uid = _ctx(info)
    created = w.attachment_create(org, uid, input)
    return {"success": bool(created), "attachment": created}


@Attachment.field("issue")
def a_issue(obj, info):
    store, _w, org, _uid = _ctx(info)
    return store.issue_by_id_or_identifier(org, obj["_issue_id"])


def _get_comment(store, org, cid):
    from sqlalchemy import and_, select

    from cliniar_server.db import comment as cmt
    with store.engine.connect() as conn:
        r = conn.execute(select(cmt).where(and_(cmt.c.organization_id == org, cmt.c.id == cid))).first()
        return store.ser_comment(dict(r._mapping)) if r else None


def build_schema():
    from pathlib import Path
    sdl = (Path(__file__).parent / "schema.graphql").read_text()
    return make_executable_schema(
        sdl, query, mutation, Team, Issue, Project, Comment,
        WorkflowState, Cycle, Attachment,
        datetime_scalar, timeless_scalar, json_scalar,
    )
