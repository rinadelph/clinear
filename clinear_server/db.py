"""Deprecated alias for :mod:`cliniar_server.db`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.db")
sys.modules[__name__] = _impl
