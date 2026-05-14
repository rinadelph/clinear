"""MCP server for clinear.

This package is **optional**. Install with:

    pip install 'clinear[mcp]'

The server exposes:
  - 1 tool:       clinear_guide(topic) — teaches the agent how to use clinear
  - 7 resources:  read-only Linear context (me, issue, team, project, cycle, ...)
  - 6 prompts:    workflow templates (triage, daily-standup, hand-off, ...)

It does NOT expose mutation tools by design. Mutations are performed via the
`clinear` CLI in a shell — that's the supported interface and the agent is
reinforced to use Bash for any write operation.

Entry point: `clinear-mcp` (console script). See `server.main()`.
"""
from clinear.mcp.server import main

__all__ = ["main"]
