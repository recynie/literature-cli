"""Collection management commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, parse_ids, services


app = typer.Typer(help="Manage paper collections.")


def _collection_by_name(collections, name: str):
    for collection in collections:
        if collection.name == name:
            return collection
    return None


@app.command("list")
def list_collections(ctx: typer.Context, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        collections = services(ctx)["collection"].get_all_collections()
        output.print_result(
            {
                "ok": True,
                "collections": [
                    output.collection_to_dict(collection) for collection in collections
                ],
                "count": len(collections),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def show(ctx: typer.Context, name: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        collection = _collection_by_name(svc["collection"].get_all_collections(), name)
        if not collection:
            output.error(f"Collection '{name}' not found", "NOT_FOUND", flag)
        papers = svc["search"].filter_papers({"collection": name})
        data = output.collection_to_dict(collection)
        output.print_result(
            {
                "ok": True,
                "collection": data,
                "papers": [output.paper_to_dict(paper) for paper in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def create(ctx: typer.Context, name: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        collection = services(ctx)["collection"].add_collection(name)
        output.print_result(
            {"ok": True, "collection": output.collection_to_dict(collection)},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def rename(ctx: typer.Context, old_name: str, new_name: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)["collection"]
        collection = svc.get_collection_by_name(old_name)
        if not collection:
            output.error(f"Collection '{old_name}' not found", "NOT_FOUND", flag)
        if not svc.update_collection_name(collection.id, new_name):
            output.error(f"Failed to rename collection '{old_name}'", "INVALID_INPUT", flag)
        updated = svc.get_collection_by_name(new_name)
        output.print_result(
            {"ok": True, "collection": output.collection_to_dict(updated)},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def delete(
    ctx: typer.Context,
    name: str,
    force: bool = typer.Option(False, "--force", "-f"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)["collection"]
        collection = svc.get_collection_by_name(name)
        if not collection:
            output.error(f"Collection '{name}' not found", "NOT_FOUND", flag)
        if not force and not flag and not typer.confirm(f"Delete collection '{name}'?"):
            raise typer.Exit(0)
        if not svc.delete_collection(collection.id):
            output.error(f"Failed to delete collection '{name}'", "INVALID_INPUT", flag)
        output.print_result(
            {"ok": True, "message": f"Deleted collection '{name}'"},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def add(ctx: typer.Context, name: str, ids: str = typer.Option(..., "--ids"), json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        paper_ids = parse_ids(ids)
        count = services(ctx)["collection"].add_papers_to_collection(paper_ids, name)
        output.print_result(
            {"ok": True, "added": count, "ids": paper_ids, "collection": name},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def remove(ctx: typer.Context, name: str, ids: str = typer.Option(..., "--ids"), json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        paper_ids = parse_ids(ids)
        count, errors = services(ctx)["collection"].remove_papers_from_collection(
            paper_ids, name
        )
        output.print_result(
            {
                "ok": not errors,
                "removed": count,
                "ids": paper_ids,
                "collection": name,
                "errors": errors,
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def purge(ctx: typer.Context, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        count = services(ctx)["collection"].purge_empty_collections()
        output.print_result(
            {"ok": True, "purged": count, "message": f"Purged {count} collection(s)"},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)

