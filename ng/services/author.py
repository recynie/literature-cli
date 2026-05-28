from __future__ import annotations

from typing import Any, List, Optional

from ng.db.database import get_db_session
from ng.db.models import Affiliation, Author, Paper, PaperAuthor
from ng.services.logger import Logger, NullLogger
from sqlalchemy import or_
from sqlalchemy.orm import joinedload


class AuthorService:
    """Service for managing authors independent of papers."""

    def __init__(self, app: Logger | None = None):
        self.app = app or NullLogger()

    def get_all_authors(self, filters: dict[str, Any] | None = None) -> List[Author]:
        with get_db_session() as session:
            query = session.query(Author).options(
                joinedload(Author.affiliation),
                joinedload(Author.paper_authors).joinedload(PaperAuthor.paper),
            )
            query = self._apply_filters(query, filters or {})
            authors = query.order_by(Author.full_name).all()
            self._detach_authors(session, authors)
            return authors

    def get_author_by_id(self, author_id: int) -> Optional[Author]:
        with get_db_session() as session:
            author = (
                session.query(Author)
                .options(
                    joinedload(Author.affiliation),
                    joinedload(Author.paper_authors).joinedload(PaperAuthor.paper),
                )
                .filter(Author.id == author_id)
                .first()
            )
            if author:
                self._detach_authors(session, [author])
            return author

    def search_authors(self, query: str) -> List[Author]:
        with get_db_session() as session:
            authors = (
                session.query(Author)
                .options(
                    joinedload(Author.affiliation),
                    joinedload(Author.paper_authors).joinedload(PaperAuthor.paper),
                )
                .filter(
                    or_(
                        Author.full_name.ilike(f"%{query}%"),
                        Author.first_name.ilike(f"%{query}%"),
                        Author.last_name.ilike(f"%{query}%"),
                    )
                )
                .order_by(Author.full_name)
                .all()
            )
            self._detach_authors(session, authors)
            return authors

    def add_author(self, data: dict[str, Any]) -> Author:
        full_name = (data.get("full_name") or "").strip()
        if not full_name:
            raise ValueError("full_name is required")
        with get_db_session() as session:
            author = Author(full_name=full_name)
            self._assign_simple_fields(author, data)
            affiliation = self._resolve_affiliation(session, data)
            if affiliation:
                author.affiliation = affiliation
            session.add(author)
            session.commit()
            session.refresh(author)
            self._detach_authors(session, [author])
            return author

    def update_author(self, author_id: int, data: dict[str, Any]) -> tuple[Optional[Author], str]:
        with get_db_session() as session:
            author = session.query(Author).filter(Author.id == author_id).first()
            if not author:
                return None, f"Author with ID {author_id} not found"
            self._assign_simple_fields(author, data, partial=True)
            if "institution" in data or "department" in data:
                institution = data.get("institution")
                department = data.get("department")
                if institution is None:
                    institution = author.affiliation.institution if author.affiliation else None
                if self._clean_optional(institution) is None:
                    author.affiliation = None
                else:
                    author.affiliation = self._resolve_affiliation(
                        session, {"institution": institution, "department": department}
                    )
            session.commit()
            session.refresh(author)
            self._detach_authors(session, [author])
            return author, ""

    def delete_author(self, author_id: int, force: bool = False) -> bool:
        with get_db_session() as session:
            author = (
                session.query(Author)
                .options(joinedload(Author.paper_authors))
                .filter(Author.id == author_id)
                .first()
            )
            if not author:
                return False
            if author.paper_authors and not force:
                raise ValueError("Author has associated papers; use --force to remove links")
            session.delete(author)
            session.commit()
            return True

    def merge_authors(self, target_id: int, source_ids: List[int]) -> Author:
        with get_db_session() as session:
            target = session.query(Author).filter(Author.id == target_id).first()
            if not target:
                raise ValueError(f"Target author with ID {target_id} not found")
            sources = session.query(Author).filter(Author.id.in_(source_ids)).all()
            if len(sources) != len(set(source_ids)):
                raise ValueError("One or more source authors were not found")
            for source in sources:
                if source.id == target.id:
                    raise ValueError("Target author cannot be a source")
                self._fill_missing_fields(target, source)
                for paper_author in list(source.paper_authors):
                    existing = (
                        session.query(PaperAuthor)
                        .filter(
                            PaperAuthor.paper_id == paper_author.paper_id,
                            PaperAuthor.author_id == target.id,
                        )
                        .first()
                    )
                    if existing:
                        session.delete(paper_author)
                    else:
                        paper_author.author = target
                session.delete(source)
            session.commit()
            session.refresh(target)
            target = (
                session.query(Author)
                .options(
                    joinedload(Author.affiliation),
                    joinedload(Author.paper_authors).joinedload(PaperAuthor.paper),
                )
                .filter(Author.id == target_id)
                .first()
            )
            self._detach_authors(session, [target])
            return target

    def get_author_papers(self, author_id: int) -> List[Paper]:
        with get_db_session() as session:
            papers = (
                session.query(Paper)
                .join(Paper.paper_authors)
                .join(PaperAuthor.author)
                .options(
                    joinedload(Paper.paper_authors).joinedload(PaperAuthor.author),
                    joinedload(Paper.collections),
                )
                .filter(Author.id == author_id)
                .order_by(Paper.added_date.desc())
                .all()
            )
            for paper in papers:
                _ = paper.paper_authors
                _ = paper.collections
            session.expunge_all()
            return papers

    def _apply_filters(self, query, filters: dict[str, Any]):
        if filters.get("institution"):
            query = query.join(Author.affiliation).filter(
                Affiliation.institution.ilike(f"%{filters['institution']}%")
            )
        if filters.get("department"):
            if "institution" not in filters:
                query = query.join(Author.affiliation)
            query = query.filter(Affiliation.department.ilike(f"%{filters['department']}%"))
        if filters.get("has_email"):
            query = query.filter(Author.email.isnot(None), Author.email != "")
        if filters.get("has_url"):
            query = query.filter(Author.personal_url.isnot(None), Author.personal_url != "")
        if filters.get("no_affiliation"):
            query = query.filter(Author.affiliation_id.is_(None))
        return query

    def _resolve_affiliation(self, session, data: dict[str, Any]) -> Affiliation | None:
        institution = self._clean_optional(data.get("institution"))
        if institution is None:
            return None
        department = self._clean_optional(data.get("department"))
        query = session.query(Affiliation).filter(Affiliation.institution == institution)
        query = query.filter(Affiliation.department.is_(None) if department is None else Affiliation.department == department)
        affiliation = query.first()
        if not affiliation:
            affiliation = Affiliation(institution=institution, department=department)
            session.add(affiliation)
            session.flush()
        return affiliation

    def _assign_simple_fields(self, author: Author, data: dict[str, Any], partial: bool = False) -> None:
        fields = ("full_name", "first_name", "last_name", "email", "personal_url", "scholar_url", "orcid")
        for field in fields:
            if field in data:
                value = self._clean_optional(data[field])
                if field == "full_name" and value is None:
                    raise ValueError("full_name is required")
                setattr(author, field, value)
            elif not partial and field != "full_name":
                setattr(author, field, self._clean_optional(data.get(field)))

    def _fill_missing_fields(self, target: Author, source: Author) -> None:
        for field in ("first_name", "last_name", "email", "personal_url", "scholar_url", "orcid", "affiliation_id"):
            if getattr(target, field) in (None, "") and getattr(source, field) not in (None, ""):
                setattr(target, field, getattr(source, field))

    @staticmethod
    def _clean_optional(value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _detach_authors(session, authors: list[Author]) -> None:
        for author in authors:
            _ = author.affiliation
            _ = author.paper_authors
            for paper_author in author.paper_authors:
                _ = paper_author.paper
        session.expunge_all()
