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
    in_sources: str | None = typer.Option(
        None, "--in",
        help="Comma-separated sources: title,abstract,authors,venue,notes,body,summary.",
    ),
    fuzzy: bool = typer.Option(False, "--fuzzy", help="Use fuzzy matching."),
    threshold: int = typer.Option(60, "--threshold", min=0, max=100),
    key: bool = typer.Option(False, "--key", help="Show raw platform identifiers instead of derived URLs."),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        if fuzzy:
            papers = svc["search"].fuzzy_search_papers(query, threshold)
            output.print_result(
                {
                    "ok": True,
                    "papers": [output.search_paper_to_dict(p, use_keys=key) for p in papers],
                    "count": len(papers),
                },
                flag,
            )
        else:
            sources = [s.strip() for s in in_sources.split(",") if s.strip()] if in_sources else None
            results = svc["search"].search_papers(query, sources)
            output.print_result(
                {
                    "ok": True,
                    "query": query,
                    "papers": [output.search_match_to_dict(m, use_keys=key) for m in results],
                    "count": len(results),
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
    affiliation: str | None = typer.Option(None, "--affiliation"),
    query: str | None = typer.Option(None, "--query"),
    key: bool = typer.Option(False, "--key", help="Show raw platform identifiers instead of derived URLs."),
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
        if affiliation:
            filters["affiliation"] = affiliation
        if query:
            filters["all"] = query
        svc = services(ctx)
        papers = svc["search"].filter_papers(filters)
        output.print_result(
            {
                "ok": True,
                "papers": [output.paper_to_dict(p, use_keys=key) for p in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)

