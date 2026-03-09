import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "sqlite-paper-fastmcp-server.py"
SCHEMA_PATH = REPO_ROOT / "create_sources_db.sql"


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "test_sources.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()
    return db_path


def _load_server_module(db_path: Path, monkeypatch: pytest.MonkeyPatch):
    module_name = "sqlite_paper_fastmcp_server_test"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    sys.modules.pop(module_name, None)
    for name in list(sys.modules):
        if name == "sqlite_lit_server" or name.startswith("sqlite_lit_server."):
            sys.modules.pop(name, None)

    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def load_server_module(monkeypatch: pytest.MonkeyPatch):
    def loader(db_path: Path):
        return _load_server_module(db_path, monkeypatch)

    return loader


@pytest.fixture
def server_module(temp_db: Path, monkeypatch: pytest.MonkeyPatch):
    return _load_server_module(temp_db, monkeypatch)
