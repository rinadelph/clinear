"""Config loading and validation.

Lookup order:
  1. $CLINEAR_CONFIG env var (absolute path)
  2. $XDG_CONFIG_HOME/clinear/config.toml
  3. ~/.config/clinear/config.toml

Token resolution order:
  1. --token CLI flag (passed in)
  2. $LINEAR_TOKEN env var
  3. config.toml [auth].token (discouraged)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover
    import tomli as tomllib

from clinear.errors import AuthError, UsageError


class AuthConfig(BaseModel):
    """Authentication configuration."""

    model_config = ConfigDict(extra="forbid")

    token: str | None = None
    token_env: str = "LINEAR_TOKEN"


class DefaultsConfig(BaseModel):
    """Default values applied to commands."""

    model_config = ConfigDict(extra="forbid")

    team: str | None = None
    output: str = "human"
    editor: str | None = None


class DisplayConfig(BaseModel):
    """Display preferences."""

    model_config = ConfigDict(extra="forbid")

    color: bool = True
    table_max_width: int = 120
    truncate_descriptions: int = 80


class Config(BaseModel):
    """Top-level clinear configuration."""

    model_config = ConfigDict(extra="forbid")

    auth: AuthConfig = Field(default_factory=AuthConfig)
    defaults: DefaultsConfig = Field(default_factory=DefaultsConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    aliases: dict[str, str] = Field(default_factory=dict)
    views: dict[str, dict[str, Any]] = Field(default_factory=dict)


def config_path() -> Path:
    """Resolve config file location."""
    if env_path := os.environ.get("CLINEAR_CONFIG"):
        return Path(env_path).expanduser().resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "clinear" / "config.toml"


def load_config(path: Path | None = None) -> Config:
    """Load and validate config.toml. Returns defaults if file missing."""
    p = path or config_path()
    if not p.exists():
        return Config()
    try:
        with open(p, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise UsageError(
            f"Invalid TOML in config file: {e}",
            hint=f"Edit {p} to fix syntax",
        ) from e
    try:
        return Config(**data)
    except Exception as e:
        raise UsageError(
            f"Invalid config: {e}",
            hint=f"See docs/DESIGN.md for the config schema",
        ) from e


def resolve_token(
    cli_token: str | None,
    config: Config,
) -> str:
    """Resolve the Linear API token using precedence rules.

    Order: --token > $LINEAR_TOKEN > config.auth.token
    """
    if cli_token:
        return cli_token
    env_var = config.auth.token_env or "LINEAR_TOKEN"
    if env_token := os.environ.get(env_var):
        return env_token
    if config.auth.token:
        return config.auth.token
    raise AuthError(
        "No Linear API token found",
        hint=(
            f"Set ${env_var}, pass --token, or configure auth.token in "
            f"{config_path()}"
        ),
    )


def redact_token(token: str) -> str:
    """Show only the last 4 chars of a token for logging."""
    if len(token) <= 8:
        return "***"
    return f"{token[:8]}…{token[-4:]}"
