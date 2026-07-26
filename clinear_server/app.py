"""Deprecated alias for :mod:`cliniar_server.app`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.app")
sys.modules[__name__] = _impl
