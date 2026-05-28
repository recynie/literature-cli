"""Affiliation management commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


app = typer.Typer(help="Manage affiliations.", rich_markup_mode=None)


@app.command("list")
def list_affiliations(ctx: typer.Context, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        affiliations = services(ctx)["affiliation"].get_all_affiliations()
        output.print_result(
            {
                "ok": True,
                "affiliations": [output.affiliation_to_dict(a) for a in affiliations],
                "count": len(affiliations),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def show(ctx: typer.Context, affiliation_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        affiliation = services(ctx)["affiliation"].get_affiliation_by_id(affiliation_id)
        if not affiliation:
            output.error(f"Affiliation with ID {affiliation_id} not found", "NOT_FOUND", flag)
        output.print_result(
            {"ok": True, "affiliation": output.affiliation_to_dict(affiliation)},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def add(
    ctx: typer.Context,
    institution: str,
    department: str | None = typer.Option(None, "--department"),
    url: str | None = typer.Option(None, "--url"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        affiliation = services(ctx)["affiliation"].add_affiliation(
            {"institution": institution, "department": department, "url": url}
        )
        output.print_result({"ok": True, "affiliation": output.affiliation_to_dict(affiliation)}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def edit(
    ctx: typer.Context,
    affiliation_id: int,
    institution: str | None = typer.Option(None, "--institution"),
    department: str | None = typer.Option(None, "--department"),
    url: str | None = typer.Option(None, "--url"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        data = {k: v for k, v in {"institution": institution, "department": department, "url": url}.items() if v is not None}
        affiliation, err = services(ctx)["affiliation"].update_affiliation(affiliation_id, data)
        if not affiliation:
            output.error(err, "NOT_FOUND", flag)
        output.print_result({"ok": True, "affiliation": output.affiliation_to_dict(affiliation)}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def delete(
    ctx: typer.Context,
    affiliation_id: int,
    force: bool = typer.Option(False, "--force", "-f"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        if not services(ctx)["affiliation"].delete_affiliation(affiliation_id, force=force):
            output.error(f"Affiliation with ID {affiliation_id} not found", "NOT_FOUND", flag)
        output.print_result({"ok": True, "message": f"Deleted affiliation {affiliation_id}"}, flag)
    except Exception as exc:
        handle_exception(exc, flag)
