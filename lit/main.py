"""Typer entry point for the LiteratureCLI."""

from __future__ import annotations

import logging
import os
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import typer

from lit.config import load_config_files
from lit.logger import CliLogger
from lit.commands import add, affiliation, author, collect, db, delete, edit, export, list, pdf, search, show
from ng.db.database import init_database


app = typer.Typer(help="Agent-oriented research paper management CLI.")


def _default_db_path() -> str:
    data_dir = Path(os.getenv("LITCLI_DATA_DIR", "~/.litcli")).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "papers.db")


@app.callback()
def main(
    ctx: typer.Context,
    json: bool = typer.Option(False, "--json", help="Output JSON by default."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs."),
):
    load_config_files()
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format="%(levelname)s:%(name)s:%(message)s",
    )
    db_path = _default_db_path()
    if verbose:
        init_database(db_path)
    else:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            init_database(db_path)
    ctx.obj = {
        "json": json,
        "db_path": db_path,
        "logger": CliLogger(db_path),
    }


app.add_typer(add.app, name="add", help="Import papers from external sources.")
app.add_typer(author.app, name="author", help="Manage authors.")
app.add_typer(affiliation.app, name="affiliation", help="Manage affiliations.")
app.command("search")(search.search)
app.command("filter")(search.filter)
app.command("list")(list.list_papers)
app.command("show")(show.show)
app.command("edit")(edit.edit)
app.command("delete")(delete.delete)
app.command("export")(export.export)
app.add_typer(collect.app, name="collect", help="Manage collections.")
app.add_typer(pdf.app, name="pdf", help="Manage local PDFs.")
app.add_typer(db.app, name="db", help="Database diagnostics and cleanup.")


if __name__ == "__main__":
    app()
