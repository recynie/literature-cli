"""List papers."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


def list_papers(
    ctx: typer.Context,
    limit: int | None = typer.Option(None, "--limit", min=1),
    sort: str = typer.Option("added_date", "--sort", help="year|title|added_date"),
    key: bool = typer.Option(False, "--key", help="Show raw platform identifiers instead of derived URLs."),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        papers = services(ctx)["paper"].get_all_papers()
        reverse = sort in {"year", "added_date"}
        if sort == "title":
            papers.sort(key=lambda paper: (paper.title or "").lower())
        elif sort == "year":
            papers.sort(key=lambda paper: paper.year or 0, reverse=reverse)
        elif sort == "added_date":
            papers.sort(key=lambda paper: paper.added_date or "", reverse=reverse)
        else:
            raise typer.BadParameter("sort must be one of: year, title, added_date")
        if limit:
            papers = papers[:limit]
        output.print_result(
            {
                "ok": True,
                "papers": [output.paper_to_dict(paper, use_keys=key) for paper in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)

