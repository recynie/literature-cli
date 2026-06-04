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
from ng.services.platform_ids import (
    arxiv_url,
    dblp_url_from_key,
    dblp_url_from_pid,
    openalex_url,
    openreview_url,
    orcid_url,
    semantic_scholar_author_url,
    semantic_scholar_paper_url,
)


console = Console()


def _iso(value: Any) -> str | None:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return None


def paper_to_dict(paper: Paper, use_keys: bool = False) -> dict[str, Any]:
    """Convert a detached Paper ORM object to the public JSON schema."""
    ordered_authors = paper.get_ordered_authors()
    pdf_path = paper.pdf_path
    if pdf_path:
        try:
            from ng.services import PDFManager

            pdf_path = PDFManager().get_absolute_path(pdf_path)
        except Exception:
            pass

    data = {
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
        "category": paper.category,
        "url": paper.url,
        "pdf_path": pdf_path,
        "collections": [collection.name for collection in paper.collections],
        "added_date": _iso(paper.added_date),
        "modified_date": _iso(paper.modified_date),
    }
    if use_keys:
        data.update({
            "arxiv_id": paper.arxiv_id,
            "openreview_id": paper.openreview_id,
            "dblp_key": paper.dblp_key,
            "openalex_id": paper.openalex_id,
            "semantic_scholar_id": paper.semantic_scholar_id,
        })
    else:
        data.update({
            "arxiv_url": arxiv_url(paper.arxiv_id) if paper.arxiv_id else None,
            "openreview_url": openreview_url(paper.openreview_id) if paper.openreview_id else None,
            "dblp_url": dblp_url_from_key(paper.dblp_key) if paper.dblp_key else None,
            "openalex_url": openalex_url(paper.openalex_id) if paper.openalex_id else None,
            "semantic_scholar_url": semantic_scholar_paper_url(paper.semantic_scholar_id) if paper.semantic_scholar_id else None,
        })
    return data


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


def author_to_dict(author: Author, use_keys: bool = False) -> dict[str, Any]:
    """Convert an Author ORM object to the public JSON schema."""
    paper_authors = list(getattr(author, "paper_authors", []) or [])
    affiliation = getattr(author, "affiliation", None)
    data = {
        "id": author.id,
        "full_name": author.full_name,
        "first_name": author.first_name,
        "last_name": author.last_name,
        "email": author.email,
        "personal_url": author.personal_url,
        "faculty_url": author.faculty_url,
        "scholar_url": author.scholar_url,
        "affiliation": affiliation_to_dict(affiliation) if affiliation else None,
        "paper_count": len(paper_authors),
    }
    if use_keys:
        data.update({
            "orcid": author.orcid,
            "openalex_id": author.openalex_id,
            "semantic_scholar_id": author.semantic_scholar_id,
            "dblp_pid": author.dblp_pid,
        })
    else:
        data.update({
            "orcid_url": orcid_url(author.orcid) if author.orcid else None,
            "openalex_url": openalex_url(author.openalex_id) if author.openalex_id else None,
            "semantic_scholar_url": semantic_scholar_author_url(author.semantic_scholar_id) if author.semantic_scholar_id else None,
            "dblp_url": dblp_url_from_pid(author.dblp_pid) if author.dblp_pid else None,
        })
    return data


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

    if isinstance(data, Mapping) and "references" in data:
        _print_reference_table(data)
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
    for key in (
        "doi",
        "arxiv_id",
        "arxiv_url",
        "openreview_id",
        "openreview_url",
        "dblp_key",
        "dblp_url",
        "openalex_id",
        "openalex_url",
        "semantic_scholar_id",
        "semantic_scholar_url",
        "url",
        "pdf_path",
    ):
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
        f"Faculty URL: {author.get('faculty_url') or ''}",
        f"Scholar URL: {author.get('scholar_url') or ''}",
        f"ORCID: {author.get('orcid') or author.get('orcid_url') or ''}",
        f"OpenAlex: {author.get('openalex_id') or author.get('openalex_url') or ''}",
        f"Semantic Scholar: {author.get('semantic_scholar_id') or author.get('semantic_scholar_url') or ''}",
        f"DBLP: {author.get('dblp_pid') or author.get('dblp_url') or ''}",
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


def _print_reference_table(data: Mapping[str, Any]):
    source = data.get("source") or {}
    source_label = (
        source.get("crossref_title")
        or source.get("title")
        or source.get("doi")
        or source.get("crossref_doi")
        or "Crossref work"
    )
    console.print(f"[bold]{source_label}[/bold]")
    if source.get("crossref_doi"):
        console.print(f"DOI: {source['crossref_doi']}")
    if data.get("matched"):
        matched = data["matched"]
        console.print(
            f"Matched: {matched.get('title') or ''} ({matched.get('doi') or ''})"
        )
    if data.get("warning"):
        console.print(f"[yellow]{data['warning']}[/yellow]")
    if data.get("error"):
        console.print(f"[red]{data['error']}[/red]")
    if data.get("code"):
        console.print(f"Code: {data['code']}")
    if data.get("available_matches"):
        console.print("[dim]Alternative title matches:[/dim]")
        for match in data["available_matches"]:
            console.print(
                f"[dim]- {match.get('title') or ''} ({match.get('doi') or ''}) similarity={match.get('similarity') if match.get('similarity') is not None else ''}[/dim]"
            )

    table = Table(show_lines=False)
    table.add_column("#", justify="right")
    table.add_column("Title", overflow="fold")
    table.add_column("Author", overflow="fold")
    table.add_column("Year", justify="right")
    table.add_column("DOI")

    for index, ref in enumerate(data.get("references") or [], start=1):
        title = ref.get("article-title") or ref.get("unstructured") or ""
        table.add_row(
            str(index),
            title,
            ref.get("author") or "",
            str(ref.get("year") or ""),
            ref.get("DOI") or "",
        )
    console.print(table)
    console.print(f"{data.get('count', 0)} reference(s)")
