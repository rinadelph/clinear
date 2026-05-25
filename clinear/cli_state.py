"""Shared CLI state — populated by the root callback, read by subcommands.

Typer doesn't have a great way to share state across commands without going
through Context. We use a small module-level container to keep subcommands
clean.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from clinear.client import LinearClient
from clinear.config import Config
from clinear.models.enums import OutputFormat


@dataclass
class CLIState:
    """Mutable per-invocation state."""

    token: str = ""
    config: Config = field(default_factory=Config)
    output: OutputFormat = OutputFormat.HUMAN
    verbose: bool = False
    quiet: bool = False
    no_color: bool = False
    dry_run: bool = False
    timeout: float = 30.0
    account_name: str = ""  # active account name for context display


_state = CLIState()


def get_state() -> CLIState:
    return _state


def set_state(state: CLIState) -> None:
    global _state
    _state = state


def build_client(state: CLIState | None = None) -> LinearClient:
    """Construct a LinearClient configured from the current CLI state."""
    s = state or _state
    return LinearClient(
        token=s.token,
        timeout=s.timeout,
        verbose=s.verbose,
    )
