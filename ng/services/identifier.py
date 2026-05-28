"""Identifier detection for unified paper import."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import unquote, urlparse, parse_qs

from ng.services.arxiv_utils import clean_arxiv_id, extract_arxiv_id_from_url


class IdentifierType(StrEnum):
    PDF = "pdf"
    BIBTEX = "bibtex"
    RIS = "ris"
    ARXIV = "arxiv"
    DOI = "doi"
    OPENREVIEW = "openreview"
    DBLP = "dblp"
    TITLE = "title"


@dataclass(frozen=True)
class DetectedIdentifier:
    type: IdentifierType
    value: str
    raw: str


_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(?:v\d+)?$", re.IGNORECASE)
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)


def detect(raw_input: str) -> DetectedIdentifier:
    """Detect a user-provided import identifier and return its normalized value."""
    raw = (raw_input or "").strip()
    if not raw:
        raise ValueError("Identifier cannot be empty")

    path = os.path.abspath(os.path.expanduser(raw))
    suffix = os.path.splitext(path)[1].lower()
    if os.path.exists(path) and suffix == ".pdf":
        return DetectedIdentifier(IdentifierType.PDF, path, raw)
    if os.path.exists(path) and suffix in {".bib", ".bibtex"}:
        return DetectedIdentifier(IdentifierType.BIBTEX, path, raw)
    if os.path.exists(path) and suffix in {".ris", ".txt"}:
        return DetectedIdentifier(IdentifierType.RIS, path, raw)

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    if "arxiv.org" in host:
        arxiv_id = extract_arxiv_id_from_url(raw)
        if arxiv_id:
            return DetectedIdentifier(IdentifierType.ARXIV, arxiv_id, raw)

    if _ARXIV_ID_RE.match(clean_arxiv_id(raw)):
        return DetectedIdentifier(IdentifierType.ARXIV, clean_arxiv_id(raw), raw)

    if "doi.org" in host:
        doi = _extract_doi(unquote(parsed.path.lstrip("/")))
        if doi:
            return DetectedIdentifier(IdentifierType.DOI, doi, raw)

    doi = _extract_doi(raw)
    if doi:
        return DetectedIdentifier(IdentifierType.DOI, doi, raw)

    if "openreview.net" in host:
        openreview_id = _extract_openreview_id(raw)
        if openreview_id:
            return DetectedIdentifier(IdentifierType.OPENREVIEW, openreview_id, raw)

    if "dblp.org" in host:
        return DetectedIdentifier(IdentifierType.DBLP, raw, raw)

    return DetectedIdentifier(IdentifierType.TITLE, raw, raw)


def _extract_doi(value: str) -> str | None:
    value = re.sub(r"^doi:\s*", "", value.strip(), flags=re.IGNORECASE)
    match = _DOI_RE.search(value)
    if not match:
        return None
    return match.group(0).rstrip(".,;)")


def _extract_openreview_id(value: str) -> str | None:
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0].strip()
    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        return path_parts[-1].strip()
    return None
