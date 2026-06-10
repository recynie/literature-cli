from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lit import config as config_module
from lit.main import app


def _write_toml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_find_project_config_dir_walks_up_from_cwd(tmp_path, monkeypatch):
    project_root = tmp_path / "workspace"
    nested = project_root / "papers" / "notes"
    nested.mkdir(parents=True)
    (project_root / ".litcli").mkdir()

    monkeypatch.chdir(nested)

    assert config_module.find_project_config_dir() == project_root / ".litcli"


def test_load_config_files_prefers_project_over_user(tmp_path, monkeypatch):
    user_dir = tmp_path / "user-config"
    project_root = tmp_path / "workspace"
    nested = project_root / "subdir"
    nested.mkdir(parents=True)

    _write_toml(
        user_dir / "config.toml",
        "[openai]\nmodel = \"user-model\"\n[litcli]\ndata_dir = \"/tmp/user-data\"\n",
    )
    _write_toml(
        project_root / ".litcli" / "config.toml",
        "[openai]\nmodel = \"project-model\"\n[litcli]\ndata_dir = \"/tmp/project-data\"\n",
    )

    monkeypatch.setattr(config_module, "USER_CONFIG_DIR", user_dir)
    monkeypatch.chdir(nested)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("LITCLI_DATA_DIR", raising=False)

    config_module.load_config_files()

    assert config_module.os.environ["OPENAI_MODEL"] == "project-model"
    assert config_module.os.environ["LITCLI_DATA_DIR"] == "/tmp/project-data"


def test_load_config_files_falls_back_to_user_config(tmp_path, monkeypatch):
    user_dir = tmp_path / "user-config"
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    _write_toml(
        user_dir / "auth.toml",
        "[openai]\napi_key = \"user-key\"\n",
    )

    monkeypatch.setattr(config_module, "USER_CONFIG_DIR", user_dir)
    monkeypatch.chdir(workspace)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    config_module.load_config_files()

    assert config_module.os.environ["OPENAI_API_KEY"] == "user-key"


def test_load_config_files_preserves_existing_environment(tmp_path, monkeypatch):
    user_dir = tmp_path / "user-config"
    project_root = tmp_path / "workspace"
    project_root.mkdir()

    _write_toml(
        user_dir / "config.toml",
        "[openai]\nmodel = \"user-model\"\n",
    )
    _write_toml(
        project_root / ".litcli" / "config.toml",
        "[openai]\nmodel = \"project-model\"\n",
    )

    monkeypatch.setattr(config_module, "USER_CONFIG_DIR", user_dir)
    monkeypatch.chdir(project_root)
    monkeypatch.setenv("OPENAI_MODEL", "env-model")

    config_module.load_config_files()

    assert config_module.os.environ["OPENAI_MODEL"] == "env-model"


def test_main_config_command_skips_database_init(tmp_path, monkeypatch):
    runner = CliRunner()
    project_root = tmp_path / "workspace"
    config_dir = project_root / ".litcli"
    config_dir.mkdir(parents=True)
    _write_toml(config_dir / "config.toml", "[openai]\nmodel = \"project-model\"\n")

    monkeypatch.chdir(project_root)
    monkeypatch.setattr("lit.main.init_database", lambda db_path: (_ for _ in ()).throw(AssertionError("init_database should not run")))

    result = runner.invoke(app, ["config", "--json"])

    assert result.exit_code == 0
    assert '"project_config_dir":' in result.output
