"""Deprecated alias for :mod:`cliniar_server.resolvers`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.resolvers")
sys.modules[__name__] = _impl
