"""Centralized arXiv identifier resolution.

All arXiv-related detection and ID extraction lives here. Callers should
use these functions instead of inline regex.
"""

from __future__ import annotations

import re
from typing import Optional

from ng.services.platform_ids import clean_arxiv_id


# Regex patterns — defined once
_ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([\d.]+(?:v\d+)?)")
_ARXIV_ID_CHARS_RE = re.compile(r"[^\d.v]")
_ARXIV_DOI_PREFIX = "10.48550/arxiv."


def parse_arxiv_id(paper) -> Optional[str]:
    """Extract a clean arXiv ID from a Paper object, checking all known sources.

    Priority order:
      1. paper.arxiv_id (e.g. "2505.15134")
      2. paper.url (e.g. "https://arxiv.org/abs/2505.15134")
      3. paper.doi (e.g. "10.48550/arXiv.2505.15134")

    Returns the bare ID (e.g. "2505.15134") or None.
    """
    arxiv_id = getattr(paper, "arxiv_id", None) or ""
    if arxiv_id:
        cleaned = clean_arxiv_id(arxiv_id)
        if cleaned:
            return cleaned

    preprint_id = getattr(paper, "preprint_id", None) or ""
    if preprint_id:
        cleaned = clean_arxiv_id(preprint_id)
        if cleaned:
            return cleaned

    # 2. URL field
    url = getattr(paper, "url", None) or ""
    if url:
        arxiv_id = extract_arxiv_id_from_url(url)
        if arxiv_id:
            return arxiv_id

    # 3. DOI field (10.48550/arXiv.2505.15134)
    doi = getattr(paper, "doi", None) or ""
    if doi.lower().startswith(_ARXIV_DOI_PREFIX):
        suffix = doi.split("/", 1)[1]  # "arXiv.2505.15134"
        # Strip the "arXiv." prefix
        if "." in suffix:
            bare = suffix.split(".", 1)[1]
            return bare

    return None


def is_arxiv_paper(paper) -> bool:
    """Determine whether a Paper object is an arXiv paper.

    Checks (in order):
      1. paper_type is "preprint" or "arxiv"
      2. arxiv_id/preprint_id contains an arXiv ID
      3. venue_full contains "arxiv"
      4. URL contains arxiv.org
      5. DOI is an arXiv DOI (10.48550/arXiv.*)
    """
    paper_type = getattr(paper, "paper_type", None) or ""
    if paper_type.lower() in ("preprint", "arxiv"):
        return True

    arxiv_id = getattr(paper, "arxiv_id", None) or ""
    if arxiv_id and re.match(r"^\d{4}\.\d{4,5}", clean_arxiv_id(arxiv_id)):
        return True

    preprint_id = getattr(paper, "preprint_id", None) or ""
    if preprint_id and re.match(r"^\d{4}\.\d{4,5}", clean_arxiv_id(preprint_id)):
        return True

    venue_full = getattr(paper, "venue_full", None) or ""
    if venue_full and "arxiv" in venue_full.lower():
        return True

    url = getattr(paper, "url", None) or ""
    if url and "arxiv.org" in url.lower():
        return True

    doi = getattr(paper, "doi", None) or ""
    if doi.lower().startswith(_ARXIV_DOI_PREFIX):
        return True

    return False


def extract_arxiv_id_from_url(url: str) -> Optional[str]:
    """Extract arXiv ID from a URL like https://arxiv.org/abs/2505.15134.

    Returns the bare ID or None if the URL is not an arXiv URL.
    """
    if not url:
        return None
    match = _ARXIV_URL_RE.search(url)
    return match.group(1) if match else None


def arxiv_pdf_url(arxiv_id: str) -> str:
    """Build the PDF download URL for a given arXiv ID."""
    clean_id = clean_arxiv_id(arxiv_id)
    return f"https://arxiv.org/pdf/{clean_id}.pdf"
