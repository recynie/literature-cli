"""Edit paper metadata."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


def edit(
    ctx: typer.Context,
    paper_id: int,
    title: str | None = typer.Option(None, "--title"),
    notes: str | None = typer.Option(None, "--notes"),
    year: int | None = typer.Option(None, "--year"),
    venue_full: str | None = typer.Option(None, "--venue-full"),
    venue_acronym: str | None = typer.Option(None, "--venue-acronym"),
    paper_type: str | None = typer.Option(None, "--paper-type"),
    doi: str | None = typer.Option(None, "--doi"),
    arxiv_id: str | None = typer.Option(None, "--arxiv-id"),
    openreview_id: str | None = typer.Option(None, "--openreview-id"),
    dblp_key: str | None = typer.Option(None, "--dblp-key"),
    openalex_id: str | None = typer.Option(None, "--openalex-id"),
    semantic_scholar_id: str | None = typer.Option(None, "--semantic-scholar-id"),
    url: str | None = typer.Option(None, "--url"),
    pdf_path: str | None = typer.Option(None, "--pdf-path"),
    extract_pdf: bool = typer.Option(False, "--extract-pdf"),
    fetch: bool = typer.Option(False, "--fetch"),
    overwrite: bool = typer.Option(False, "--overwrite"),
    summarize: bool = typer.Option(False, "--summarize"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper_service = svc["paper"]
        paper = paper_service.get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)

        updates = {
            "title": title,
            "notes": notes,
            "year": year,
            "venue_full": venue_full,
            "venue_acronym": venue_acronym,
            "paper_type": paper_type,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "openreview_id": openreview_id,
            "dblp_key": dblp_key,
            "openalex_id": openalex_id,
            "semantic_scholar_id": semantic_scholar_id,
            "url": url,
            "pdf_path": pdf_path,
        }
        updates = {key: value for key, value in updates.items() if value is not None}

        warning = ""
        if extract_pdf:
            if not paper.pdf_path:
                output.error(
                    f"Paper with ID {paper_id} has no linked PDF",
                    "INVALID_INPUT",
                    flag,
                )
            result = svc["add"].extract_and_update_pdf_metadata(
                paper_id, paper.pdf_path
            )
            if not result.get("success"):
                output.error(
                    result.get("error") or "Failed to extract PDF metadata",
                    "LLM_ERROR",
                    flag,
                )
            paper = paper_service.get_paper_by_id(paper_id)

        if summarize:
            if not paper.pdf_path:
                output.error(
                    f"Paper with ID {paper_id} has no linked PDF",
                    "INVALID_INPUT",
                    flag,
                )
            summary = svc["metadata"].generate_paper_summary(paper.pdf_path)
            if not summary:
                output.error("Failed to generate paper summary", "LLM_ERROR", flag)
            updates["notes"] = summary

        if updates:
            updated_paper, warning = paper_service.update_paper(paper_id, updates)
            if not updated_paper:
                output.error(warning or "Failed to update paper", "INVALID_INPUT", flag)
            paper = paper_service.get_paper_by_id(paper_id)

        fetched_fields = []
        fetch_metadata = None
        if fetch:
            result = svc["fetch"].fetch_metadata_for_paper(paper, overwrite=overwrite)
            paper = result["paper"]
            fetched_fields = result.get("updated") or []
            fetch_metadata = result.get("metadata")
            warning = warning or result.get("warning") or ""

        output.print_result(
            {
                "ok": True,
                "paper": output.paper_to_dict(paper),
                "fetched_fields": fetched_fields,
                "fetched_metadata": fetch_metadata,
                "warning": warning or None,
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)
