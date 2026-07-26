"""Contracts for the one-release Clinear → Cliniar compatibility bridge."""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from cliniar.config import Config, config_path
from cliniar.memory_board import memory_path
from cliniar_server.db import app_url, db_path_for, resolve_database_target


def test_legacy_imports_resolve_to_canonical_modules() -> None:
    canonical = importlib.import_module("cliniar.config")
    legacy = importlib.import_module("clinear.config")

    assert legacy is canonical
    assert legacy.Config is Config
    assert importlib.import_module("clinear.client") is importlib.import_module(
        "cliniar.client"
    )
    canonical_db = importlib.import_module("cliniar_server.db")
    legacy_db = importlib.import_module("clinear_server.db")
    assert legacy_db is canonical_db
    assert legacy_db.metadata is canonical_db.metadata


@pytest.mark.parametrize(
    "module",
    ["cliniar_server.cli", "clinear_server.cli"],
)
def test_server_module_entry_points(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", module, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "cliniar-serve 0.7.0"


@pytest.mark.parametrize(
    "submodule",
    ["app", "cli", "db", "resolvers", "store", "writer"],
)
@pytest.mark.parametrize("legacy_first", [False, True])
def test_server_submodules_share_identity_in_both_import_orders(
    submodule: str,
    legacy_first: bool,
) -> None:
    first = "clinear_server" if legacy_first else "cliniar_server"
    second = "cliniar_server" if legacy_first else "clinear_server"
    code = f"""
import importlib
first = importlib.import_module({first!r} + '.{submodule}')
second = importlib.import_module({second!r} + '.{submodule}')
assert first is second
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_legacy_server_base_import_is_lazy() -> None:
    code = """
import sys
import clinear_server
assert not any(
    name.startswith(('clinear_server.', 'cliniar_server.'))
    for name in sys.modules
)
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_config_environment_prefers_cliniar(monkeypatch, tmp_path) -> None:
    canonical = tmp_path / "canonical.toml"
    legacy = tmp_path / "legacy.toml"
    monkeypatch.setenv("CLINIAR_CONFIG", str(canonical))
    monkeypatch.setenv("CLINEAR_CONFIG", str(legacy))

    assert config_path() == canonical


def test_config_legacy_environment_fallback_warns(monkeypatch, tmp_path) -> None:
    legacy = tmp_path / "legacy.toml"
    monkeypatch.delenv("CLINIAR_CONFIG", raising=False)
    monkeypatch.setenv("CLINEAR_CONFIG", str(legacy))

    with pytest.warns(DeprecationWarning, match="CLINEAR_CONFIG"):
        assert config_path() == legacy


def test_config_path_prefers_existing_canonical_then_legacy(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("CLINIAR_CONFIG", raising=False)
    monkeypatch.delenv("CLINEAR_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    canonical = tmp_path / "cliniar" / "config.toml"
    legacy = tmp_path / "clinear" / "config.toml"
    legacy.parent.mkdir()
    legacy.write_text("[accounts]\n")

    with pytest.warns(DeprecationWarning, match="clinear"):
        assert config_path() == legacy

    canonical.parent.mkdir()
    canonical.write_text("[accounts]\n")
    assert config_path() == canonical


def test_memory_path_falls_back_without_moving_data(
    monkeypatch,
    tmp_path,
) -> None:
    legacy = tmp_path / ".clinear" / "memory.yaml"
    legacy.parent.mkdir()
    legacy.write_text("version: 1\n")
    monkeypatch.setattr("cliniar.memory_board._find_git_root", lambda _start: tmp_path)

    with pytest.warns(DeprecationWarning, match=r"\.clinear"):
        assert memory_path(tmp_path) == legacy
    assert legacy.exists()
    assert not (tmp_path / ".cliniar" / "memory.yaml").exists()


def test_database_path_prefers_existing_canonical_then_legacy(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    legacy = tmp_path / "clinear" / "shared.db"
    legacy.parent.mkdir()
    legacy.touch()

    with pytest.warns(DeprecationWarning, match="clinear"):
        assert db_path_for("shared") == legacy

    canonical = tmp_path / "cliniar" / "shared.db"
    canonical.parent.mkdir()
    canonical.touch()
    assert db_path_for("shared") == canonical


def test_server_environment_prefers_cliniar_and_supports_legacy(
    monkeypatch,
) -> None:
    monkeypatch.setenv("CLINEAR_DATABASE_URL", "sqlite:///legacy.db")
    monkeypatch.setenv("CLINIAR_DATABASE_URL", "sqlite:///canonical.db")
    assert resolve_database_target() == "sqlite:///canonical.db"

    monkeypatch.delenv("CLINIAR_DATABASE_URL")
    with pytest.warns(DeprecationWarning, match="CLINEAR_DATABASE_URL"):
        assert resolve_database_target() == "sqlite:///legacy.db"

    monkeypatch.setenv("CLINEAR_APP_URL", "https://legacy.example.test")
    monkeypatch.setenv("CLINIAR_APP_URL", "https://canonical.example.test/")
    assert app_url() == "https://canonical.example.test"

    monkeypatch.delenv("CLINIAR_APP_URL")
    with pytest.warns(DeprecationWarning, match="CLINEAR_APP_URL"):
        assert app_url() == "https://legacy.example.test"


def test_new_database_defaults_to_cliniar_directory(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    assert db_path_for("new") == Path(tmp_path) / "cliniar" / "new.db"


def test_mcp_registers_canonical_and_legacy_names() -> None:
    pytest.importorskip("mcp")
    from cliniar.mcp.content import ClinearGuide, CliniarGuide
    from cliniar.mcp.server import _build_server

    server = _build_server()
    assert set(server._tool_manager._tools) == {
        "cliniar_guide",
        "clinear_guide",
    }
    resource_uris = {
        str(uri) for uri in server._resource_manager._resources
    } | {
        str(uri) for uri in server._resource_manager._templates
    }
    canonical = {uri for uri in resource_uris if uri.startswith("cliniar://")}
    legacy = {uri for uri in resource_uris if uri.startswith("clinear://")}
    assert len(canonical) == 7
    assert {uri.replace("clinear://", "cliniar://", 1) for uri in legacy} == canonical
    assert ClinearGuide is CliniarGuide
