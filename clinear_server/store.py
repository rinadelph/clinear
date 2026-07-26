"""Store — org-scoped data access + serialization to Linear camelCase shapes.

Every method takes an org_id and NEVER returns rows from other orgs → tenant
isolation by construction. Serializers emit exactly the camelCase field names
clinear's Pydantic models expect.
"""
from __future__ import annotations

from sqlalchemy import and_, or_, select
from sqlalchemy.engine import Engine

from clinear_server.db import (
    api_key,
    comment,
    cycle,
    issue,
    issue_label,
    issue_label_link,
    issue_subscriber,
    project,
    project_member,
    team,
    team_member,
    token_hash,
    user,
    workflow_state,
)


def _conn_rows(conn, stmt) -> list[dict]:
    return [dict(r._mapping) for r in conn.execute(stmt)]


def _one(conn, stmt) -> dict | None:
    r = conn.execute(stmt).first()
    return dict(r._mapping) if r else None


class Store:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # ------------------------------------------------------------------ auth
    def resolve_token(self, token: str) -> dict | None:
        """token → {user_id, organization_id} or None."""
        th = token_hash(token)
        with self.engine.connect() as conn:
            row = _one(
                conn,
                select(api_key)
                .join(
                    user,
                    and_(
                        user.c.id == api_key.c.user_id,
                        user.c.organization_id == api_key.c.organization_id,
                    ),
                )
                .where(
                    and_(
                        api_key.c.token_hash == th,
                        api_key.c.revoked_at.is_(None),
                        user.c.active.is_(True),
                        user.c.archived_at.is_(None),
                    )
                ),
            )
            return row

    # ------------------------------------------------------------ serializers
    def ser_user(self, row: dict | None, ctx_user_id: str | None = None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row.get("name"), "displayName": row.get("display_name"),
            "email": row.get("email"), "active": bool(row.get("active", True)),
            "isMe": row["id"] == ctx_user_id, "admin": bool(row.get("admin", False)),
            "avatarUrl": row.get("avatar_url"), "url": row.get("url"),
            "timezone": row.get("timezone"), "statusEmoji": row.get("status_emoji"),
            "statusLabel": row.get("status_label"),
            "createdAt": row.get("created_at"), "updatedAt": row.get("updated_at"),
        }

    def ser_state(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row["name"], "color": row.get("color"),
            "description": row.get("description"), "position": row.get("position"),
            "type": row["type"], "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }

    def ser_team(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row["name"], "key": row["key"],
            "description": row.get("description"), "color": row.get("color"),
            "icon": row.get("icon"), "private": bool(row.get("private", False)),
            "timezone": row.get("timezone"), "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"), "_id": row["id"],
        }

    def ser_label(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row["name"], "color": row.get("color"),
            "description": row.get("description"), "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
        }

    def ser_cycle(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row.get("name"), "number": row.get("number"),
            "startsAt": row.get("starts_at"), "endsAt": row.get("ends_at"),
            "completedAt": row.get("completed_at"), "progress": row.get("progress"),
            "createdAt": row.get("created_at"), "updatedAt": row.get("updated_at"),
        }

    def ser_project(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "name": row["name"], "description": row.get("description"),
            "slugId": row.get("slug_id"), "icon": row.get("icon"), "color": row.get("color"),
            "state": row.get("state"), "progress": row.get("progress"),
            "startDate": row.get("start_date"), "targetDate": row.get("target_date"),
            "url": row.get("url"), "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"),
            "_lead_id": row.get("lead_id"), "_creator_id": row.get("creator_id"),
        }

    def ser_comment(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "body": row["body"], "url": row.get("url"),
            "createdAt": row.get("created_at"), "updatedAt": row.get("updated_at"),
            "_user_id": row.get("user_id"),
        }

    def ser_issue(self, row: dict | None) -> dict | None:
        if not row:
            return None
        return {
            "id": row["id"], "identifier": row["identifier"], "title": row["title"],
            "description": row.get("description"), "priority": row.get("priority", 0),
            "priorityLabel": row.get("priority_label"), "estimate": row.get("estimate"),
            "url": row.get("url"), "branchName": row.get("branch_name"),
            "number": row.get("number"), "createdAt": row.get("created_at"),
            "updatedAt": row.get("updated_at"), "dueDate": row.get("due_date"),
            "completedAt": row.get("completed_at"), "canceledAt": row.get("canceled_at"),
            "startedAt": row.get("started_at"), "snoozedUntilAt": row.get("snoozed_until_at"),
            # ids for lazy field resolvers
            "_state_id": row.get("state_id"), "_assignee_id": row.get("assignee_id"),
            "_creator_id": row.get("creator_id"), "_team_id": row.get("team_id"),
            "_project_id": row.get("project_id"), "_cycle_id": row.get("cycle_id"),
            "_parent_id": row.get("parent_id"), "_org_id": row.get("organization_id"),
        }

    # ------------------------------------------------------------------ reads
    def get_user(self, org_id: str, user_id: str) -> dict | None:
        with self.engine.connect() as conn:
            return _one(conn, select(user).where(
                and_(user.c.organization_id == org_id, user.c.id == user_id)))

    def viewer(self, org_id: str, user_id: str) -> dict | None:
        return self.ser_user(self.get_user(org_id, user_id), user_id)

    def teams(self, org_id: str, key: str | None = None) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(team).where(and_(
                team.c.organization_id == org_id, team.c.archived_at.is_(None)))
            if key:
                stmt = stmt.where(team.c.key == key.upper())
            stmt = stmt.order_by(team.c.key)
            return [self.ser_team(r) for r in _conn_rows(conn, stmt)]

    def team_by_id_or_key(self, org_id: str, ident: str) -> dict | None:
        with self.engine.connect() as conn:
            row = _one(conn, select(team).where(and_(
                team.c.organization_id == org_id,
                or_(team.c.id == ident, team.c.key == ident.upper()))))
            return row  # raw row (field resolvers need _id / active_cycle_id)

    def team_states(self, org_id: str, team_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(workflow_state).where(and_(
                workflow_state.c.organization_id == org_id,
                workflow_state.c.team_id == team_id,
                workflow_state.c.archived_at.is_(None))).order_by(workflow_state.c.position)
            return [self.ser_state(r) for r in _conn_rows(conn, stmt)]

    def team_members(self, org_id: str, team_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(user).select_from(
                user.join(team_member, team_member.c.user_id == user.c.id)
            ).where(and_(team_member.c.team_id == team_id, user.c.organization_id == org_id))
            return [self.ser_user(r) for r in _conn_rows(conn, stmt)]

    def team_cycles(self, org_id: str, team_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(cycle).where(and_(
                cycle.c.organization_id == org_id, cycle.c.team_id == team_id)).order_by(cycle.c.number)
            return [self.ser_cycle(r) for r in _conn_rows(conn, stmt)]

    def issue_by_id_or_identifier(self, org_id: str, ident: str) -> dict | None:
        with self.engine.connect() as conn:
            row = _one(conn, select(issue).where(and_(
                issue.c.organization_id == org_id,
                or_(issue.c.id == ident, issue.c.identifier == ident.upper()))))
            return self.ser_issue(row)

    def labels(self, org_id: str, team_id: str | None = None, name: str | None = None) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(issue_label).where(and_(
                issue_label.c.organization_id == org_id, issue_label.c.archived_at.is_(None)))
            if team_id:
                stmt = stmt.where(issue_label.c.team_id == team_id)
            if name:
                stmt = stmt.where(issue_label.c.name == name)
            return [self.ser_label(r) for r in _conn_rows(conn, stmt.order_by(issue_label.c.name))]

    def issue_labels_for(self, org_id: str, issue_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(issue_label).select_from(
                issue_label.join(issue_label_link, issue_label_link.c.label_id == issue_label.c.id)
            ).where(and_(issue_label_link.c.issue_id == issue_id,
                         issue_label.c.organization_id == org_id))
            return [self.ser_label(r) for r in _conn_rows(conn, stmt)]

    def issue_subscribers_for(self, org_id: str, issue_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(user).select_from(
                user.join(issue_subscriber, issue_subscriber.c.user_id == user.c.id)
            ).where(and_(issue_subscriber.c.issue_id == issue_id, user.c.organization_id == org_id))
            return [self.ser_user(r) for r in _conn_rows(conn, stmt)]

    def comments_for(self, org_id: str, issue_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(comment).where(and_(
                comment.c.organization_id == org_id, comment.c.issue_id == issue_id,
                comment.c.archived_at.is_(None))).order_by(comment.c.created_at)
            return [self.ser_comment(r) for r in _conn_rows(conn, stmt)]

    def projects(self, org_id: str, flt: dict | None = None) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(project).where(and_(
                project.c.organization_id == org_id, project.c.archived_at.is_(None)))
            stmt = _apply_project_filter(stmt, flt)
            return [self.ser_project(r) for r in _conn_rows(conn, stmt.order_by(project.c.created_at))]

    def project_by_id(self, org_id: str, pid: str) -> dict | None:
        with self.engine.connect() as conn:
            return self.ser_project(_one(conn, select(project).where(and_(
                project.c.organization_id == org_id, project.c.id == pid))))

    def project_members(self, org_id: str, project_id: str) -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(user).select_from(
                user.join(project_member, project_member.c.user_id == user.c.id)
            ).where(and_(project_member.c.project_id == project_id, user.c.organization_id == org_id))
            return [self.ser_user(r) for r in _conn_rows(conn, stmt)]

    def state_by_id(self, org_id: str, sid: str) -> dict | None:
        with self.engine.connect() as conn:
            return self.ser_state(_one(conn, select(workflow_state).where(and_(
                workflow_state.c.organization_id == org_id, workflow_state.c.id == sid))))

    def raw_team(self, org_id: str, tid: str) -> dict | None:
        with self.engine.connect() as conn:
            return _one(conn, select(team).where(and_(
                team.c.organization_id == org_id, team.c.id == tid)))

    # --------------------------------------------------------------- issue list
    def issues(self, org_id: str, viewer_id: str, flt: dict | None,
               order_by: str = "updatedAt") -> list[dict]:
        with self.engine.connect() as conn:
            stmt = select(issue).where(and_(
                issue.c.organization_id == org_id, issue.c.archived_at.is_(None)))
            stmt = _apply_issue_filter(conn, stmt, org_id, viewer_id, flt)
            col = issue.c.updated_at if order_by == "updatedAt" else issue.c.created_at
            stmt = stmt.order_by(col.desc())
            return [self.ser_issue(r) for r in _conn_rows(conn, stmt)]

    def search_issues(self, org_id: str, term: str) -> list[dict]:
        with self.engine.connect() as conn:
            like = f"%{term}%"
            stmt = select(issue).where(and_(
                issue.c.organization_id == org_id, issue.c.archived_at.is_(None),
                or_(issue.c.title.ilike(like), issue.c.description.ilike(like),
                    issue.c.identifier.ilike(like)))).order_by(issue.c.updated_at.desc())
            return [self.ser_issue(r) for r in _conn_rows(conn, stmt)]


# ============================================================ filter compilers
def _apply_str_cmp(col, cmp: dict):
    clauses = []
    if "eq" in cmp:
        clauses.append(col == cmp["eq"])
    if "neq" in cmp:
        clauses.append(col != cmp["neq"])
    if "in" in cmp:
        clauses.append(col.in_(cmp["in"]))
    if "nin" in cmp:
        clauses.append(col.notin_(cmp["nin"]))
    if "contains" in cmp:
        clauses.append(col.ilike(f"%{cmp['contains']}%"))
    if "containsIgnoreCase" in cmp:
        clauses.append(col.ilike(f"%{cmp['containsIgnoreCase']}%"))
    if "eqIgnoreCase" in cmp:
        clauses.append(col.ilike(cmp["eqIgnoreCase"]))
    return and_(*clauses) if clauses else None


def _apply_num_cmp(col, cmp: dict):
    clauses = []
    if "eq" in cmp:
        clauses.append(col == cmp["eq"])
    if "neq" in cmp:
        clauses.append(col != cmp["neq"])
    if "gt" in cmp:
        clauses.append(col > cmp["gt"])
    if "lt" in cmp:
        clauses.append(col < cmp["lt"])
    if "gte" in cmp:
        clauses.append(col >= cmp["gte"])
    if "lte" in cmp:
        clauses.append(col <= cmp["lte"])
    if "in" in cmp:
        clauses.append(col.in_(cmp["in"]))
    if "nin" in cmp:
        clauses.append(col.notin_(cmp["nin"]))
    return and_(*clauses) if clauses else None


def _apply_date_cmp(col, cmp: dict):
    # ISO strings sort lexicographically → string comparison is correct
    clauses = []
    if "eq" in cmp:
        clauses.append(col == cmp["eq"])
    if "gt" in cmp:
        clauses.append(col > cmp["gt"])
    if "lt" in cmp:
        clauses.append(col < cmp["lt"])
    if "gte" in cmp:
        clauses.append(col >= cmp["gte"])
    if "lte" in cmp:
        clauses.append(col <= cmp["lte"])
    return and_(*clauses) if clauses else None


def _apply_project_filter(stmt, flt: dict | None):
    if not flt:
        return stmt
    if "slugId" in flt:
        c = _apply_str_cmp(project.c.slug_id, flt["slugId"])
        if c is not None:
            stmt = stmt.where(c)
    if "name" in flt:
        c = _apply_str_cmp(project.c.name, flt["name"])
        if c is not None:
            stmt = stmt.where(c)
    if "state" in flt:
        c = _apply_str_cmp(project.c.state, flt["state"])
        if c is not None:
            stmt = stmt.where(c)
    return stmt


def _resolve_team_ids(conn, org_id: str, cmp: dict) -> list[str]:
    stmt = select(team.c.id).where(team.c.organization_id == org_id)
    if "key" in cmp:
        kc = _apply_str_cmp(team.c.key, cmp["key"])
        if kc is not None:
            stmt = stmt.where(kc)
    if "id" in cmp:
        ic = _apply_str_cmp(team.c.id, cmp["id"])
        if ic is not None:
            stmt = stmt.where(ic)
    return [r[0] for r in conn.execute(stmt)]


def _resolve_state_ids(conn, org_id: str, cmp: dict) -> list[str]:
    stmt = select(workflow_state.c.id).where(workflow_state.c.organization_id == org_id)
    if "name" in cmp:
        c = _apply_str_cmp(workflow_state.c.name, cmp["name"])
        if c is not None:
            stmt = stmt.where(c)
    if "type" in cmp:
        c = _apply_str_cmp(workflow_state.c.type, cmp["type"])
        if c is not None:
            stmt = stmt.where(c)
    return [r[0] for r in conn.execute(stmt)]


def _resolve_user_ids(conn, org_id: str, cmp: dict) -> list[str]:
    stmt = select(user.c.id).where(user.c.organization_id == org_id)
    if "id" in cmp:
        c = _apply_str_cmp(user.c.id, cmp["id"])
        if c is not None:
            stmt = stmt.where(c)
    if "email" in cmp:
        c = _apply_str_cmp(user.c.email, cmp["email"])
        if c is not None:
            stmt = stmt.where(c)
    if "displayName" in cmp:
        c = _apply_str_cmp(user.c.display_name, cmp["displayName"])
        if c is not None:
            stmt = stmt.where(c)
    return [r[0] for r in conn.execute(stmt)]


def _apply_issue_filter(conn, stmt, org_id, viewer_id, flt: dict | None):
    if not flt:
        return stmt
    if "team" in flt:
        ids = _resolve_team_ids(conn, org_id, flt["team"])
        stmt = stmt.where(issue.c.team_id.in_(ids or ["__none__"]))
    if "state" in flt:
        ids = _resolve_state_ids(conn, org_id, flt["state"])
        stmt = stmt.where(issue.c.state_id.in_(ids or ["__none__"]))
    for who, col in (("assignee", issue.c.assignee_id), ("creator", issue.c.creator_id)):
        if who in flt:
            ids = _resolve_user_ids(conn, org_id, flt[who])
            stmt = stmt.where(col.in_(ids or ["__none__"]))
    if "project" in flt:
        cmp = flt["project"]
        if "id" in cmp:
            c = _apply_str_cmp(issue.c.project_id, cmp["id"])
            if c is not None:
                stmt = stmt.where(c)
        elif "name" in cmp:
            sub = select(project.c.id).where(project.c.organization_id == org_id)
            nc = _apply_str_cmp(project.c.name, cmp["name"])
            if nc is not None:
                sub = sub.where(nc)
            stmt = stmt.where(issue.c.project_id.in_([r[0] for r in conn.execute(sub)] or ["__none__"]))
    if "priority" in flt:
        c = _apply_num_cmp(issue.c.priority, flt["priority"])
        if c is not None:
            stmt = stmt.where(c)
    if "number" in flt:
        c = _apply_num_cmp(issue.c.number, flt["number"])
        if c is not None:
            stmt = stmt.where(c)
    if "title" in flt:
        c = _apply_str_cmp(issue.c.title, flt["title"])
        if c is not None:
            stmt = stmt.where(c)
    if "description" in flt:
        c = _apply_str_cmp(issue.c.description, flt["description"])
        if c is not None:
            stmt = stmt.where(c)
    for datef, col in (("updatedAt", issue.c.updated_at), ("createdAt", issue.c.created_at),
                       ("dueDate", issue.c.due_date)):
        if datef in flt:
            c = _apply_date_cmp(col, flt[datef])
            if c is not None:
                stmt = stmt.where(c)
    if "labels" in flt and "name" in flt["labels"]:
        sub = select(issue_label_link.c.issue_id).select_from(
            issue_label_link.join(issue_label, issue_label.c.id == issue_label_link.c.label_id)
        ).where(issue_label.c.organization_id == org_id)
        nc = _apply_str_cmp(issue_label.c.name, flt["labels"]["name"])
        if nc is not None:
            sub = sub.where(nc)
        stmt = stmt.where(issue.c.id.in_([r[0] for r in conn.execute(sub)] or ["__none__"]))
    if "or" in flt:
        ors = []
        for sub in flt["or"]:
            if "title" in sub:
                c = _apply_str_cmp(issue.c.title, sub["title"])
                if c is not None:
                    ors.append(c)
            if "description" in sub:
                c = _apply_str_cmp(issue.c.description, sub["description"])
                if c is not None:
                    ors.append(c)
        if ors:
            stmt = stmt.where(or_(*ors))
    return stmt
