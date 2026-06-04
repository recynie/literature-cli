from __future__ import annotations

import re
from urllib.parse import urlparse, parse_qs


_ARXIV_DOI_PREFIX = "10.48550/arxiv."


def clean_arxiv_id(raw: str) -> str:
    raw = (raw or "").strip()
    raw = re.sub(r"^arxiv[:\s]*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"[^\dv.]", "", raw)
    return raw


def arxiv_url(arxiv_id: str) -> str:
    return f"https://arxiv.org/abs/{clean_arxiv_id(arxiv_id)}"


def openreview_url(openreview_id: str) -> str:
    return f"https://openreview.net/forum?id={openreview_id.strip()}"


def dblp_url_from_key(dblp_key: str) -> str:
    key = dblp_key.strip().removeprefix("https://dblp.org/rec/").removeprefix("http://dblp.org/rec/")
    if key.endswith(".html"):
        key = key[:-5]
    return f"https://dblp.org/rec/{key}"


def dblp_url_from_pid(dblp_pid: str) -> str:
    return f"https://dblp.org/pid/{dblp_pid.strip()}.html"


def openalex_url(openalex_id: str) -> str:
    return openalex_id.strip()


def semantic_scholar_paper_url(paper_id: str) -> str:
    return f"https://www.semanticscholar.org/paper/{paper_id.strip()}"


def semantic_scholar_author_url(author_id: str) -> str:
    return f"https://www.semanticscholar.org/author/{author_id.strip()}"


def orcid_url(orcid: str) -> str:
    return f"https://orcid.org/{orcid.strip()}"


def parse_openreview_id(value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.netloc and "openreview.net" not in parsed.netloc:
        return None
    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0].strip()
    parts = [p for p in parsed.path.split("/") if p]
    return parts[-1].strip() if parts else None


def parse_dblp_key(value: str) -> str | None:
    value = (value or "").strip()
    if "dblp.org/rec/" in value:
        return value.split("/rec/", 1)[1].split("?", 1)[0].removesuffix(".html")
    return value or None
