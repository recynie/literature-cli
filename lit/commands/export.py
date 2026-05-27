"""Export papers to citation and document formats."""

from __future__ import annotations

import json as jsonlib

import typer

from lit import output
from lit.commands import (
    JSON_OPTION,
    as_json,
    handle_exception,
    papers_by_ids,
    parse_ids,
    services,
    write_text,
)
from ng.services.export import (
    export_to_bibtex,
    export_to_html,
    export_to_ieee,
    export_to_json,
    export_to_markdown,
)


EXPORTERS = {
    "bibtex": export_to_bibtex,
    "ieee": export_to_ieee,
    "markdown": export_to_markdown,
    "html": export_to_html,
    "json": export_to_json,
}


def export(
    ctx: typer.Context,
    format: str = typer.Option("bibtex", "--format", help="bibtex|ieee|markdown|html|json"),
    ids: str | None = typer.Option(None, "--ids", help="Comma-separated paper IDs."),
    collection: str | None = typer.Option(None, "--collection"),
    output_path: str | None = typer.Option(None, "--output"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        fmt = format.lower()
        if fmt not in EXPORTERS:
            raise typer.BadParameter("format must be one of: bibtex, ieee, markdown, html, json")

        svc = services(ctx)
        if collection:
            papers = svc["search"].filter_papers({"collection": collection})
        else:
            papers = papers_by_ids(svc["paper"], parse_ids(ids))

        content = EXPORTERS[fmt](papers)
        if output_path:
            write_text(output_path, content)

        if flag:
            exported: object = content
            if fmt == "json":
                exported = jsonlib.loads(content)
            data = {
                "ok": True,
                "format": fmt,
                "count": len(papers),
                "output": output_path,
                "content": exported,
            }
            output.print_result(data, True)
        else:
            if output_path:
                output.print_result(
                    {
                        "ok": True,
                        "message": f"Exported {len(papers)} paper(s) to {output_path}",
                    },
                    False,
                )
            else:
                print(content)
    except Exception as exc:
        handle_exception(exc, flag)

