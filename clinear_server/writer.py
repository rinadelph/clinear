"""Deprecated alias for :mod:`cliniar_server.writer`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.writer")
sys.modules[__name__] = _impl
