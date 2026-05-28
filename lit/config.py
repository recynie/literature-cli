"""Configuration loading for LiteratureCLI.

Two TOML files are supported:
  config.toml  — shareable settings (model, base_url, data_dir, …)
  auth.toml    — secrets (api_key); never commit this file

Both files are looked up in two locations, applied in order so that
later values override earlier ones (env vars always win):
  1. ~/.config/litcli/config.toml
  2. ~/.config/litcli/auth.toml
  3. <project>/.litcli/config.toml
  4. <project>/.litcli/auth.toml
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]


USER_CONFIG_DIR = Path("~/.config/litcli").expanduser()
PROJECT_CONFIG_DIR = ".litcli"

CONFIG_FILENAME = "config.toml"
AUTH_FILENAME = "auth.toml"

# Maps dotted TOML key paths to environment variable names.
CONFIG_ENV_MAP = {
    "openai.api_key": "OPENAI_API_KEY",
    "openai.base_url": "OPENAI_BASE_URL",
    "openai.model": "OPENAI_MODEL",
    "openai.max_tokens": "OPENAI_MAX_TOKENS",
    "openai.temperature": "OPENAI_TEMPERATURE",
    "litcli.data_dir": "LITCLI_DATA_DIR",
    "litcli.pdf_pages": "LITCLI_PDF_PAGES",
    "services.unpaywall_email": "UNPAYWALL_EMAIL",
    "services.openalex_email": "OPENALEX_EMAIL",
    "services.semantic_scholar_api_key": "SEMANTIC_SCHOLAR_API_KEY",
}


def find_project_config_dir(start: Path | None = None) -> Path | None:
    """Walk up from *start* (default: cwd) to find a .litcli/ directory."""
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        candidate = directory / PROJECT_CONFIG_DIR
        if candidate.is_dir():
            return candidate
    return None


def load_config_files() -> None:
    """Load config.toml and auth.toml from user and project locations.

    Environment variables set before this call are never overwritten.
    """
    project_dir = find_project_config_dir()

    candidates: list[Path] = [
        USER_CONFIG_DIR / CONFIG_FILENAME,
        USER_CONFIG_DIR / AUTH_FILENAME,
    ]
    if project_dir is not None:
        candidates += [
            project_dir / CONFIG_FILENAME,
            project_dir / AUTH_FILENAME,
        ]

    original_env = set(os.environ)
    for config_path in candidates:
        if not config_path.is_file():
            continue
        config = _read_toml_config(config_path)
        for key_path, env_name in CONFIG_ENV_MAP.items():
            if env_name in original_env:
                continue
            value = _get_nested_value(config, key_path)
            if value is not None:
                os.environ[env_name] = str(value)


def _read_toml_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open("rb") as fh:
            config = tomllib.load(fh)
    except Exception as exc:
        raise ValueError(f"Invalid TOML config file: {config_path}") from exc

    if not isinstance(config, dict):
        raise ValueError(f"TOML config must be a table: {config_path}")
    return config


def _get_nested_value(config: dict[str, Any], key_path: str) -> Any:
    current: Any = config
    for key in key_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current
