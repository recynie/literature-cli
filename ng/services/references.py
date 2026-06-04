"""Crossref reference retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests
from fuzzywuzzy import fuzz

from ng.services import http_utils
from ng.services.logger import Logger, NullLogger


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
REFERENCE_FIELDS = [
    "DOI",
    "author",
    "article-title",
    "journal-title",
    "year",
    "volume",
    "issue",
    "first-page",
    "unstructured",
    "key",
]
TITLE_MATCH_MIN_SCORE = 85
TITLE_MATCH_AMBIGUOUS_GAP = 3
TITLE_MATCH_TOP_ROWS = 5


class ReferenceError(ValueError):
    """Typed error for reference retrieval failures."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CrossrefTitleMatch:
    doi: str
    title: str | None
    score: float | None
    similarity: int
    year: int | None
    author_tokens: tuple[str, ...]
    composite_score: int


class ReferenceService:
    """Fetch paper reference lists from Crossref."""

    def __init__(self, paper_service, app: Logger | None = None):
        self.paper_service = paper_service
        self.app = app or NullLogger()

    def references_for_paper(self, paper_id: int) -> dict[str, Any]:
        paper = self.paper_service.get_paper_by_id(paper_id)
        if not paper:
            raise ReferenceError(f"Paper with ID {paper_id} not found", "NOT_FOUND")

        source: dict[str, Any] = {"paper_id": paper.id, "title": paper.title}
        doi = _clean_doi(getattr(paper, "doi", None))
        if doi:
            source["doi"] = doi
            return self.references_for_doi(doi, source=source)

        title = (getattr(paper, "title", None) or "").strip()
        if not title:
            raise ReferenceError(
                "Cannot fetch references without a DOI or title",
                "INVALID_INPUT",
            )

        result = self.references_for_title(
            title,
            source=source,
            expected_year=getattr(paper, "year", None),
            expected_authors=[author.full_name for author in paper.get_ordered_authors()],
        )
        result["warning"] = _combine_warnings(
            result.get("warning"),
            "Paper has no DOI; matched Crossref work by title before fetching references",
        )
        return result

    def references_for_doi(
        self, doi: str, source: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        doi = _clean_doi(doi)
        if not doi:
            raise ReferenceError("DOI is required", "INVALID_INPUT")

        work = self._fetch_work_by_doi(doi)
        return self._build_result(work, {**(source or {}), "doi": doi}, None)

    def references_for_title(
        self,
        title: str,
        source: dict[str, Any] | None = None,
        expected_year: int | None = None,
        expected_authors: list[str] | None = None,
    ) -> dict[str, Any]:
        title = (title or "").strip()
        if not title:
            raise ReferenceError("Title is required", "INVALID_INPUT")

        matches = self._find_works_by_title(
            title,
            expected_year=expected_year,
            expected_authors=expected_authors,
        )
        best = matches[0]
        warning = self._title_match_warning(title, matches)

        full_work = self._fetch_work_by_doi(best.doi)
        matched = {
            "doi": best.doi,
            "title": _first(full_work.get("title")) or best.title,
            "score": best.score,
            "similarity": best.similarity,
            "year": best.year,
            "composite_score": best.composite_score,
        }
        return self._build_result(full_work, source or {"title": title}, matched, warning=warning)

    def _fetch_work_by_doi(self, doi: str) -> dict[str, Any]:
        try:
            response = http_utils.get(
                f"{CROSSREF_WORKS_URL}/{doi}",
                headers=_crossref_headers(),
                timeout=10,
            )
            work = response.json().get("message") or {}
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404:
                raise ReferenceError(
                    f"Crossref work not found for DOI {doi}", "NOT_FOUND"
                ) from exc
            if status == 429:
                raise ReferenceError(
                    f"Crossref rate limit reached while fetching DOI {doi}",
                    "NETWORK_ERROR",
                ) from exc
            raise ReferenceError(
                f"Crossref HTTP {status or 'error'} while fetching DOI {doi}",
                "NETWORK_ERROR",
            ) from exc
        except requests.Timeout as exc:
            raise ReferenceError(
                f"Crossref request timed out while fetching DOI {doi}",
                "NETWORK_ERROR",
            ) from exc
        except requests.RequestException as exc:
            raise ReferenceError(
                f"Failed to fetch Crossref work for DOI {doi}: {exc}",
                "NETWORK_ERROR",
            ) from exc

        if not work:
            raise ReferenceError(f"Crossref work not found for DOI {doi}", "NOT_FOUND")
        return work

    def _find_works_by_title(
        self,
        title: str,
        expected_year: int | None = None,
        expected_authors: list[str] | None = None,
    ) -> list[CrossrefTitleMatch]:
        try:
            response = http_utils.get(
                CROSSREF_WORKS_URL,
                headers=_crossref_headers(),
                params={"query.bibliographic": title, "rows": TITLE_MATCH_TOP_ROWS},
                timeout=10,
            )
            items = (response.json().get("message") or {}).get("items") or []
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 429:
                raise ReferenceError(
                    "Crossref rate limit reached while searching by title",
                    "NETWORK_ERROR",
                ) from exc
            raise ReferenceError(
                f"Crossref HTTP {status or 'error'} while searching by title",
                "NETWORK_ERROR",
            ) from exc
        except requests.Timeout as exc:
            raise ReferenceError(
                "Crossref request timed out while searching by title",
                "NETWORK_ERROR",
            ) from exc
        except requests.RequestException as exc:
            raise ReferenceError(
                f"Failed to search Crossref by title: {exc}",
                "NETWORK_ERROR",
            ) from exc

        if not items:
            raise ReferenceError("No Crossref work found for title", "NOT_FOUND")

        matches = [
            self._to_title_match(
                title,
                item,
                expected_year=expected_year,
                expected_authors=expected_authors,
            )
            for item in items
            if _clean_doi(item.get("DOI"))
        ]
        if not matches:
            raise ReferenceError(
                "Crossref title matches did not include a DOI",
                "NOT_FOUND",
            )

        matches.sort(
            key=lambda item: (item.composite_score, item.similarity, item.score or 0),
            reverse=True,
        )
        best = matches[0]
        if best.similarity < TITLE_MATCH_MIN_SCORE:
            raise ReferenceError(
                f"Crossref title match too weak (similarity {best.similarity}) for '{title}'",
                "NOT_FOUND",
            )
        return matches

    def _to_title_match(
        self,
        query_title: str,
        item: dict[str, Any],
        expected_year: int | None = None,
        expected_authors: list[str] | None = None,
    ) -> CrossrefTitleMatch:
        matched_title = _first(item.get("title"))
        similarity = fuzz.token_set_ratio(query_title.lower(), (matched_title or "").lower())
        year = _extract_work_year(item)
        author_tokens = _extract_author_tokens(item)
        composite_score = similarity

        if expected_year is not None and year is not None:
            if year == expected_year:
                composite_score += 10
            elif abs(year - expected_year) == 1:
                composite_score += 4
            else:
                composite_score -= min(12, abs(year - expected_year) * 2)

        expected_author_tokens = _normalize_author_tokens(expected_authors or [])
        if expected_author_tokens and author_tokens:
            overlap = len(set(expected_author_tokens) & set(author_tokens))
            composite_score += min(12, overlap * 4)

        return CrossrefTitleMatch(
            doi=_clean_doi(item.get("DOI")),
            title=matched_title,
            score=item.get("score"),
            similarity=similarity,
            year=year,
            author_tokens=author_tokens,
            composite_score=composite_score,
        )

    def _title_match_warning(
        self, query_title: str, matches: list[CrossrefTitleMatch]
    ) -> str | None:
        if not matches:
            return None
        best = matches[0]
        warnings: list[str] = []
        if best.similarity < 95:
            warnings.append(
                f"Crossref title match used heuristic similarity {best.similarity} for '{query_title}'"
            )
        if best.composite_score != best.similarity:
            warnings.append(
                f"Crossref title ranking used year/author hints (composite score {best.composite_score})"
            )
        if len(matches) > 1:
            second = matches[1]
            gap = best.composite_score - second.composite_score
            if gap <= TITLE_MATCH_AMBIGUOUS_GAP and second.similarity >= TITLE_MATCH_MIN_SCORE:
                warnings.append(
                    "Crossref title search was ambiguous; selected the highest-similarity DOI among close matches"
                )
        return "; ".join(warnings) if warnings else None

    def _build_result(
        self,
        work: dict[str, Any],
        source: dict[str, Any],
        matched: dict[str, Any] | None,
        warning: str | None = None,
    ) -> dict[str, Any]:
        references = [_reference_to_dict(item) for item in work.get("reference") or []]
        result_warning = warning
        if not references:
            result_warning = _combine_warnings(
                result_warning,
                "Crossref returned no structured references for this work",
            )
        return {
            "source": {
                **source,
                "crossref_doi": _clean_doi(work.get("DOI")),
                "crossref_title": _first(work.get("title")),
            },
            "matched": matched,
            "references": references,
            "count": len(references),
            "warning": result_warning,
        }


def _reference_to_dict(reference: dict[str, Any]) -> dict[str, Any]:
    data = {field: reference.get(field) for field in REFERENCE_FIELDS}
    data["raw"] = dict(reference)
    return data


def _clean_doi(doi: str | None) -> str:
    doi = (doi or "").strip()
    if not doi:
        return ""
    if doi.lower().startswith("http"):
        match = re.search(r"10\.\d+/[^\s]+", doi)
        doi = match.group(0) if match else doi
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    return doi.strip()


def _first(value: Any) -> str | None:
    if isinstance(value, list):
        return value[0] if value else None
    return value if isinstance(value, str) else None


def _crossref_headers() -> dict[str, str]:
    return {
        "User-Agent": "LiteratureCLI/0.1 (https://github.com/SXKDZ/LiteratureCLI; mailto:litcli@example.com)"
    }


def _extract_work_year(item: dict[str, Any]) -> int | None:
    for key in ("published-print", "published-online", "issued"):
        date_part = item.get(key) or {}
        parts = date_part.get("date-parts") or []
        if parts and parts[0]:
            year = parts[0][0]
            if isinstance(year, int):
                return year
    return None


def _extract_author_tokens(item: dict[str, Any]) -> tuple[str, ...]:
    tokens: list[str] = []
    for author in item.get("author") or []:
        family = (author.get("family") or "").strip().lower()
        if family:
            tokens.append(family)
    return tuple(tokens)


def _normalize_author_tokens(authors: list[str]) -> tuple[str, ...]:
    tokens: list[str] = []
    for author in authors:
        parts = [part.strip().lower() for part in str(author).split() if part.strip()]
        if parts:
            tokens.append(parts[-1])
    return tuple(tokens)


def _combine_warnings(existing: str | None, extra: str | None) -> str | None:
    parts = [part for part in (existing, extra) if part]
    return "; ".join(parts) if parts else None
