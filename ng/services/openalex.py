"""OpenAlex API wrapper."""

from __future__ import annotations

import os
from typing import Any

from ng.services import http_utils
from ng.services.utils import normalize_paper_data


BASE_URL = "https://api.openalex.org/works"


def search_by_doi(doi: str) -> dict[str, Any] | None:
    doi = _clean_doi(doi)
    if not doi:
        return None
    url = f"{BASE_URL}/doi:{doi}"
    response = http_utils.get(url, params=_params(), timeout=30)
    return _work_to_metadata(response.json())


def search_by_title(title: str) -> dict[str, Any] | None:
    title = (title or "").strip()
    if not title:
        return None
    response = http_utils.get(
        BASE_URL,
        params={**_params(), "search": title, "per-page": 1},
        timeout=30,
    )
    results = response.json().get("results") or []
    if not results:
        return None
    return _work_to_metadata(results[0])


def get_pdf_url(identifier: str) -> str | None:
    work: dict[str, Any] | None = None
    if identifier.startswith(("http://", "https://")):
        response = http_utils.get(identifier, params=_params(), timeout=30)
        work = response.json()
    else:
        try:
            response = http_utils.get(
                f"{BASE_URL}/doi:{_clean_doi(identifier)}", params=_params(), timeout=30
            )
            work = response.json()
        except Exception:
            work = None
    return _extract_pdf_url(work or {})


def _params() -> dict[str, str]:
    email = os.getenv("OPENALEX_EMAIL")
    return {"mailto": email} if email else {}


def _clean_doi(doi: str) -> str:
    doi = (doi or "").strip()
    if doi.lower().startswith("https://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("http://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("doi:"):
        return doi[4:].strip()
    return doi


def _work_to_metadata(work: dict[str, Any]) -> dict[str, Any] | None:
    if not work:
        return None
    metadata = {
        "title": work.get("title") or "Unknown Title",
        "abstract": _inverted_index_to_text(work.get("abstract_inverted_index")),
        "authors": _authors(work),
        "year": work.get("publication_year"),
        "venue_full": _venue(work),
        "venue_acronym": "",
        "paper_type": _paper_type(work.get("type")),
        "doi": _strip_doi_url(work.get("doi")),
        "url": work.get("primary_location", {}).get("landing_page_url")
        or work.get("id"),
        "volume": work.get("biblio", {}).get("volume"),
        "issue": work.get("biblio", {}).get("issue"),
        "pages": _pages(work.get("biblio", {})),
        "openalex_id": work.get("id"),
        "pdf_url": _extract_pdf_url(work),
    }
    return normalize_paper_data(metadata)


def _authors(work: dict[str, Any]) -> list[dict[str, Any]]:
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if not name:
            continue
        institutions = authorship.get("institutions") or []
        affiliation = {}
        if institutions:
            institution = institutions[0]
            affiliation = {
                "institution": institution.get("display_name"),
                "url": institution.get("ror"),
            }
        authors.append({
            "full_name": name,
            "affiliation": affiliation,
            "openalex_id": author.get("id"),
        })
    return authors


def _venue(work: dict[str, Any]) -> str:
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    return source.get("display_name") or ""


def _paper_type(openalex_type: str | None) -> str:
    if openalex_type == "article":
        return "journal"
    if openalex_type == "preprint":
        return "preprint"
    if openalex_type == "proceedings-article":
        return "conference"
    return openalex_type or "unknown"


def _pages(biblio: dict[str, Any]) -> str | None:
    first = biblio.get("first_page")
    last = biblio.get("last_page")
    if first and last and first != last:
        return f"{first}-{last}"
    return first or last


def _strip_doi_url(doi: str | None) -> str | None:
    if not doi:
        return None
    return doi.removeprefix("https://doi.org/")


def _extract_pdf_url(work: dict[str, Any]) -> str | None:
    best = work.get("best_oa_location") or {}
    if best.get("pdf_url"):
        return best["pdf_url"]
    primary = work.get("primary_location") or {}
    if primary.get("pdf_url"):
        return primary["pdf_url"]
    for location in work.get("locations") or []:
        if location.get("pdf_url"):
            return location["pdf_url"]
    return None


def _inverted_index_to_text(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positions = [pos for poses in index.values() for pos in poses]
    if not positions:
        return ""
    words: list[str | None] = [None] * (max(positions) + 1)
    for word, positions in index.items():
        for position in positions:
            words[position] = word
    return " ".join(word for word in words if word)
