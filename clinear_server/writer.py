"""Write operations — mutations with the per-team identifier counter, derived
fields, and state-transition timestamps. Transaction-safe (single writer under
SQLite WAL; counter bumped inside the same transaction as the insert).
"""
from __future__ import annotations

from sqlalchemy import and_, select
from sqlalchemy.engine import Engine

from clinear_server.db import (
    PRIORITY_LABELS,
    comment,
    issue,
    issue_label,
    issue_label_link,
    new_id,
    now_iso,
    organization,
    project,
    project_member,
    team,
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
            n = (trow.get("issue_counter") or 0) + 1
            conn.execute(team.update().where(team.c.id == tid).values(issue_counter=n))
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
                url=f"https://linear.app/{url_key}/issue/{ident}",
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
            iid = dict(row._mapping)["id"]
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

    # -------------------------------------------------------------- labels
    def label_create(self, org_id: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            team_id = None
            if inp.get("teamId"):
                trow = conn.execute(select(team.c.id).where(and_(
                    team.c.organization_id == org_id,
                    (team.c.id == inp["teamId"]) | (team.c.key == str(inp["teamId"]).upper())))).first()
                team_id = trow[0] if trow else None
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
                url=f"https://linear.app/{url_key}/project/{slug}",
                created_at=ts, updated_at=ts))
            conn.execute(project_member.insert().values(project_id=pid, user_id=viewer_id))
            return pid

    def project_update(self, org_id: str, pid: str, inp: dict) -> str | None:
        with self.engine.begin() as conn:
            row = conn.execute(select(project.c.id).where(and_(
                project.c.organization_id == org_id, project.c.id == pid))).first()
            if not row:
                return None
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
