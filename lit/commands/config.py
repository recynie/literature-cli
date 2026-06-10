"""Configuration inspection commands."""

from __future__ import annotations

import os
from pathlib import Path

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json
from lit.config import (
    AUTH_FILENAME,
    CONFIG_FILENAME,
    USER_CONFIG_DIR,
    config_candidates,
    find_project_config_dir,
)

app = typer.Typer(help="Inspect resolved configuration.", rich_markup_mode=None)


def _config_report() -> dict:
    cwd = Path.cwd().resolve()
    project_dir = find_project_config_dir(cwd)
    user_config = USER_CONFIG_DIR / CONFIG_FILENAME
    user_auth = USER_CONFIG_DIR / AUTH_FILENAME
    project_config = project_dir / CONFIG_FILENAME if project_dir else None
    project_auth = project_dir / AUTH_FILENAME if project_dir else None

    return {
        "ok": True,
        "cwd": str(cwd),
        "project_config_dir": str(project_dir) if project_dir else None,
        "files": {
            "project_config": str(project_config) if project_config and project_config.is_file() else None,
            "project_auth": str(project_auth) if project_auth and project_auth.is_file() else None,
            "user_config": str(user_config) if user_config.is_file() else None,
            "user_auth": str(user_auth) if user_auth.is_file() else None,
        },
        "load_order": [str(path) for path in config_candidates(cwd) if path.is_file()],
        "resolved": {
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL"),
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL"),
            "OPENAI_API_KEY_SET": bool(os.getenv("OPENAI_API_KEY")),
            "LITCLI_DATA_DIR": os.getenv("LITCLI_DATA_DIR", str(Path("~/.litcli").expanduser())),
            "LITCLI_PDF_PAGES": os.getenv("LITCLI_PDF_PAGES"),
            "UNPAYWALL_EMAIL": os.getenv("UNPAYWALL_EMAIL"),
            "OPENALEX_EMAIL": os.getenv("OPENALEX_EMAIL"),
            "SEMANTIC_SCHOLAR_API_KEY_SET": bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
            "MINERU_API_KEY_SET": bool(os.getenv("MINERU_API_KEY")),
            "MINERU_MODEL": os.getenv("MINERU_MODEL"),
            "MINERU_LANGUAGE": os.getenv("MINERU_LANGUAGE"),
            "MINERU_OCR": os.getenv("MINERU_OCR"),
        },
    }


@app.callback(invoke_without_command=True)
def config_root(ctx: typer.Context, json: bool = JSON_OPTION):
    if ctx.invoked_subcommand is not None:
        return
    output.print_result(_config_report(), as_json(ctx, json))
