"""PDF management commands."""

from __future__ import annotations

import os
import re

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services
from ng.db.database import get_pdf_directory


app = typer.Typer(help="Manage paper PDFs.")


def _paper_or_error(ctx: typer.Context, paper_id: int, flag: bool):
    paper = services(ctx)["paper"].get_paper_by_id(paper_id)
    if not paper:
        output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)
    return paper


@app.command()
def path(ctx: typer.Context, paper_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper = svc["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)
        if not paper.pdf_path:
            output.error(
                f"Paper with ID {paper_id} has no linked PDF",
                "NOT_FOUND",
                flag,
            )
        absolute_path = svc["pdf_manager"].get_absolute_path(paper.pdf_path)
        output.print_result({"ok": True, "path": absolute_path}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def open(ctx: typer.Context, paper_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper = svc["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)
        if not paper.pdf_path:
            output.error(
                f"Paper with ID {paper_id} has no linked PDF",
                "NOT_FOUND",
                flag,
            )
        absolute_path = svc["pdf_manager"].get_absolute_path(paper.pdf_path)
        ok, err = svc["system"].open_pdf(absolute_path)
        if not ok:
            output.error(err, "INVALID_INPUT", flag)
        output.print_result({"ok": True, "path": absolute_path, "message": "Opened PDF"}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def download(ctx: typer.Context, paper_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper = svc["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)

        source = None
        identifier = None
        if paper.preprint_id and "arxiv" in paper.preprint_id.lower():
            source = "arxiv"
            identifier = paper.preprint_id.lower().replace("arxiv", "").strip()
        elif paper.url and "arxiv.org" in paper.url.lower():
            source = "arxiv"
            # Extract arXiv ID from URL like https://arxiv.org/abs/2505.15134
            match = re.search(r"arxiv\.org/(?:abs|pdf)/([\d.]+(?:v\d+)?)", paper.url)
            if match:
                identifier = match.group(1)
        elif paper.url and "openreview.net" in paper.url:
            source = "openreview"
            identifier = paper.url.rsplit("id=", 1)[-1]
        elif paper.url and paper.url.lower().endswith(".pdf"):
            relative, err = svc["pdf_manager"].process_pdf_path(
                paper.url,
                {
                    "title": paper.title,
                    "authors": [a.full_name for a in paper.get_ordered_authors()],
                    "year": paper.year,
                },
                paper.pdf_path,
            )
            if err:
                output.error(err, "NETWORK_ERROR", flag)
            updated, update_error = svc["paper"].update_paper(
                paper_id, {"pdf_path": relative}
            )
            if update_error:
                output.error(update_error, "INVALID_INPUT", flag)
            updated = svc["paper"].get_paper_by_id(paper_id)
            output.print_result(
                {"ok": True, "paper": output.paper_to_dict(updated)},
                flag,
            )
            return

        if not source or not identifier:
            output.error(
                "PDF download is only supported for arXiv, OpenReview, or direct PDF URLs",
                "INVALID_INPUT",
                flag,
            )

        paper_data = {
            "title": paper.title,
            "authors": [a.full_name for a in paper.get_ordered_authors()],
            "year": paper.year,
        }
        pdf_path, pdf_error, duration = svc["system"].download_pdf(
            source, identifier, get_pdf_directory(), paper_data
        )
        if pdf_error:
            output.error(pdf_error, "NETWORK_ERROR", flag)
        relative_path = os.path.relpath(pdf_path, get_pdf_directory())
        updated, update_error = svc["paper"].update_paper(
            paper_id, {"pdf_path": relative_path}
        )
        if update_error:
            output.error(update_error, "INVALID_INPUT", flag)
        updated = svc["paper"].get_paper_by_id(paper_id)
        output.print_result(
            {
                "ok": True,
                "paper": output.paper_to_dict(updated),
                "pdf_path": pdf_path,
                "download_duration": duration,
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)
