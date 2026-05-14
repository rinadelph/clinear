"""Root CLI entrypoint.

Defines the top-level Typer app, global flags, error handling, and
registers all subcommand modules.
"""

from __future__ import annotations

import sys
from typing import Optional

import typer

from clinear import __version__
from clinear.cli_state import CLIState, set_state
from clinear.commands.auth_cmd import auth_app, me_app
from clinear.commands.comment import comment_app
from clinear.commands.cycle import cycle_app
from clinear.commands.init import init_app
from clinear.commands.issue import issue_app
from clinear.commands.label import label_app
from clinear.commands.project import project_app
from clinear.commands.raw import raw_app
from clinear.commands.team import team_app
from clinear.config import load_config, resolve_token
from clinear.errors import ClinearError
from clinear.models.enums import OutputFormat
from clinear.output import emit_error


app = typer.Typer(
    name="clinear",
    help="Type-safe Linear CLI built on Pydantic v2 + httpx + Typer",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


def _version_cb(value: bool) -> None:
    if value:
        typer.echo(f"clinear {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    token: Optional[str] = typer.Option(None, "--token", envvar=None, help="Linear API token (overrides $LINEAR_TOKEN)"),
    output: OutputFormat = typer.Option(OutputFormat.HUMAN, "--output", "-o", help="Output format"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Print GraphQL operations to stderr"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI colors"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print mutations without executing"),
    timeout: float = typer.Option(30.0, "--timeout", help="HTTP timeout in seconds"),
    version: Optional[bool] = typer.Option(
        None, "--version", callback=_version_cb, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """Global flags applied before any subcommand."""
    # Resolve config + token
    config = load_config()

    # Token resolution: only required for commands that hit the API.
    # We defer the actual AuthError to first API call to allow `--help` etc.
    try:
        resolved_token = resolve_token(token, config)
    except ClinearError:
        resolved_token = ""

    state = CLIState(
        token=resolved_token,
        config=config,
        output=output,
        verbose=verbose,
        quiet=quiet,
        no_color=no_color,
        dry_run=dry_run,
        timeout=timeout,
    )
    set_state(state)


# Register subcommands
app.add_typer(me_app, name="me")
app.add_typer(auth_app, name="auth")
app.add_typer(init_app, name="init")
app.add_typer(team_app, name="team")
app.add_typer(issue_app, name="issue")
app.add_typer(project_app, name="project")
app.add_typer(cycle_app, name="cycle")
app.add_typer(comment_app, name="comment")
app.add_typer(label_app, name="label")
app.add_typer(raw_app, name="raw")


def _entry() -> None:
    """Wrap typer_app() with consistent error handling and exit codes."""
    try:
        typer_app()
    except ClinearError as e:
        from clinear.cli_state import get_state
        state = get_state()
        if state.output == OutputFormat.JSON:
            import json as _json
            print(_json.dumps(e.to_dict(), indent=2), file=sys.stderr)
        else:
            emit_error(e.message, hint=e.hint)
        sys.exit(int(e.exit_code))
    except KeyboardInterrupt:
        emit_error("Interrupted")
        sys.exit(130)


# Public callable for `clinear` script entry point in pyproject.toml.
# Renamed to `typer_app` internally so the wrapper is what pip-installed
# `clinear` actually invokes.
typer_app = app
app = _entry  # type: ignore[assignment]


if __name__ == "__main__":
    _entry()
