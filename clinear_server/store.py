"""Deprecated alias for :mod:`cliniar_server.store`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.store")
sys.modules[__name__] = _impl
