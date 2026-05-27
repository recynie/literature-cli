"""Show paper details."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, services


def show(ctx: typer.Context, paper_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        paper = services(ctx)["paper"].get_paper_by_id(paper_id)
        if not paper:
            output.error(f"Paper with ID {paper_id} not found", "NOT_FOUND", flag)
        output.print_result({"ok": True, "paper": output.paper_to_dict(paper)}, flag)
    except Exception as exc:
        handle_exception(exc, flag)

