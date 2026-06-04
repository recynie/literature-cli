"""PDF management commands."""

from __future__ import annotations

import os
from typing import Optional

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services
from ng.db.database import get_db_manager, get_pdf_directory
from ng.services.mineru import MinerUService, mineru_config_from_env

app = typer.Typer(help="Manage paper PDFs.", rich_markup_mode=None)


def _paper_or_error(ctx: typer.Context, paper_id: int, flag: bool):
    paper = services(ctx)["paper"].get_paper_by_id(paper_id)
    if not paper:
        output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)
    return paper


def _get_parsed_dir(paper_id: int) -> str:
    """Return the parsed output directory for *paper_id* (not yet created)."""
    data_dir = os.path.dirname(get_db_manager().db_path)
    return os.path.join(data_dir, "parsed", str(paper_id))


def _run_mineru_parse(
    ctx: typer.Context,
    paper,
    flag: bool,
    *,
    model: Optional[str] = None,
    ocr: Optional[bool] = None,
    language: Optional[str] = None,
    extra_formats: list[str] | None = None,
    force: bool = False,
) -> dict | None:
    """Run MinerU parse for *paper*.  Returns result dict or None on skip.

    Raises typer.Exit (via output.error) on hard errors.
    """
    svc = services(ctx)

    mineru_cfg = mineru_config_from_env()
    if mineru_cfg is None:
        return None  # Not configured → silent skip

    # Apply per-call overrides
    if model is not None:
        mineru_cfg.model = model
    if ocr is not None:
        mineru_cfg.ocr = ocr
    if language is not None:
        mineru_cfg.language = language

    # Resolve absolute PDF path
    abs_pdf = svc["pdf_manager"].get_absolute_path(paper.pdf_path)
    if not os.path.exists(abs_pdf):
        output.error(
            f"Local PDF file not found at {abs_pdf}",
            "NOT_FOUND",
            flag,
        )

    output_dir = _get_parsed_dir(paper.id)
    mineru_svc = MinerUService(app=svc["app"])

    result = mineru_svc.parse_pdf(
        pdf_path=abs_pdf,
        paper_id=paper.id,
        output_dir=output_dir,
        config=mineru_cfg,
        extra_formats=extra_formats or [],
    )

    # Store relative markdown path in DB
    data_dir = os.path.dirname(get_db_manager().db_path)
    relative_md = os.path.relpath(result.markdown_path, data_dir)
    svc["paper"].update_paper(paper.id, {"parsed_pdf_path": relative_md})

    return {
        "markdown_path": result.markdown_path,
        "json_path": result.json_path,
        "extra_paths": result.extra_paths,
    }


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
def download(
    ctx: typer.Context,
    paper_id: int,
    json: bool = JSON_OPTION,
    no_parse: bool = typer.Option(False, "--no-parse", help="Skip MinerU PDF parsing after download."),
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper = svc["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)

        source = None
        identifier = None
        from ng.services.arxiv_utils import parse_arxiv_id

        arxiv_id = parse_arxiv_id(paper)
        if arxiv_id:
            source = "arxiv"
            identifier = arxiv_id
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

            parse_result = None
            if not no_parse:
                try:
                    parse_result = _run_mineru_parse(ctx, updated, flag)
                except Exception as parse_exc:
                    output.error(str(parse_exc), "MINERU_ERROR", flag)

            result_dict = {"ok": True, "paper": output.paper_to_dict(updated)}
            if parse_result:
                result_dict["parsed"] = parse_result
            output.print_result(result_dict, flag)
            return
        elif paper.doi:
            source = "doi"
            identifier = paper.doi

        if not source or not identifier:
            output.error(
                "PDF download is only supported when arXiv, OpenReview, DOI, or direct PDF URL metadata is available",
                "INVALID_INPUT",
                flag,
            )

        paper_data = {
            "title": paper.title,
            "authors": [a.full_name for a in paper.get_ordered_authors()],
            "year": paper.year,
            "doi": paper.doi,
            "arxiv_id": getattr(paper, "arxiv_id", None),
            "openreview_id": getattr(paper, "openreview_id", None),
            "url": paper.url,
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

        parse_result = None
        if not no_parse:
            try:
                parse_result = _run_mineru_parse(ctx, updated, flag)
            except Exception as parse_exc:
                output.error(str(parse_exc), "MINERU_ERROR", flag)

        result_dict = {
            "ok": True,
            "paper": output.paper_to_dict(updated),
            "pdf_path": pdf_path,
            "download_duration": duration,
        }
        if parse_result:
            result_dict["parsed"] = parse_result
        output.print_result(result_dict, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def parse(
    ctx: typer.Context,
    paper_id: int,
    json: bool = JSON_OPTION,
    force: bool = typer.Option(False, "--force", help="Re-parse even if results already exist."),
    model: Optional[str] = typer.Option(None, "--model", help="Override MinerU model (vlm/pipeline/html)."),
    ocr: Optional[bool] = typer.Option(None, "--ocr/--no-ocr", help="Override OCR setting."),
    language: Optional[str] = typer.Option(None, "--language", help="Override language code."),
    extra_formats: Optional[list[str]] = typer.Option(None, "--extra-formats", help="Extra output formats (html, docx, latex). Repeatable."),
):
    """Parse a paper's local PDF with MinerU and save structured results."""
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        paper = svc["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)

        if not paper.pdf_path:
            output.error(
                f"Paper {paper_id} has no local PDF. Run `lit pdf download {paper_id}` first.",
                "NOT_FOUND",
                flag,
            )

        # Check if already parsed (skip unless --force)
        if not force and paper.parsed_pdf_path:
            data_dir = os.path.dirname(get_db_manager().db_path)
            abs_md = os.path.join(data_dir, paper.parsed_pdf_path)
            if os.path.exists(abs_md):
                output.print_result(
                    {
                        "ok": True,
                        "skipped": True,
                        "message": "Already parsed. Use --force to re-parse.",
                        "markdown_path": abs_md,
                    },
                    flag,
                )
                return

        mineru_cfg = mineru_config_from_env()
        if mineru_cfg is None:
            output.error(
                "MINERU_API_KEY is not configured. Set it in auth.toml or as an environment variable.",
                "INVALID_INPUT",
                flag,
            )

        try:
            parse_result = _run_mineru_parse(
                ctx,
                paper,
                flag,
                model=model,
                ocr=ocr,
                language=language,
                extra_formats=extra_formats or [],
                force=force,
            )
        except Exception as parse_exc:
            output.error(str(parse_exc), "MINERU_ERROR", flag)

        output.print_result(
            {
                "ok": True,
                "paper_id": paper_id,
                "parsed": parse_result,
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)
