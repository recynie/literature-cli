"""Database diagnostic and cleanup commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, logger
from ng.services import DatabaseHealthService


app = typer.Typer(help="Database maintenance.")


def _service(ctx: typer.Context) -> DatabaseHealthService:
    log = logger(ctx)
    db_path = (ctx.obj or {}).get("db_path")
    return DatabaseHealthService(db_path=db_path, app=log)


@app.command()
def check(ctx: typer.Context, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        report = _service(ctx).run_full_diagnostic()
        output.print_result({"ok": True, "report": report}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def clean(ctx: typer.Context, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = _service(ctx)
        results = {
            "orphaned_records": svc.clean_orphaned_records(),
            "orphaned_pdfs": svc.clean_orphaned_pdfs(),
            "orphaned_htmls": svc.clean_orphaned_htmls(),
            "absolute_pdf_paths": svc.fix_absolute_pdf_paths(),
            "pdf_filenames": svc.clean_pdf_filenames(),
        }
        output.print_result({"ok": True, "cleaned": results}, flag)
    except Exception as exc:
        handle_exception(exc, flag)

