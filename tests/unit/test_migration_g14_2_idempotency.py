from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_migration(relative_path: str, module_name: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load migration module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeInspector:
    def __init__(self, has_table: bool, columns: list[str], indexes: list[str] | None = None) -> None:
        self._has_table = has_table
        self._columns = columns
        self._indexes = indexes or []

    def has_table(self, _table_name: str) -> bool:
        return self._has_table

    def get_columns(self, _table_name: str) -> list[dict[str, Any]]:
        return [{"name": column} for column in self._columns]

    def get_indexes(self, _table_name: str) -> list[dict[str, Any]]:
        return [{"name": index} for index in self._indexes]


class _FakeOp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def get_bind(self) -> object:
        return object()

    def execute(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("execute", args, kwargs))

    def add_column(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("add_column", args, kwargs))

    def alter_column(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("alter_column", args, kwargs))

    def drop_column(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("drop_column", args, kwargs))

    def create_table(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("create_table", args, kwargs))

    def create_index(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("create_index", args, kwargs))

    def drop_index(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("drop_index", args, kwargs))

    def drop_table(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(("drop_table", args, kwargs))


def test_tool_examples_upgrade_noops_when_registry_table_missing(monkeypatch) -> None:
    module = _load_migration(
        "migrations/versions/g14_2_01_tool_input_examples.py",
        "g14_2_01_tool_examples_test",
    )
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _FakeInspector(False, []))

    module.upgrade()

    assert fake_op.calls == []


def test_schema_json_upgrade_skips_add_when_column_already_exists(monkeypatch) -> None:
    module = _load_migration(
        "migrations/versions/g14_2_03_schema_json.py",
        "g14_2_03_schema_json_test_existing",
    )
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _FakeInspector(True, ["tool_id", "metadata_json", "schema_json"]),
    )

    module.upgrade()

    call_names = [name for name, _, _ in fake_op.calls]
    assert "add_column" not in call_names
    assert "execute" in call_names
    assert "alter_column" in call_names


def test_schema_json_upgrade_noops_when_registry_table_missing(monkeypatch) -> None:
    module = _load_migration(
        "migrations/versions/g14_2_03_schema_json.py",
        "g14_2_03_schema_json_test_missing",
    )
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(module.sa, "inspect", lambda _bind: _FakeInspector(False, []))

    module.upgrade()

    assert fake_op.calls == []


def test_sandbox_runs_upgrade_skips_duplicate_type_and_existing_table(monkeypatch) -> None:
    module = _load_migration(
        "migrations/versions/p15_01_sandbox_runs.py",
        "p15_01_sandbox_runs_test_existing",
    )
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _FakeInspector(
            True,
            [],
            ["ix_sandbox_runs_run_id", "idx_sandbox_runs_verdict", "idx_sandbox_runs_fingerprint"],
        ),
    )

    module.upgrade()

    call_names = [name for name, _, _ in fake_op.calls]
    assert "create_table" not in call_names
    assert "create_index" not in call_names


def test_remedy_cache_upgrade_skips_create_when_table_and_indexes_exist(monkeypatch) -> None:
    module = _load_migration(
        "migrations/versions/p15_02_remedy_template_cache.py",
        "p15_02_remedy_template_cache_test_existing",
    )
    fake_op = _FakeOp()

    monkeypatch.setattr(module, "op", fake_op)
    monkeypatch.setattr(
        module.sa,
        "inspect",
        lambda _bind: _FakeInspector(
            True,
            [],
            [
                "ix_remedy_template_cache_template_id",
                "ix_remedy_template_cache_fingerprint",
                "ix_remedy_template_cache_expires_at",
                "idx_remedy_fingerprint_conf",
                "idx_remedy_last_applied",
            ],
        ),
    )

    module.upgrade()

    call_names = [name for name, _, _ in fake_op.calls]
    assert "create_table" not in call_names
    assert "create_index" not in call_names
