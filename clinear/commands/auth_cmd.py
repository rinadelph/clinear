"""`clinear me` and `clinear auth ...` commands."""

from __future__ import annotations

import asyncio

import typer

from clinear.auth import get_viewer
from clinear.cli_state import build_client, get_state
from clinear.models.enums import OutputFormat
from clinear.output import render

me_app = typer.Typer(help="Show the currently-authenticated Linear user")
auth_app = typer.Typer(help="Authentication operations")


@me_app.callback(invoke_without_command=True)
def me(ctx: typer.Context) -> None:
    """Show the currently-authenticated user (alias for `auth status`)."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_run_me())


@auth_app.command("status")
def status() -> None:
    """Show the currently-authenticated user and token source."""
    asyncio.run(_run_me())


@auth_app.command("whoami")
def whoami() -> None:
    """Alias of `auth status`."""
    asyncio.run(_run_me())


async def _run_me() -> None:
    state = get_state()
    async with build_client(state) as client:
        viewer = await get_viewer(client)
        render(viewer, fmt=state.output, title="Viewer")
