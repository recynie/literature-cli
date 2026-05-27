"""Configuration loading for LiteratureCLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


USER_CONFIG_PATH = Path("~/.config/litcli/auth.json").expanduser()
PROJECT_CONFIG_DIR = ".litcli"
CONFIG_FILENAME = "auth.json"


CONFIG_ENV_MAP = {
    "openai.api_key": "OPENAI_API_KEY",
    "openai.base_url": "OPENAI_BASE_URL",
    "openai.model": "OPENAI_MODEL",
    "openai.max_tokens": "OPENAI_MAX_TOKENS",
    "openai.temperature": "OPENAI_TEMPERATURE",
    "litcli.data_dir": "LITCLI_DATA_DIR",
    "litcli.pdf_pages": "LITCLI_PDF_PAGES",
}


def find_project_config(start: Path | None = None) -> Path | None:
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        config_path = directory / PROJECT_CONFIG_DIR / CONFIG_FILENAME
        if config_path.is_file():
            return config_path
    return None


def load_config_files() -> None:
    original_env = set(os.environ)
    for config_path in (USER_CONFIG_PATH, find_project_config()):
        if config_path is None or not config_path.is_file():
            continue
        config = _read_json_config(config_path)
        for key_path, env_name in CONFIG_ENV_MAP.items():
            value = _get_nested_value(config, key_path)
            if value is None or env_name in original_env:
                continue
            os.environ[env_name] = str(value)


def _read_json_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open(encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON config file: {config_path}") from exc

    if not isinstance(config, dict):
        raise ValueError(f"JSON config must be an object: {config_path}")
    return config


def _get_nested_value(config: dict[str, Any], key_path: str) -> Any:
    current: Any = config
    for key in key_path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current
