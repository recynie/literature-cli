"""Paper import commands."""

from __future__ import annotations

import os

import typer
import typer._click as click
from typer.core import TyperGroup

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


class AddCommandGroup(TyperGroup):
    """Route unknown `lit add <identifier>` values to the unified importer."""

    def list_commands(self, ctx):
        return [
            name
            for name in super().list_commands(ctx)
            if not getattr(self.get_command(ctx, name), "hidden", False)
        ]

    def resolve_command(self, ctx, args):
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError:
            command = self.get_command(ctx, "identifier")
            if command is None or not args:
                raise
            return "identifier", command, args


app = typer.Typer(cls=AddCommandGroup, help="Import papers.", rich_markup_mode=None)


def _single_response(result: dict, svc: dict) -> dict:
    paper = result.get("paper")
    if paper and result.get("pdf_path") and not result.get("pdf_error"):
        relative_path = svc["pdf_manager"].get_relative_path(result["pdf_path"])
        updated, update_error = svc["paper"].update_paper(paper.id, {"pdf_path": relative_path})
        if updated:
            paper = svc["paper"].get_paper_by_id(paper.id)
        elif update_error:
            result["pdf_error"] = update_error
    return {
        "ok": True,
        "paper": output.paper_to_dict(paper),
        "pdf_path": result.get("pdf_path"),
        "pdf_error": result.get("pdf_error"),
        "download_duration": result.get("download_duration"),
    }


def _identifier_response(result: dict, svc: dict) -> dict:
    if "papers" in result:
        return {
            "ok": True,
            "papers": [output.paper_to_dict(paper) for paper in result["papers"]],
            "errors": result.get("errors") or [],
            "count": result.get("count", len(result["papers"])),
            "identifier_type": result.get("identifier_type"),
        }
    data = _single_response(result, svc)
    data["identifier_type"] = result.get("identifier_type")
    return data


@app.command("identifier", hidden=True)
def identifier(ctx: typer.Context, identifier: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        result = svc["add"].add_by_identifier(identifier)
        output.print_result(_identifier_response(result, svc), flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def arxiv(ctx: typer.Context, identifier: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        output.print_result(_single_response(svc["add"].add_arxiv_paper(identifier), svc), flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def dblp(ctx: typer.Context, url: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        output.print_result(_single_response(svc["add"].add_dblp_paper(url), svc), flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def openreview(ctx: typer.Context, identifier: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        output.print_result(
            _single_response(svc["add"].add_openreview_paper(identifier), svc), flag
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def doi(ctx: typer.Context, doi_value: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        output.print_result(_single_response(svc["add"].add_doi_paper(doi_value), svc), flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def pdf(ctx: typer.Context, path: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        result = svc["add"].add_pdf_paper_async(path)
        paper = result["paper"]
        metadata_result = svc["add"].extract_and_update_pdf_metadata(
            paper.id, os.path.abspath(os.path.expanduser(path))
        )
        if metadata_result.get("success") and metadata_result.get("paper"):
            paper = svc["paper"].get_paper_by_id(paper.id)
        data = {
            "ok": metadata_result.get("success", False),
            "paper": output.paper_to_dict(paper),
            "error": metadata_result.get("error"),
        }
        output.print_result(data, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def bib(ctx: typer.Context, path: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        papers, errors = svc["add"].add_bib_papers(path)
        data = {
            "ok": True,
            "papers": [output.paper_to_dict(paper) for paper in papers],
            "errors": errors,
            "count": len(papers),
        }
        output.print_result(data, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def ris(ctx: typer.Context, path: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        papers, errors = svc["add"].add_ris_papers(path)
        data = {
            "ok": True,
            "papers": [output.paper_to_dict(paper) for paper in papers],
            "errors": errors,
            "count": len(papers),
        }
        output.print_result(data, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def manual(
    ctx: typer.Context,
    title: str = typer.Option("", "--title", help="Paper title."),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        output.print_result(_single_response(svc["add"].add_manual_paper(title), svc), flag)
    except Exception as exc:
        handle_exception(exc, flag)
