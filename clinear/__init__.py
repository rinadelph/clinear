"""Compatibility package for the renamed :mod:`cliniar` package."""

import pkgutil
import sys
from importlib import import_module
from typing import Any

_impl = import_module("cliniar")

# Alias every shipped canonical module to its legacy name so Python never loads
# one source file twice under two package identities.
for module_info in pkgutil.walk_packages(_impl.__path__, prefix="cliniar."):
    module = import_module(module_info.name)
    legacy_name = module_info.name.replace("cliniar.", "clinear.", 1)
    sys.modules.setdefault(legacy_name, module)

__all__ = _impl.__all__
__version__ = _impl.__version__


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)
