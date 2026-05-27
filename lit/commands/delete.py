"""Delete papers."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, parse_ids, services


def delete(
    ctx: typer.Context,
    paper_id: int | None = typer.Argument(None),
    ids: str | None = typer.Option(None, "--ids", help="Comma-separated paper IDs."),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation."),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        paper_ids = parse_ids(ids)
        if paper_id is not None:
            paper_ids.insert(0, paper_id)
        paper_ids = list(dict.fromkeys(paper_ids))
        if not paper_ids:
            output.error("Provide a paper ID or --ids", "INVALID_INPUT", flag)

        if not force and not flag:
            confirmed = typer.confirm(
                f"Delete {len(paper_ids)} paper(s) and linked PDF files?"
            )
            if not confirmed:
                raise typer.Exit(0)

        paper_service = services(ctx)["paper"]
        if len(paper_ids) == 1:
            deleted = paper_service.delete_paper(paper_ids[0])
            count = 1 if deleted else 0
        else:
            count = paper_service.delete_papers(paper_ids)
        if count == 0:
            output.error("No matching papers found", "NOT_FOUND", flag)
        output.print_result(
            {
                "ok": True,
                "deleted": count,
                "ids": paper_ids,
                "message": f"Deleted {count} paper(s)",
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)

