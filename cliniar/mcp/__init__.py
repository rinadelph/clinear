"""MCP server for Cliniar.

This package is **optional**. Install with:

    pip install 'cliniar[mcp]'

The server exposes:
  - 1 tool:       cliniar_guide(topic)
  - 7 resources:  read-only workspace context
  - 6 prompts:    workflow templates (triage, daily-standup, hand-off, ...)

It does NOT expose mutation tools by design. Mutations are performed via the
`cliniar` CLI in a shell — that's the supported interface and the agent is
reinforced to use Bash for any write operation.

Entry point: `cliniar-mcp` (console script). See `server.main()`.
"""


def main() -> None:
    """Run the MCP server without importing it during package initialization."""
    from .server import main as server_main

    server_main()


__all__ = ["main"]
