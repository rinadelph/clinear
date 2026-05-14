"""clinear — Type-safe Linear CLI built on Pydantic v2."""

from pathlib import Path


def _read_version() -> str:
    """Read version from VERSION file at the repo root.

    Falls back to a hardcoded string if the file is missing (e.g. when
    installed from a wheel where VERSION isn't packaged).
    """
    try:
        version_file = Path(__file__).resolve().parent.parent / "VERSION"
        if version_file.is_file():
            return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    return "0.2.0"


__version__ = _read_version()
__all__ = ["__version__"]
