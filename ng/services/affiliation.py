from __future__ import annotations

from typing import Any, List, Optional

from ng.db.database import get_db_session
from ng.db.models import Affiliation
from ng.services.logger import Logger, NullLogger
from sqlalchemy import or_
from sqlalchemy.orm import joinedload


class AffiliationService:
    """Service for managing affiliations."""

    def __init__(self, app: Logger | None = None):
        self.app = app or NullLogger()

    def get_all_affiliations(self) -> List[Affiliation]:
        with get_db_session() as session:
            affiliations = (
                session.query(Affiliation)
                .options(joinedload(Affiliation.authors))
                .order_by(Affiliation.institution, Affiliation.department)
                .all()
            )
            for affiliation in affiliations:
                _ = affiliation.authors
            session.expunge_all()
            return affiliations

    def get_affiliation_by_id(self, aff_id: int) -> Optional[Affiliation]:
        with get_db_session() as session:
            affiliation = (
                session.query(Affiliation)
                .options(joinedload(Affiliation.authors))
                .filter(Affiliation.id == aff_id)
                .first()
            )
            if affiliation:
                _ = affiliation.authors
                session.expunge(affiliation)
            return affiliation

    def search_affiliations(self, query: str) -> List[Affiliation]:
        with get_db_session() as session:
            affiliations = (
                session.query(Affiliation)
                .options(joinedload(Affiliation.authors))
                .filter(
                    or_(
                        Affiliation.institution.ilike(f"%{query}%"),
                        Affiliation.department.ilike(f"%{query}%"),
                    )
                )
                .order_by(Affiliation.institution, Affiliation.department)
                .all()
            )
            for affiliation in affiliations:
                _ = affiliation.authors
            session.expunge_all()
            return affiliations

    def add_affiliation(self, data: dict[str, Any]) -> Affiliation:
        institution = (data.get("institution") or "").strip()
        if not institution:
            raise ValueError("institution is required")
        department = self._clean_optional(data.get("department"))
        with get_db_session() as session:
            existing = self._find(session, institution, department)
            if existing:
                raise ValueError("Affiliation already exists")
            affiliation = Affiliation(
                institution=institution,
                department=department,
                url=self._clean_optional(data.get("url")),
            )
            session.add(affiliation)
            session.commit()
            session.refresh(affiliation)
            _ = affiliation.authors
            session.expunge(affiliation)
            return affiliation

    def update_affiliation(self, aff_id: int, data: dict[str, Any]) -> tuple[Optional[Affiliation], str]:
        with get_db_session() as session:
            affiliation = session.query(Affiliation).filter(Affiliation.id == aff_id).first()
            if not affiliation:
                return None, f"Affiliation with ID {aff_id} not found"
            for key in ("institution", "department", "url"):
                if key in data:
                    value = data[key]
                    if key == "institution":
                        value = (value or "").strip()
                        if not value:
                            return None, "institution is required"
                    else:
                        value = self._clean_optional(value)
                    setattr(affiliation, key, value)
            session.commit()
            session.refresh(affiliation)
            _ = affiliation.authors
            session.expunge(affiliation)
            return affiliation, ""

    def delete_affiliation(self, aff_id: int, force: bool = False) -> bool:
        with get_db_session() as session:
            affiliation = (
                session.query(Affiliation)
                .options(joinedload(Affiliation.authors))
                .filter(Affiliation.id == aff_id)
                .first()
            )
            if not affiliation:
                return False
            if affiliation.authors and not force:
                raise ValueError("Affiliation has associated authors; use --force to clear links")
            if force:
                for author in affiliation.authors:
                    author.affiliation_id = None
            session.delete(affiliation)
            session.commit()
            return True

    def get_or_create(self, institution: str, department: str | None = None) -> Affiliation:
        institution = (institution or "").strip()
        if not institution:
            raise ValueError("institution is required")
        department = self._clean_optional(department)
        with get_db_session() as session:
            affiliation = self._find(session, institution, department)
            if not affiliation:
                affiliation = Affiliation(institution=institution, department=department)
                session.add(affiliation)
                session.commit()
                session.refresh(affiliation)
            _ = affiliation.authors
            session.expunge(affiliation)
            return affiliation

    @staticmethod
    def _clean_optional(value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    @staticmethod
    def _find(session, institution: str, department: str | None) -> Affiliation | None:
        query = session.query(Affiliation).filter(Affiliation.institution == institution)
        if department is None:
            query = query.filter(Affiliation.department.is_(None))
        else:
            query = query.filter(Affiliation.department == department)
        return query.first()
