"""Write operations with transactional identifiers and derived fields."""
from __future__ import annotations

from urllib.parse import urlparse

from graphql import GraphQLError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.engine import Engine

from cliniar_server.db import (
    PRIORITY_LABELS,
    attachment,
    comment,
    cycle,
    entity_url,
    issue,
    issue_label,
    issue_label_link,
    new_id,
    now_iso,
    organization,
    project,
    project_member,
    project_team,
    team,
    team_member,
    user,
    workflow_state,
)


def _slug(text: str, n: int = 24) -> str:
    out = "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out[:n].strip("-")


def _org_url_key(conn, org_id: str) -> str:
    r = conn.execute(select(organization.c.url_key).where(organization.c.id == org_id)).first()
    return (r[0] if r and r[0] else "local")


class InvalidReferenceError(GraphQLError):
    def __init__(self, field: str) -> None:
        super().__init__(
            "Invalid reference",
            extensions={"code": "BAD_USER_INPUT", "field": field},
        )


def _require_org_reference(conn, table, org_id: str, value: str, field: str, *extra) -> str:
    conditions = [
        table.c.id == value,
        table.c.organization_id == org_id,
        *extra,
    ]
    if "archived_at" in table.c:
        conditions.append(table.c.archived_at.is_(None))
    if not conn.execute(select(table.c.id).where(and_(*conditions))).first():
        raise InvalidReferenceError(field)
    return value


def _require_team_user(conn, org_id: str, team_id: str, value: str, field: str) -> str:
    row = conn.execute(
        select(user.c.id)
        .join(team_member, team_member.c.user_id == user.c.id)
        .where(
            and_(
                user.c.id == value,
                user.c.organization_id == org_id,
                user.c.active.is_(True),
                user.c.archived_at.is_(None),
                team_member.c.team_id == team_id,
            )
        )
    ).first()
    if not row:
        raise InvalidReferenceError(field)
    return value


def _validate_issue_references(
    conn,
    org_id: str,
    team_id: str,
    inp: dict,
    *,
    issue_id: str | None = None,
    default_state_id: str | None = None,
) -> None:
    state_id = inp.get("stateId") if "stateId" in inp else default_state_id
    if state_id:
        _require_org_reference(
            conn, workflow_state, org_id, state_id, "stateId",
            workflow_state.c.team_id == team_id,
        )
    if assignee_id := inp.get("assigneeId"):
        _require_team_user(conn, org_id, team_id, assignee_id, "assigneeId")
    if project_id := inp.get("projectId"):
        _require_org_reference(conn, project, org_id, project_id, "projectId")
        project_teams = list(
            conn.execute(
                select(project_team.c.team_id).where(
                    project_team.c.project_id == project_id
                )
            ).scalars()
        )
        if project_teams and team_id not in project_teams:
            raise InvalidReferenceError("projectId")
    if cycle_id := inp.get("cycleId"):
        _require_org_reference(
            conn, cycle, org_id, cycle_id, "cycleId", cycle.c.team_id == team_id
        )
    if parent_id := inp.get("parentId"):
        if parent_id == issue_id:
            raise InvalidReferenceError("parentId")
        _require_org_reference(
            conn, issue, org_id, parent_id, "parentId", issue.c.team_id == team_id
        )
    label_ids = inp.get("labelIds") if "labelIds" in inp else None
    if label_ids:
        expected = set(label_ids)
        found = set(
            conn.execute(
                select(issue_label.c.id).where(
                    and_(
                        issue_label.c.id.in_(expected),
                        issue_label.c.organization_id == org_id,
                        issue_label.c.archived_at.is_(None),
                        or_(
                            issue_label.c.team_id.is_(None),
                            issue_label.c.team_id == team_id,
                        ),
                    )
                )
            ).scalars()
        )
        if found != expected:
            raise InvalidReferenceError("labelIds")


class Writer:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    # -------------------------------------------------------------- issues
    def issue_create(self, org_id: str, viewer_id: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            team_ref = inp["teamId"]
            trow = conn.execute(select(team).where(and_(
                team.c.organization_id == org_id,
                (team.c.id == team_ref) | (team.c.key == str(team_ref).upper())))).first()
            if not trow:
                return None
            trow = dict(trow._mapping)
            tid = trow["id"]
            _validate_issue_references(
                conn,
                org_id,
                tid,
                inp,
                default_state_id=trow.get("default_state_id"),
            )
            result = conn.execute(
                team.update()
                .where(and_(team.c.id == tid, team.c.organization_id == org_id))
                .values(issue_counter=func.coalesce(team.c.issue_counter, 0) + 1)
            )
            if result.rowcount != 1:
                raise InvalidReferenceError("teamId")
            n = conn.execute(
                select(team.c.issue_counter).where(
                    and_(team.c.id == tid, team.c.organization_id == org_id)
                )
            ).scalar_one()
            ident = f"{trow['key']}-{n}"
            prio = int(inp.get("priority", 0) or 0)
            state_id = inp.get("stateId") or trow.get("default_state_id")
            ts = now_iso()
            url_key = _org_url_key(conn, org_id)
            iid = new_id()
            conn.execute(issue.insert().values(
                id=iid, organization_id=org_id, team_id=tid, number=n, identifier=ident,
                title=inp["title"], description=inp.get("description"),
                priority=prio, priority_label=PRIORITY_LABELS.get(prio, "No priority"),
                estimate=inp.get("estimate"), state_id=state_id,
                assignee_id=inp.get("assigneeId"), creator_id=viewer_id,
                project_id=inp.get("projectId"), cycle_id=inp.get("cycleId"),
                parent_id=inp.get("parentId"),
                url=entity_url(url_key, "issue", ident),
                branch_name=f"{viewer_id[:8]}/{ident.lower()}-{_slug(inp['title'])}",
                due_date=inp.get("dueDate"), created_at=ts, updated_at=ts,
            ))
            self._apply_state_ts(conn, org_id, iid, state_id, ts)
            for lid in (inp.get("labelIds") or []):
                conn.execute(issue_label_link.insert().values(issue_id=iid, label_id=lid))
            return iid

    def issue_update(self, org_id: str, ident: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            row = conn.execute(select(issue).where(and_(
                issue.c.organization_id == org_id,
                (issue.c.id == ident) | (issue.c.identifier == ident.upper())))).first()
            if not row:
                return None
            issue_row = dict(row._mapping)
            iid = issue_row["id"]
            _validate_issue_references(
                conn, org_id, issue_row["team_id"], inp, issue_id=iid
            )
            ts = now_iso()
            values: dict = {"updated_at": ts}
            mapping = {
                "title": "title", "description": "description", "estimate": "estimate",
                "assigneeId": "assignee_id", "projectId": "project_id",
                "cycleId": "cycle_id", "parentId": "parent_id", "dueDate": "due_date",
            }
            for k, col in mapping.items():
                if k in inp:
                    values[col] = inp[k]
            if "priority" in inp:
                p = int(inp["priority"] or 0)
                values["priority"] = p
                values["priority_label"] = PRIORITY_LABELS.get(p, "No priority")
            if "stateId" in inp:
                values["state_id"] = inp["stateId"]
            conn.execute(issue.update().where(issue.c.id == iid).values(**values))
            if "stateId" in inp:
                self._apply_state_ts(conn, org_id, iid, inp["stateId"], ts)
            if "labelIds" in inp:
                conn.execute(issue_label_link.delete().where(issue_label_link.c.issue_id == iid))
                for lid in (inp.get("labelIds") or []):
                    conn.execute(issue_label_link.insert().values(issue_id=iid, label_id=lid))
            return iid

    def _apply_state_ts(self, conn, org_id, iid, state_id, ts):
        if not state_id:
            return
        srow = conn.execute(select(workflow_state.c.type).where(and_(
            workflow_state.c.organization_id == org_id,
            workflow_state.c.id == state_id))).first()
        if not srow:
            return
        stype = srow[0]
        vals: dict = {}
        if stype == "started":
            vals = {"started_at": ts, "completed_at": None, "canceled_at": None}
        elif stype == "completed":
            cur = conn.execute(select(issue.c.started_at).where(issue.c.id == iid)).first()
            vals = {"completed_at": ts, "canceled_at": None}
            if not (cur and cur[0]):
                vals["started_at"] = ts
        elif stype == "canceled":
            vals = {"canceled_at": ts}
        elif stype in ("backlog", "unstarted", "triage"):
            vals = {"started_at": None, "completed_at": None, "canceled_at": None}
        if vals:
            conn.execute(issue.update().where(issue.c.id == iid).values(**vals))

    def issue_archive(self, org_id: str, ident: str) -> bool:
        return self._soft_delete(issue, org_id, ident, by_identifier=True)

    def issue_delete(self, org_id: str, ident: str) -> bool:
        return self._soft_delete(issue, org_id, ident, by_identifier=True)

    def _soft_delete(self, table, org_id, ident, by_identifier=False) -> bool:
        with self.engine.begin() as conn:
            cond = (table.c.id == ident)
            if by_identifier and "identifier" in table.c:
                cond = cond | (table.c.identifier == ident.upper())
            row = conn.execute(select(table.c.id).where(and_(
                table.c.organization_id == org_id, cond))).first()
            if not row:
                return False
            conn.execute(table.update().where(table.c.id == row[0]).values(archived_at=now_iso()))
            return True

    # -------------------------------------------------------------- comments
    def comment_create(self, org_id: str, viewer_id: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            irow = conn.execute(select(issue).where(and_(
                issue.c.organization_id == org_id,
                (issue.c.id == inp["issueId"]) | (issue.c.identifier == str(inp["issueId"]).upper())))).first()
            if not irow:
                return None
            irow = dict(irow._mapping)
            ts = now_iso()
            cid = new_id()
            conn.execute(comment.insert().values(
                id=cid, organization_id=org_id, issue_id=irow["id"], body=inp["body"],
                user_id=viewer_id, url=f"{irow.get('url')}#comment-{cid[:8]}",
                created_at=ts, updated_at=ts))
            return cid

    def comment_update(self, org_id: str, cid: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            row = conn.execute(select(comment.c.id).where(and_(
                comment.c.organization_id == org_id, comment.c.id == cid))).first()
            if not row:
                return None
            vals = {"updated_at": now_iso()}
            if "body" in inp:
                vals["body"] = inp["body"]
            conn.execute(comment.update().where(comment.c.id == cid).values(**vals))
            return cid

    def comment_delete(self, org_id: str, cid: str) -> bool:
        return self._soft_delete(comment, org_id, cid)

    # -------------------------------------------------------------- attachments
    def attachment_create(self, org_id: str, viewer_id: str, inp: dict) -> dict | None:
        with self.engine.begin() as conn:
            parsed_url = urlparse(inp["url"])
            if (
                parsed_url.scheme not in {"http", "https"}
                or not parsed_url.netloc
                or parsed_url.username
                or parsed_url.password
            ):
                raise InvalidReferenceError("url")
            irow = conn.execute(select(issue.c.id).where(and_(
                issue.c.organization_id == org_id,
                (issue.c.id == inp["issueId"])
                | (issue.c.identifier == str(inp["issueId"]).upper()),
            ))).first()
            if not irow:
                return None
            aid = new_id()
            created_at = now_iso()
            conn.execute(attachment.insert().values(
                id=aid,
                organization_id=org_id,
                issue_id=irow[0],
                creator_id=viewer_id,
                url=inp["url"],
                title=inp["title"],
                subtitle=inp.get("subtitle"),
                created_at=created_at,
            ))
            return {
                "id": aid,
                "url": inp["url"],
                "title": inp["title"],
                "subtitle": inp.get("subtitle"),
                "createdAt": created_at,
                "_issue_id": irow[0],
            }

    # -------------------------------------------------------------- labels
    def label_create(self, org_id: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            team_id = None
            if inp.get("teamId"):
                trow = conn.execute(select(team.c.id).where(and_(
                    team.c.organization_id == org_id,
                    (team.c.id == inp["teamId"]) | (team.c.key == str(inp["teamId"]).upper())))).first()
                if not trow:
                    raise InvalidReferenceError("teamId")
                team_id = trow[0]
            ts = now_iso()
            lid = new_id()
            conn.execute(issue_label.insert().values(
                id=lid, organization_id=org_id, team_id=team_id, name=inp["name"],
                color=inp.get("color"), description=inp.get("description"),
                created_at=ts, updated_at=ts))
            return lid

    def label_delete(self, org_id: str, lid: str) -> bool:
        return self._soft_delete(issue_label, org_id, lid)

    # -------------------------------------------------------------- projects
    def project_create(self, org_id: str, viewer_id: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            if lead_id := inp.get("leadId"):
                _require_org_reference(
                    conn, user, org_id, lead_id, "leadId",
                    user.c.active.is_(True),
                )
            team_ids = set(inp.get("teamIds") or [])
            if team_ids:
                found = set(
                    conn.execute(
                        select(team.c.id).where(
                            and_(
                                team.c.id.in_(team_ids),
                                team.c.organization_id == org_id,
                                team.c.archived_at.is_(None),
                            )
                        )
                    ).scalars()
                )
                if found != team_ids:
                    raise InvalidReferenceError("teamIds")
            ts = now_iso()
            pid = new_id()
            slug = _slug(inp["name"])
            url_key = _org_url_key(conn, org_id)
            conn.execute(project.insert().values(
                id=pid, organization_id=org_id, name=inp["name"],
                description=inp.get("description"), slug_id=slug,
                icon=inp.get("icon"), color=inp.get("color"),
                state=inp.get("state", "backlog"), progress=0,
                lead_id=inp.get("leadId"), creator_id=viewer_id,
                start_date=inp.get("startDate"), target_date=inp.get("targetDate"),
                url=entity_url(url_key, "project", slug),
                created_at=ts, updated_at=ts))
            conn.execute(project_member.insert().values(project_id=pid, user_id=viewer_id))
            for team_id in team_ids:
                conn.execute(project_team.insert().values(project_id=pid, team_id=team_id))
            return pid

    def project_update(self, org_id: str, pid: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            row = conn.execute(select(project.c.id).where(and_(
                project.c.organization_id == org_id, project.c.id == pid))).first()
            if not row:
                return None
            if lead_id := inp.get("leadId"):
                _require_org_reference(
                    conn, user, org_id, lead_id, "leadId",
                    user.c.active.is_(True),
                )
            vals = {"updated_at": now_iso()}
            m = {"name": "name", "description": "description", "leadId": "lead_id",
                 "state": "state", "color": "color", "icon": "icon",
                 "startDate": "start_date", "targetDate": "target_date"}
            for k, col in m.items():
                if k in inp:
                    vals[col] = inp[k]
            conn.execute(project.update().where(project.c.id == pid).values(**vals))
            return pid

    def project_archive(self, org_id: str, pid: str) -> bool:
        return self._soft_delete(project, org_id, pid)
