"""Output serialization and terminal formatting helpers."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ng.db.models import Affiliation, Author, Collection, Paper


console = Console()


def _iso(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


def paper_to_dict(paper: Paper) -> dict[str, Any]:
    """Convert a detached Paper ORM object to the public JSON schema."""
    ordered_authors = paper.get_ordered_authors()
    pdf_path = paper.pdf_path
    if pdf_path:
        try:
            from ng.services import PDFManager

            pdf_path = PDFManager().get_absolute_path(pdf_path)
        except Exception:
            pass

    return {
        "id": paper.id,
        "title": paper.title,
        "authors": [author.full_name for author in ordered_authors],
        "year": paper.year,
        "venue_full": paper.venue_full,
        "venue_acronym": paper.venue_acronym,
        "paper_type": paper.paper_type,
        "abstract": paper.abstract,
        "notes": paper.notes,
        "doi": paper.doi,
        "preprint_id": paper.preprint_id,
        "category": paper.category,
        "url": paper.url,
        "pdf_path": pdf_path,
        "collections": [collection.name for collection in paper.collections],
        "added_date": _iso(paper.added_date),
        "modified_date": _iso(paper.modified_date),
    }


def affiliation_to_dict(affiliation: Affiliation) -> dict[str, Any]:
    """Convert an Affiliation ORM object to the public JSON schema."""
    try:
        author_count = len(list(getattr(affiliation, "authors", []) or []))
    except Exception:
        author_count = 0
    return {
        "id": affiliation.id,
        "institution": affiliation.institution,
        "department": affiliation.department,
        "url": affiliation.url,
        "author_count": author_count,
    }


def author_to_dict(author: Author) -> dict[str, Any]:
    """Convert an Author ORM object to the public JSON schema."""
    paper_authors = list(getattr(author, "paper_authors", []) or [])
    affiliation = getattr(author, "affiliation", None)
    return {
        "id": author.id,
        "full_name": author.full_name,
        "first_name": author.first_name,
        "last_name": author.last_name,
        "email": author.email,
        "personal_url": author.personal_url,
        "scholar_url": author.scholar_url,
        "orcid": author.orcid,
        "affiliation": affiliation_to_dict(affiliation) if affiliation else None,
        "paper_count": len(paper_authors),
    }


def collection_to_dict(collection: Collection) -> dict[str, Any]:
    """Convert a detached Collection ORM object to the public JSON schema."""
    try:
        paper_count = len(list(getattr(collection, "papers", []) or []))
    except Exception:
        paper_count = 0
    return {
        "id": collection.id,
        "name": collection.name,
        "paper_count": paper_count,
        "created_at": _iso(collection.created_at),
        "last_modified": _iso(collection.last_modified),
    }


def print_result(data: Any, as_json: bool = False):
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
        return
    print_human(data)


def error(message: str, code: str = "INVALID_INPUT", as_json: bool = False):
    print_result({"ok": False, "error": message, "code": code}, as_json)
    raise typer_exit(1)


def typer_exit(code: int):
    try:
        import typer

        return typer.Exit(code)
    except Exception:
        sys.exit(code)


def print_human(data: Any):
    if isinstance(data, Mapping) and "papers" in data:
        _print_paper_table(data.get("papers") or [])
        count = data.get("count", len(data.get("papers") or []))
        console.print(f"{count} paper(s)")
        if data.get("errors"):
            for item in data["errors"]:
                console.print(f"[red]{item}[/red]")
        return

    if isinstance(data, Mapping) and "paper" in data:
        _print_paper_detail(data["paper"])
        if data.get("pdf_error"):
            console.print(f"[yellow]PDF: {data['pdf_error']}[/yellow]")
        return

    if isinstance(data, Mapping) and "authors" in data:
        _print_author_table(data.get("authors") or [])
        return

    if isinstance(data, Mapping) and "author" in data:
        _print_author_detail(data["author"])
        return

    if isinstance(data, Mapping) and "affiliations" in data:
        _print_affiliation_table(data.get("affiliations") or [])
        return

    if isinstance(data, Mapping) and "affiliation" in data:
        _print_affiliation_detail(data["affiliation"])
        return

    if isinstance(data, Mapping) and "collections" in data:
        _print_collection_table(data.get("collections") or [])
        return

    if isinstance(data, Mapping) and "collection" in data:
        _print_collection_detail(data["collection"])
        return

    if isinstance(data, Mapping) and data.get("ok") is False:
        console.print(f"[red]{data.get('error', 'Error')}[/red]")
        return

    if isinstance(data, Mapping) and "message" in data:
        console.print(data["message"])
        return

    if isinstance(data, str):
        console.print(data)
        return

    console.print_json(json.dumps(data, ensure_ascii=False, default=str))


def _print_paper_table(papers: Sequence[Mapping[str, Any]]):
    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Title", overflow="fold")
    table.add_column("Authors", overflow="fold")
    table.add_column("Year", justify="right")
    table.add_column("Venue")

    for paper in papers:
        authors = ", ".join(paper.get("authors") or [])
        venue = paper.get("venue_acronym") or paper.get("venue_full") or ""
        table.add_row(
            str(paper.get("id", "")),
            paper.get("title") or "",
            authors,
            str(paper.get("year") or ""),
            venue,
        )
    console.print(table)


def _print_paper_detail(paper: Mapping[str, Any]):
    authors = ", ".join(paper.get("authors") or [])
    lines = [
        f"[bold]{paper.get('title') or ''}[/bold]",
        f"ID: {paper.get('id')}",
        f"Authors: {authors}",
        f"Year: {paper.get('year') or ''}",
        f"Venue: {paper.get('venue_full') or ''} ({paper.get('venue_acronym') or ''})",
        f"Type: {paper.get('paper_type') or ''}",
    ]
    for key in ("doi", "preprint_id", "url", "pdf_path"):
        if paper.get(key):
            lines.append(f"{key}: {paper[key]}")
    if paper.get("collections"):
        lines.append("Collections: " + ", ".join(paper["collections"]))
    if paper.get("abstract"):
        lines.append("\n[bold]Abstract[/bold]\n" + paper["abstract"])
    if paper.get("notes"):
        lines.append("\n[bold]Notes[/bold]\n" + paper["notes"])
    console.print(Panel("\n".join(lines)))


def _print_author_table(authors: Sequence[Mapping[str, Any]]):
    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("Affiliation")
    table.add_column("Papers", justify="right")
    for author in authors:
        affiliation = author.get("affiliation") or {}
        aff_text = affiliation.get("institution") or ""
        if affiliation.get("department"):
            aff_text += f" / {affiliation['department']}"
        table.add_row(
            str(author.get("id", "")),
            author.get("full_name") or "",
            author.get("email") or "",
            aff_text,
            str(author.get("paper_count") or 0),
        )
    console.print(table)


def _print_author_detail(author: Mapping[str, Any]):
    affiliation = author.get("affiliation") or {}
    lines = [
        f"[bold]{author.get('full_name') or ''}[/bold]",
        f"ID: {author.get('id')}",
        f"First name: {author.get('first_name') or ''}",
        f"Last name: {author.get('last_name') or ''}",
        f"Email: {author.get('email') or ''}",
        f"Personal URL: {author.get('personal_url') or ''}",
        f"Scholar URL: {author.get('scholar_url') or ''}",
        f"ORCID: {author.get('orcid') or ''}",
        f"Affiliation: {affiliation.get('institution') or ''} {affiliation.get('department') or ''}",
        f"Papers: {author.get('paper_count') or 0}",
    ]
    console.print(Panel("\n".join(lines)))


def _print_affiliation_table(affiliations: Sequence[Mapping[str, Any]]):
    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Institution")
    table.add_column("Department")
    table.add_column("Authors", justify="right")
    for affiliation in affiliations:
        table.add_row(
            str(affiliation.get("id", "")),
            affiliation.get("institution") or "",
            affiliation.get("department") or "",
            str(affiliation.get("author_count") or 0),
        )
    console.print(table)


def _print_affiliation_detail(affiliation: Mapping[str, Any]):
    console.print(
        Panel(
            "\n".join(
                [
                    f"[bold]{affiliation.get('institution') or ''}[/bold]",
                    f"ID: {affiliation.get('id')}",
                    f"Department: {affiliation.get('department') or ''}",
                    f"URL: {affiliation.get('url') or ''}",
                    f"Authors: {affiliation.get('author_count') or 0}",
                ]
            )
        )
    )


def _print_collection_table(collections: Sequence[Mapping[str, Any]]):
    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Papers", justify="right")
    for collection in collections:
        table.add_row(
            str(collection.get("id", "")),
            collection.get("name") or "",
            str(collection.get("paper_count") or 0),
        )
    console.print(table)


def _print_collection_detail(collection: Mapping[str, Any]):
    console.print(
        Panel(
            "\n".join(
                [
                    f"[bold]{collection.get('name') or ''}[/bold]",
                    f"ID: {collection.get('id')}",
                    f"Papers: {collection.get('paper_count') or 0}",
                    f"Created: {collection.get('created_at') or ''}",
                ]
            )
        )
    )
