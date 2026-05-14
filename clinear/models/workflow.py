"""Workflow state model.

A workflow state is a team-defined column like "Todo", "In Progress", "Done".
Each maps to a broader StateType (backlog / started / completed / etc.).
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from clinear.models.base import Timestamped


class WorkflowStateType(str, Enum):
    """Linear's six built-in workflow state categories."""

    TRIAGE = "triage"
    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class WorkflowState(Timestamped):
    """A team's workflow state (e.g. 'Todo', 'In Progress', 'Done')."""

    id: str
    name: str
    color: str | None = None
    description: str | None = None
    position: float | None = None
    type: WorkflowStateType
    team_id: str | None = Field(alias="teamId", default=None)
