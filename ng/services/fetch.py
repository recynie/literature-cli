"""Metadata completion for existing papers."""

from __future__ import annotations

from typing import Any

from ng.services.arxiv_utils import parse_arxiv_id
from ng.services.logger import Logger, NullLogger
from ng.services import openalex, semantic_scholar
from ng.services.utils import normalize_paper_data


class FetchMetadataService:
    """Fetch remote metadata and merge it into an existing paper."""

    def __init__(self, paper_service, metadata_extractor, app: Logger | None = None):
        self.paper_service = paper_service
        self.metadata_extractor = metadata_extractor
        self.app = app or NullLogger()

    def fetch_metadata_for_paper(self, paper, overwrite: bool = False) -> dict[str, Any]:
        if not paper:
            raise ValueError("Paper is required")

        candidates = self._candidate_metadata(paper)
        if not candidates:
            raise ValueError("Cannot fetch metadata without at least a title, DOI, or arXiv ID")

        merged_remote = self._merge_candidates(candidates)
        updates = self._build_updates(paper, merged_remote, overwrite)
        if not updates:
            return {
                "paper": paper,
                "updated": [],
                "metadata": merged_remote,
                "warning": None,
            }

        updated_paper, warning = self.paper_service.update_paper(paper.id, updates)
        if not updated_paper:
            raise ValueError(warning or "Failed to update paper")

        return {
            "paper": updated_paper,
            "updated": sorted(updates.keys()),
            "metadata": merged_remote,
            "warning": warning or None,
        }

    def _candidate_metadata(self, paper) -> list[dict[str, Any]]:
        arxiv_id = parse_arxiv_id(paper)
        if arxiv_id:
            candidates = [self.metadata_extractor.extract_from_arxiv(arxiv_id)]
            doi = getattr(paper, "doi", None)
            if doi:
                candidates += self._safe_s2_doi(doi)
            elif getattr(paper, "title", None):
                candidates += self._safe_s2_title(paper.title)
            return candidates

        doi = getattr(paper, "doi", None)
        if doi:
            candidates = [self.metadata_extractor.extract_from_doi(doi)]
            candidates += self._safe_openalex_doi(doi)
            candidates += self._safe_s2_doi(doi)
            return candidates

        title = (getattr(paper, "title", None) or "").strip()
        if title:
            candidates = self._safe_openalex_title(title)
            candidates += self._safe_s2_title(title)
            return candidates

        return []

    def _merge_candidates(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for candidate in candidates:
            if not candidate:
                continue
            normalized = normalize_paper_data(candidate)
            for key, value in normalized.items():
                if self._has_value(value) and not self._has_value(merged.get(key)):
                    merged[key] = value
        return merged

    def _build_updates(self, paper, metadata: dict[str, Any], overwrite: bool) -> dict[str, Any]:
        fields = [
            "title",
            "abstract",
            "year",
            "venue_full",
            "venue_acronym",
            "paper_type",
            "doi",
            "url",
            "preprint_id",
            "category",
            "volume",
            "issue",
            "pages",
        ]
        updates: dict[str, Any] = {}
        for field in fields:
            value = metadata.get(field)
            if not self._has_value(value):
                continue
            current = getattr(paper, field, None)
            if overwrite or not self._has_value(current):
                updates[field] = value

        authors = metadata.get("authors")
        if self._has_value(authors) and (overwrite or not paper.get_ordered_authors()):
            updates["authors"] = authors
        return updates

    def _safe_openalex_doi(self, doi: str) -> list[dict[str, Any]]:
        return self._safe(lambda: openalex.search_by_doi(doi))

    def _safe_openalex_title(self, title: str) -> list[dict[str, Any]]:
        return self._safe(lambda: openalex.search_by_title(title))

    def _safe_s2_doi(self, doi: str) -> list[dict[str, Any]]:
        return self._safe(lambda: semantic_scholar.search_by_doi(doi))

    def _safe_s2_title(self, title: str) -> list[dict[str, Any]]:
        return self._safe(lambda: semantic_scholar.search_by_title(title))

    def _safe(self, fetcher) -> list[dict[str, Any]]:
        try:
            result = fetcher()
            return [result] if result else []
        except Exception as exc:
            self.app._add_log("metadata_fetch_warning", str(exc))
            return []

    def _has_value(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, dict, set)):
            return bool(value)
        return True
