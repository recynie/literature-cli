"""Semantic Scholar API wrapper."""

from __future__ import annotations

import os
import time
from typing import Any

from ng.services import http_utils
from ng.services.utils import normalize_paper_data


BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = ",".join(
    [
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "publicationVenue",
        "publicationTypes",
        "journal",
        "externalIds",
        "url",
        "openAccessPdf",
    ]
)
_last_request_time = 0.0


def search_by_doi(doi: str) -> dict[str, Any] | None:
    doi = _clean_doi(doi)
    if not doi:
        return None
    data = _get(f"{BASE_URL}/paper/DOI:{doi}", params={"fields": FIELDS})
    return _paper_to_metadata(data)


def search_by_title(title: str) -> dict[str, Any] | None:
    title = (title or "").strip()
    if not title:
        return None
    data = _get(
        f"{BASE_URL}/paper/search",
        params={"query": title, "limit": 1, "fields": FIELDS},
    )
    papers = data.get("data") or []
    if not papers:
        return None
    return _paper_to_metadata(papers[0])


def get_pdf_url(identifier: str) -> str | None:
    metadata = search_by_doi(identifier)
    return metadata.get("pdf_url") if metadata else None


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    global _last_request_time
    if not os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
        elapsed = time.time() - _last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
    headers = {}
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    response = http_utils.get(url, params=params, headers=headers, timeout=30)
    _last_request_time = time.time()
    return response.json()


def _clean_doi(doi: str) -> str:
    doi = (doi or "").strip()
    if doi.lower().startswith("https://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("http://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("doi:"):
        return doi[4:].strip()
    return doi


def _paper_to_metadata(paper: dict[str, Any]) -> dict[str, Any] | None:
    if not paper:
        return None
    external_ids = paper.get("externalIds") or {}
    journal = paper.get("journal") or {}
    publication_venue = paper.get("publicationVenue") or {}
    metadata = {
        "title": paper.get("title") or "Unknown Title",
        "abstract": paper.get("abstract") or "",
        "authors": [
            {"full_name": author.get("name")}
            for author in paper.get("authors") or []
            if author.get("name")
        ],
        "year": paper.get("year"),
        "venue_full": publication_venue.get("name")
        or paper.get("venue")
        or journal.get("name")
        or "",
        "venue_acronym": "",
        "paper_type": _paper_type(paper.get("publicationTypes")),
        "doi": external_ids.get("DOI"),
        "preprint_id": _preprint_id(external_ids),
        "url": paper.get("url"),
        "volume": journal.get("volume"),
        "pages": journal.get("pages"),
        "semantic_scholar_id": paper.get("paperId"),
        "pdf_url": (paper.get("openAccessPdf") or {}).get("url"),
    }
    return normalize_paper_data(metadata)


def _paper_type(publication_types: list[str] | None) -> str:
    values = {value.lower() for value in publication_types or []}
    if "journalarticle" in values:
        return "journal"
    if "conference" in values:
        return "conference"
    if "review" in values:
        return "review"
    return "unknown"


def _preprint_id(external_ids: dict[str, Any]) -> str | None:
    arxiv_id = external_ids.get("ArXiv")
    return f"arXiv {arxiv_id}" if arxiv_id else None
