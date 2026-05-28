"""Shared command helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from lit.logger import CliLogger
from lit import output
from ng.services import (
    AddPaperService,
    AffiliationService,
    AuthorService,
    CollectionService,
    FetchMetadataService,
    MetadataExtractor,
    PaperService,
    PDFManager,
    SearchService,
    SystemService,
)


JSON_OPTION = typer.Option(False, "--json", help="Output machine-readable JSON.")


def as_json(ctx: typer.Context, json: bool) -> bool:
    return bool(json or (ctx.obj or {}).get("json"))


def logger(ctx: typer.Context) -> CliLogger:
    obj = ctx.obj or {}
    existing = obj.get("logger")
    if existing:
        return existing
    return CliLogger(obj.get("db_path"))


def services(ctx: typer.Context) -> dict[str, Any]:
    app = logger(ctx)
    pdf_manager = PDFManager(app=app)
    paper_service = PaperService(app)
    metadata_extractor = MetadataExtractor(pdf_manager, app)
    system_service = SystemService(pdf_manager, app)
    return {
        "app": app,
        "pdf_manager": pdf_manager,
        "paper": paper_service,
        "author": AuthorService(app),
        "affiliation": AffiliationService(app),
        "search": SearchService(app),
        "collection": CollectionService(app),
        "metadata": metadata_extractor,
        "system": system_service,
        "fetch": FetchMetadataService(
            paper_service, metadata_extractor, app
        ),
        "add": AddPaperService(
            paper_service, metadata_extractor, system_service, app
        ),
    }


def parse_ids(value: str | None) -> list[int]:
    if not value:
        return []
    ids: list[int] = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            ids.append(int(raw))
        except ValueError as exc:
            raise typer.BadParameter(f"Invalid paper id: {raw}") from exc
    return ids


def parse_year_range(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split("-", 1)]
    if len(parts) != 2:
        raise typer.BadParameter("Use START-END, for example 2020-2023")
    try:
        start, end = int(parts[0]), int(parts[1])
    except ValueError as exc:
        raise typer.BadParameter("Year range values must be integers") from exc
    return start, end


def papers_by_ids(paper_service: PaperService, ids: list[int]):
    if not ids:
        return paper_service.get_all_papers()
    papers = []
    missing = []
    for paper_id in ids:
        paper = paper_service.get_paper_by_id(paper_id)
        if paper:
            papers.append(paper)
        else:
            missing.append(paper_id)
    if missing:
        raise ValueError(f"Paper ID(s) not found: {', '.join(map(str, missing))}")
    return papers


def handle_exception(exc: Exception, as_json_flag: bool):
    if isinstance(exc, typer.Exit):
        raise exc
    message = str(exc)
    lower = message.lower()
    if (
        "not found" in lower
        or "no paper" in lower
        or "failed to fetch arxiv metadata" in lower
        or "bad request" in lower
    ):
        code = "NOT_FOUND"
    elif "already exists" in lower or "duplicate" in lower:
        code = "ALREADY_EXISTS"
    elif "openai" in lower or "llm" in lower or "api key" in lower:
        code = "LLM_ERROR"
    elif "network" in lower or "request" in lower or "http" in lower:
        code = "NETWORK_ERROR"
    else:
        code = "INVALID_INPUT"
    output.error(message, code, as_json_flag)


def write_text(path: str, content: str):
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
