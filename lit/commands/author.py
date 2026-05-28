"""Author management commands."""

from __future__ import annotations

import typer

from lit import output
from lit.commands import JSON_OPTION, as_json, handle_exception, parse_ids, services


app = typer.Typer(help="Manage authors.", rich_markup_mode=None)


@app.command("list")
def list_authors(
    ctx: typer.Context,
    institution: str | None = typer.Option(None, "--institution", "--affiliation"),
    department: str | None = typer.Option(None, "--department"),
    has_email: bool = typer.Option(False, "--has-email"),
    has_url: bool = typer.Option(False, "--has-url"),
    no_affiliation: bool = typer.Option(False, "--no-affiliation"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        filters = {}
        if institution:
            filters["institution"] = institution
        if department:
            filters["department"] = department
        if has_email:
            filters["has_email"] = True
        if has_url:
            filters["has_url"] = True
        if no_affiliation:
            filters["no_affiliation"] = True
        authors = services(ctx)["author"].get_all_authors(filters)
        output.print_result(
            {"ok": True, "authors": [output.author_to_dict(a) for a in authors], "count": len(authors)},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def search(ctx: typer.Context, query: str, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        authors = services(ctx)["author"].search_authors(query)
        output.print_result(
            {"ok": True, "authors": [output.author_to_dict(a) for a in authors], "count": len(authors)},
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def show(ctx: typer.Context, author_id: int, json: bool = JSON_OPTION):
    flag = as_json(ctx, json)
    try:
        svc = services(ctx)
        author = svc["author"].get_author_by_id(author_id)
        if not author:
            output.error(f"Author with ID {author_id} not found", "NOT_FOUND", flag)
        papers = svc["author"].get_author_papers(author_id)
        output.print_result(
            {
                "ok": True,
                "author": output.author_to_dict(author),
                "papers": [output.paper_to_dict(p) for p in papers],
                "count": len(papers),
            },
            flag,
        )
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def add(
    ctx: typer.Context,
    full_name: str,
    first_name: str | None = typer.Option(None, "--first-name"),
    last_name: str | None = typer.Option(None, "--last-name"),
    email: str | None = typer.Option(None, "--email"),
    personal_url: str | None = typer.Option(None, "--personal-url"),
    faculty_url: str | None = typer.Option(None, "--faculty-url"),
    scholar_url: str | None = typer.Option(None, "--scholar-url"),
    orcid: str | None = typer.Option(None, "--orcid"),
    institution: str | None = typer.Option(None, "--institution"),
    department: str | None = typer.Option(None, "--department"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        data = _author_data(full_name, first_name, last_name, email, personal_url, faculty_url, scholar_url, orcid, institution, department)
        author = services(ctx)["author"].add_author(data)
        output.print_result({"ok": True, "author": output.author_to_dict(author)}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def edit(
    ctx: typer.Context,
    author_id: int,
    full_name: str | None = typer.Option(None, "--full-name"),
    first_name: str | None = typer.Option(None, "--first-name"),
    last_name: str | None = typer.Option(None, "--last-name"),
    email: str | None = typer.Option(None, "--email"),
    personal_url: str | None = typer.Option(None, "--personal-url"),
    faculty_url: str | None = typer.Option(None, "--faculty-url"),
    scholar_url: str | None = typer.Option(None, "--scholar-url"),
    orcid: str | None = typer.Option(None, "--orcid"),
    institution: str | None = typer.Option(None, "--institution"),
    department: str | None = typer.Option(None, "--department"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        data = {k: v for k, v in {
            "full_name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "personal_url": personal_url,
            "faculty_url": faculty_url,
            "scholar_url": scholar_url,
            "orcid": orcid,
            "institution": institution,
            "department": department,
        }.items() if v is not None}
        author, err = services(ctx)["author"].update_author(author_id, data)
        if not author:
            output.error(err, "NOT_FOUND", flag)
        output.print_result({"ok": True, "author": output.author_to_dict(author)}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def delete(
    ctx: typer.Context,
    author_id: int,
    force: bool = typer.Option(False, "--force", "-f"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        if not services(ctx)["author"].delete_author(author_id, force=force):
            output.error(f"Author with ID {author_id} not found", "NOT_FOUND", flag)
        output.print_result({"ok": True, "message": f"Deleted author {author_id}"}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


@app.command()
def merge(
    ctx: typer.Context,
    target: int = typer.Option(..., "--target"),
    sources: str = typer.Option(..., "--sources"),
    json: bool = JSON_OPTION,
):
    flag = as_json(ctx, json)
    try:
        source_ids = parse_ids(sources)
        author = services(ctx)["author"].merge_authors(target, source_ids)
        output.print_result({"ok": True, "author": output.author_to_dict(author), "merged": source_ids}, flag)
    except Exception as exc:
        handle_exception(exc, flag)


def _author_data(full_name, first_name, last_name, email, personal_url, faculty_url, scholar_url, orcid, institution, department):
    return {
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "personal_url": personal_url,
        "faculty_url": faculty_url,
        "scholar_url": scholar_url,
        "orcid": orcid,
        "institution": institution,
        "department": department,
    }
