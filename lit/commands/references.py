"""Crossref reference retrieval commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


def references(
    ctx: typer.Context,
    paper_id: int | None = typer.Argument(
        None, help="Local paper ID. Uses DOI first, then title lookup."
    ),
    doi: str | None = typer.Option(None, "--doi", help="Fetch references by DOI."),
    title: str | None = typer.Option(
        None,
        "--title",
        help="Match a Crossref work by title, then fetch references by DOI.",
    ),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        selected = sum(value is not None for value in (paper_id, doi, title))
        if selected != 1:
            raise ValueError("Provide exactly one of PAPER_ID, --doi, or --title")

        service = services(ctx)["references"]
        if paper_id is not None:
            result = service.references_for_paper(paper_id)
        elif doi:
            result = service.references_for_doi(doi)
        else:
            result = service.references_for_title(title or "")

        result["ok"] = True
        output.print_result(result, flag)
    except Exception as exc:
        handle_exception(exc, flag)
