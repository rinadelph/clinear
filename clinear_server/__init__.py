"""Compatibility package for the renamed :mod:`cliniar_server` package."""

from importlib import import_module
from typing import Any

_impl = import_module("cliniar_server")

# Server submodules are represented by tiny lazy shim files in this package.
# This keeps base imports optional-dependency-safe while ensuring normal legacy
# imports replace themselves with the canonical module object.

__version__ = _impl.__version__


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)
