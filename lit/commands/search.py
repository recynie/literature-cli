"""Search and filter commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import (
    JSON_OPTION,
    as_json,
    handle_exception,
    parse_year_range,
    services,
)


def search(
    ctx: typer.Context,
    query: str,
    fields: str | None = typer.Option(None, "--fields", help="Comma-separated fields."),
    fuzzy: bool = typer.Option(False, "--fuzzy", help="Use fuzzy matching."),
    threshold: int = typer.Option(60, "--threshold", min=0, max=100),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        if fuzzy:
            papers = svc["search"].fuzzy_search_papers(query, threshold)
        else:
            field_list = [item.strip() for item in fields.split(",")] if fields else None
            papers = svc["search"].search_papers(query, field_list)
        output.print_result(
            {
                "ok": True,
                "papers": [output.paper_to_dict(paper) for paper in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


def filter(
    ctx: typer.Context,
    author: str | None = typer.Option(None, "--author"),
    year: int | None = typer.Option(None, "--year"),
    year_range: str | None = typer.Option(None, "--year-range"),
    venue: str | None = typer.Option(None, "--venue"),
    paper_type: str | None = typer.Option(None, "--type"),
    collection: str | None = typer.Option(None, "--collection"),
    query: str | None = typer.Option(None, "--query"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        filters = {}
        if author:
            filters["author"] = author
        if year is not None:
            filters["year"] = year
        parsed_range = parse_year_range(year_range)
        if parsed_range:
            filters["year_range"] = parsed_range
        if venue:
            filters["venue"] = venue
        if paper_type:
            filters["paper_type"] = paper_type
        if collection:
            filters["collection"] = collection
        if query:
            filters["all"] = query
        svc = services(ctx)
        papers = svc["search"].filter_papers(filters)
        output.print_result(
            {
                "ok": True,
                "papers": [output.paper_to_dict(paper) for paper in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)

