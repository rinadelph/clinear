"""cliniar-mcp — Model Context Protocol server for the cliniar CLI.

Run via the `cliniar-mcp` console script (registered in pyproject.toml).
Uses the official `mcp` Python SDK with FastMCP convenience layer.

Exposes:
  - 1 tool      : cliniar_guide(topic) — teaches the agent how to use cliniar
  - 7 resources : read-only Linear context
  - 6 prompts   : workflow templates

By design the server does NOT expose mutation tools. Mutations happen via the
`cliniar` CLI in a shell — the tool's response payload and the prompt bodies
both carry a behavioral reminder reinforcing this rule.

STDIO TRANSPORT NOTE: When running on stdio (the default), stdout is reserved
for the JSON-RPC stream. ALL logging must go to stderr. We configure that at
the top of this module before any other import that might log.
"""
from __future__ import annotations

import logging
import sys

# Route logging to stderr BEFORE importing anything that might log.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="[cliniar-mcp] %(levelname)s %(message)s",
)

# Module-level imports for types used in tool/resource/prompt signatures.
# The MCP SDK uses inspect.signature(..., eval_str=True) which resolves
# stringified annotations against MODULE globals — so Topic/CliniarGuide
# must be importable at module level, not just inside _build_server().
from . import prompts as _prompts  # noqa: E402
from . import resources as _resources  # noqa: E402
from .content import CliniarGuide, Topic, load_topic  # noqa: E402


def main() -> None:
    """Entry point for the `cliniar-mcp` console script.

    Lazy-imports the MCP SDK so that `import cliniar` (without the [mcp] extra)
    does not fail at the top of this module. If the dep is missing, print a
    friendly install hint to stderr and exit 2.
    """
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError:
        sys.stderr.write(
            "cliniar-mcp requires the [mcp] extra.\n"
            "Install with:\n"
            "  pip install 'cliniar[mcp]'\n"
        )
        sys.exit(2)

    _build_server().run(transport="stdio")


def _build_server():
    """Wire tools, resources, and prompts onto a FastMCP server."""
    from mcp.server.fastmcp import FastMCP

    from cliniar import __version__

    mcp = FastMCP(
        "cliniar",
        instructions=(
            "Use this server to learn how to drive Linear from a shell using "
            "the `cliniar` CLI. Call `cliniar_guide(topic)` BEFORE attempting "
            "any Linear-related task. Read resources for read-only context. "
            "Read prompts for multi-step workflow templates. Perform all "
            "mutations via `cliniar <command>` invoked through the Bash tool."
        ),
    )

    # ------------------------------------------------------------------
    # Tool — single teaching tool
    # ------------------------------------------------------------------
    @mcp.tool()
    def cliniar_guide(topic: Topic = Topic.OVERVIEW) -> CliniarGuide:
        """Return a guide on how to use the `cliniar` CLI for a given topic.

        ALWAYS call this BEFORE any Linear-related task. Then execute cliniar
        commands via the Bash tool. Do NOT write Python wrappers around the
        Linear GraphQL API — cliniar is the supported interface.

        Available topics:
          - overview         — when to reach for cliniar; behavioral rules
          - commands         — full command tree with examples
          - workflows        — common multi-step patterns
          - filters          — `issue list` filter DSL
          - output-formats   — when to use --output json vs human vs ids
          - examples         — copy-pasteable recipes
        """
        return load_topic(topic)

    @mcp.tool()
    def clinear_guide(topic: Topic = Topic.OVERVIEW) -> CliniarGuide:
        """Deprecated alias for `cliniar_guide` during the v0.7 bridge."""
        return load_topic(topic)

    # ------------------------------------------------------------------
    # Resources — read-only Linear context
    # ------------------------------------------------------------------
    @mcp.resource(
        "clinear://me",
        name="legacy-viewer",
        description="Deprecated alias for cliniar://me.",
    )
    @mcp.resource("cliniar://me", name="viewer", description="Currently-authenticated Linear user.")
    async def res_me() -> str:
        return await _resources.viewer()

    @mcp.resource(
        "clinear://issue/{id}",
        name="legacy-issue",
        description="Deprecated alias for cliniar://issue/{id}.",
    )
    @mcp.resource(
        "cliniar://issue/{id}",
        name="issue",
        description="Full Linear issue by identifier (e.g. ENG-35), including comments, labels, subscribers.",
    )
    async def res_issue(id: str) -> str:
        return await _resources.issue(id)

    @mcp.resource(
        "clinear://team/{key}",
        name="legacy-team",
        description="Deprecated alias for cliniar://team/{key}.",
    )
    @mcp.resource(
        "cliniar://team/{key}",
        name="team",
        description="Team detail + workflow states + members for a team key (e.g. ENG).",
    )
    async def res_team(key: str) -> str:
        return await _resources.team(key)

    @mcp.resource(
        "clinear://project/{id_or_slug}",
        name="legacy-project",
        description="Deprecated alias for cliniar://project/{id_or_slug}.",
    )
    @mcp.resource(
        "cliniar://project/{id_or_slug}",
        name="project",
        description="Linear project by id or slug, including lead, creator, members.",
    )
    async def res_project(id_or_slug: str) -> str:
        return await _resources.project(id_or_slug)

    @mcp.resource(
        "clinear://cycle/current/{team_key}",
        name="legacy-cycle-current",
        description="Deprecated alias for cliniar://cycle/current/{team_key}.",
    )
    @mcp.resource(
        "cliniar://cycle/current/{team_key}",
        name="cycle-current",
        description="Active cycle for a team. Returns {active_cycle: null} when none.",
    )
    async def res_cycle(team_key: str) -> str:
        return await _resources.cycle_current(team_key)

    @mcp.resource(
        "clinear://issues/mine",
        name="legacy-issues-mine",
        description="Deprecated alias for cliniar://issues/mine.",
    )
    @mcp.resource(
        "cliniar://issues/mine",
        name="issues-mine",
        description="Open issues assigned to the viewer (Todo + In Progress).",
    )
    async def res_issues_mine() -> str:
        return await _resources.issues_mine()

    @mcp.resource(
        "clinear://issues/team/{team_key}",
        name="legacy-issues-team",
        description="Deprecated alias for cliniar://issues/team/{team_key}.",
    )
    @mcp.resource(
        "cliniar://issues/team/{team_key}",
        name="issues-team",
        description="Open issues for a team (Todo + In Progress).",
    )
    async def res_issues_team(team_key: str) -> str:
        return await _resources.issues_team(team_key)

    # ------------------------------------------------------------------
    # Prompts — workflow templates
    # ------------------------------------------------------------------
    @mcp.prompt(description="Triage unassigned issues for a team — step-by-step shell commands.")
    def triage(team_key: str) -> str:
        return _prompts.triage(team_key)

    @mcp.prompt(description="Generate a daily standup report from viewer's recent activity.")
    def daily_standup() -> str:
        return _prompts.daily_standup()

    @mcp.prompt(description="Create an issue from an error trace, with duplicate-search step.")
    def create_from_error(error_text: str, team_key: str, priority: int = 3) -> str:
        return _prompts.create_from_error(error_text, team_key, priority)

    @mcp.prompt(description="Hand off an issue to another teammate in 3 commands.")
    def hand_off(issue_id: str, to_user: str, note: str = "") -> str:
        return _prompts.hand_off(issue_id, to_user, note)

    @mcp.prompt(description="Review the current cycle for a team — done/in-progress/blockers/stale.")
    def cycle_review(team_key: str) -> str:
        return _prompts.cycle_review(team_key)

    @mcp.prompt(description="Deep-dive investigation of a single issue.")
    def issue_investigate(issue_id: str) -> str:
        return _prompts.issue_investigate(issue_id)

    logging.info(
        "cliniar-mcp v%s ready (tools=2, resources=14, prompts=6)",
        __version__,
    )
    return mcp


if __name__ == "__main__":
    main()
