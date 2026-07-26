"""Deprecated module/CLI alias for :mod:`cliniar_server.cli`."""

import sys
from importlib import import_module

_impl = import_module("cliniar_server.cli")

if __name__ == "__main__":
    _impl.main()
else:
    sys.modules[__name__] = _impl
