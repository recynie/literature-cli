"""Paper search and filtering service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

from fuzzywuzzy import fuzz
from ng.db.database import get_db_manager, get_db_session
from ng.db.models import Affiliation, Author, Collection, Paper, PaperAuthor
from ng.services.logger import Logger, NullLogger
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload


# Default search sources
DEFAULT_SEARCH_SOURCES = ["title", "abstract", "body", "summary"]


def _count_matches_in_file(filepath: str, query: str) -> int:
    """Count case-insensitive substring occurrences of *query* in *filepath*.

    Returns 0 if the file does not exist or cannot be read.
    """
    q = query.lower()
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read().lower().count(q)
    except (FileNotFoundError, OSError):
        return 0


@dataclass
class SearchMatch:
    """One paper matched during a search, with per-field hit info."""

    paper: Paper
    matched_fields: dict[str, int]  # field_name -> hit count

    @property
    def total_hits(self) -> int:
        return sum(self.matched_fields.values())


class SearchService:
    """Service for searching and filtering papers."""

    def __init__(self, app: Logger | None = None):
        self.app = app or NullLogger()

    def search_papers(
        self, query: str, sources: list[str] | None = None
    ) -> list[SearchMatch]:
        """Search papers by query in specified sources.

        Args:
            query: Search string.
            sources: Which fields/sources to search.
                     Defaults to [\"title\", \"abstract\", \"body\", \"summary\"].

        Returns:
            List of SearchMatch objects, ordered by total_hits descending.
        """
        if sources is None:
            sources = list(DEFAULT_SEARCH_SOURCES)

        query_lower = query.lower()

        with get_db_session() as session:
            # --- Stage 1: database-level conditions (metadata fields) ---
            db_conditions = []

            if "title" in sources:
                db_conditions.append(Paper.title.ilike(f"%{query}%"))
            if "abstract" in sources:
                db_conditions.append(Paper.abstract.ilike(f"%{query}%"))
            if "venue" in sources:
                db_conditions.append(
                    or_(
                        Paper.venue_full.ilike(f"%{query}%"),
                        Paper.venue_acronym.ilike(f"%{query}%"),
                    )
                )
            if "notes" in sources:
                db_conditions.append(Paper.notes.ilike(f"%{query}%"))
            if "authors" in sources:
                papers_by_author = (
                    session.query(Paper)
                    .join(Paper.paper_authors)
                    .join(PaperAuthor.author)
                    .filter(Author.full_name.ilike(f"%{query}%"))
                    .all()
                )
                paper_ids = [p.id for p in papers_by_author]
                if paper_ids:
                    db_conditions.append(Paper.id.in_(paper_ids))

            # Load all papers if we need file-level search (body/summary)
            need_body = "body" in sources
            need_summary = "summary" in sources
            need_file_search = need_body or need_summary

            if need_file_search:
                all_papers = (
                    session.query(Paper)
                    .options(
                        joinedload(Paper.paper_authors).joinedload(PaperAuthor.author),
                        joinedload(Paper.collections),
                    )
                    .all()
                )
                for p in all_papers:
                    _ = p.paper_authors
                    _ = p.collections
                session.expunge_all()
                candidate_papers = all_papers
            elif db_conditions:
                candidate_papers = (
                    session.query(Paper)
                    .options(
                        joinedload(Paper.paper_authors).joinedload(PaperAuthor.author),
                        joinedload(Paper.collections),
                    )
                    .filter(or_(*db_conditions))
                    .order_by(Paper.added_date.desc())
                    .all()
                )
                for p in candidate_papers:
                    _ = p.paper_authors
                    _ = p.collections
                session.expunge_all()
            else:
                return []

        # --- Stage 2: per-paper matching (count hits per field) ---
        results: list[SearchMatch] = []
        for paper in candidate_papers:
            matched: dict[str, int] = {}

            if "title" in sources and paper.title:
                c = paper.title.lower().count(query_lower)
                if c:
                    matched["title"] = c

            if "abstract" in sources and paper.abstract:
                c = paper.abstract.lower().count(query_lower)
                if c:
                    matched["abstract"] = c

            if "venue" in sources:
                c = 0
                if paper.venue_full:
                    c += paper.venue_full.lower().count(query_lower)
                if paper.venue_acronym:
                    c += paper.venue_acronym.lower().count(query_lower)
                if c:
                    matched["venue"] = c

            if "notes" in sources and paper.notes:
                c = paper.notes.lower().count(query_lower)
                if c:
                    matched["notes"] = c

            if "authors" in sources:
                c = sum(
                    query_lower in a.full_name.lower()
                    for a in paper.get_ordered_authors()
                )
                if c:
                    matched["authors"] = c

            # Body: search MinerU parsed Markdown
            if need_body and paper.parsed_pdf_path:
                data_dir = os.path.dirname(get_db_manager().db_path)
                md_path = os.path.join(data_dir, paper.parsed_pdf_path)
                c = _count_matches_in_file(md_path, query)
                if c:
                    matched["body"] = c

            # Summary: currently stored in notes (set by --summarize)
            if need_summary:
                if paper.notes:
                    c = paper.notes.lower().count(query_lower)
                    if c:
                        matched["summary"] = c

            if matched:
                results.append(SearchMatch(paper=paper, matched_fields=matched))

        # Sort by total hits descending, then by year descending
        results.sort(key=lambda m: (-m.total_hits, -(m.paper.year or 0)))

        self.app._add_log(
            "search_query",
            f"Search '{query}' in sources {sources} -> {len(results)} result(s)",
        )
        return results

    def fuzzy_search_papers(self, query: str, threshold: int = 60) -> list[Paper]:
        """Fuzzy search papers using edit distance."""
        with get_db_session() as session:
            all_papers = (
                session.query(Paper)
                .options(
                    joinedload(Paper.paper_authors).joinedload(PaperAuthor.author),
                    joinedload(Paper.collections),
                )
                .all()
            )

            scored_papers = []

            for paper in all_papers:
                _ = paper.paper_authors
                _ = paper.collections

                title_score = fuzz.partial_ratio(query.lower(), paper.title.lower())
                ordered_authors = paper.get_ordered_authors()
                author_score = max(
                    [
                        fuzz.partial_ratio(query.lower(), author.full_name.lower())
                        for author in ordered_authors
                    ]
                    or [0]
                )
                venue_score = max(
                    [
                        (
                            fuzz.partial_ratio(query.lower(), paper.venue_full.lower())
                            if paper.venue_full
                            else 0
                        ),
                        (
                            fuzz.partial_ratio(
                                query.lower(), paper.venue_acronym.lower()
                            )
                            if paper.venue_acronym
                            else 0
                        ),
                    ]
                )

                max_score = max(title_score, author_score, venue_score)

                if max_score >= threshold:
                    scored_papers.append((paper, max_score))

            scored_papers.sort(key=lambda x: x[1], reverse=True)

            session.expunge_all()
            results = [paper for paper, score in scored_papers]
            self.app._add_log(
                "search_fuzzy",
                f"Fuzzy search '{query}' (threshold={threshold}) -> {len(results)} result(s)",
            )
            return results

    def filter_papers(self, filters: Dict[str, Any]) -> List[Paper]:
        """Filter papers by various criteria."""
        with get_db_session() as session:
            query = session.query(Paper).options(
                joinedload(Paper.paper_authors).joinedload(PaperAuthor.author),
                joinedload(Paper.collections),
            )

            if "all" in filters:
                search_term = filters["all"]
                query = query.filter(
                    or_(
                        Paper.title.ilike(f"%{search_term}%"),
                        Paper.abstract.ilike(f"%{search_term}%"),
                        Paper.venue_full.ilike(f"%{search_term}%"),
                        Paper.venue_acronym.ilike(f"%{search_term}%"),
                        Paper.paper_authors.any(
                            Author.full_name.ilike(f"%{search_term}%")
                        ),
                    )
                )

            if "year" in filters:
                query = query.filter(Paper.year == filters["year"])

            if "year_range" in filters:
                start, end = filters["year_range"]
                query = query.filter(and_(Paper.year >= start, Paper.year <= end))

            if "paper_type" in filters:
                query = query.filter(Paper.paper_type == filters["paper_type"])

            if "venue" in filters:
                query = query.filter(
                    or_(
                        Paper.venue_full.ilike(f'%{filters["venue"]}%'),
                        Paper.venue_acronym.ilike(f'%{filters["venue"]}%'),
                    )
                )

            if "collection" in filters:
                query = query.join(Paper.collections).filter(
                    Collection.name == filters["collection"]
                )

            if "author" in filters:
                query = (
                    query.join(Paper.paper_authors)
                    .join(PaperAuthor.author)
                    .filter(Author.full_name.ilike(f'%{filters["author"]}%'))
                )

            if "affiliation" in filters:
                query = (
                    query.join(Paper.paper_authors)
                    .join(PaperAuthor.author)
                    .outerjoin(Author.affiliation)
                    .filter(
                        or_(
                            Affiliation.institution.ilike(f'%{filters["affiliation"]}%'),
                            Affiliation.department.ilike(f'%{filters["affiliation"]}%'),
                        )
                    )
                )

            papers = query.order_by(Paper.added_date.desc()).all()

            for paper in papers:
                _ = paper.paper_authors
                _ = paper.collections

            session.expunge_all()
            self.app._add_log(
                "search_filter",
                f"Applied filters {filters} -> {len(papers)} result(s)",
            )
            return papers
