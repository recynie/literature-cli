"""Unpaywall API wrapper."""

from __future__ import annotations

import os
from typing import Any

from ng.services import http_utils


BASE_URL = "https://api.unpaywall.org/v2"


def get_oa_pdf_url(doi: str) -> str | None:
    doi = _clean_doi(doi)
    if not doi:
        return None
    email = os.getenv("UNPAYWALL_EMAIL") or "litcli@example.com"
    response = http_utils.get(f"{BASE_URL}/{doi}", params={"email": email}, timeout=30)
    data = response.json()
    return _extract_pdf_url(data)


def _clean_doi(doi: str) -> str:
    doi = (doi or "").strip()
    if doi.lower().startswith("https://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("http://doi.org/"):
        return doi.split("/", 3)[-1]
    if doi.lower().startswith("doi:"):
        return doi[4:].strip()
    return doi


def _extract_pdf_url(data: dict[str, Any]) -> str | None:
    best = data.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        return best["url_for_pdf"]
    for location in data.get("oa_locations") or []:
        if location.get("url_for_pdf"):
            return location["url_for_pdf"]
    return None
