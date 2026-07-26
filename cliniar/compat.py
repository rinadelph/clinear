"""One-release compatibility helpers for the Clinear → Cliniar rename."""

from __future__ import annotations

import os
import warnings


def warn_legacy(legacy: str, replacement: str) -> None:
    warnings.warn(
        f"{legacy} is deprecated; use {replacement}.",
        DeprecationWarning,
        stacklevel=3,
    )


def env_value(
    canonical: str,
    legacy: str,
    default: str | None = None,
) -> str | None:
    """Read a canonical environment variable, then its legacy alias."""
    if canonical in os.environ:
        return os.environ[canonical]
    if legacy in os.environ:
        warn_legacy(legacy, canonical)
        return os.environ[legacy]
    return default
