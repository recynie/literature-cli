from __future__ import annotations

import os
import re
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from ng.db.database import get_pdf_directory
from ng.services import (
    MetadataExtractor,
    PaperService,
    PDFManager,
    PDFService,
    SystemService,
    format_title_by_words,
    normalize_paper_data,
    openalex,
    semantic_scholar,
)
from ng.services.identifier import IdentifierType, detect
from ng.services.arxiv_utils import arxiv_pdf_url
from ng.services.logger import Logger, NullLogger

if TYPE_CHECKING:
    from ng.db.models import Paper


class AddPaperService:
    """Service for adding papers from various sources."""

    def __init__(
        self,
        paper_service: PaperService,
        metadata_extractor: MetadataExtractor,
        system_service: SystemService,
        app: Logger | None = None,
    ):
        """Initialize the add paper service."""
        self.paper_service = paper_service
        self.metadata_extractor = metadata_extractor
        self.system_service = system_service
        self.app = app or NullLogger()

    # Internal helpers
    def _build_paper_data(
        self, metadata: Dict[str, Any], overrides: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Build and normalize paper data from raw metadata with optional overrides."""
        data: Dict[str, Any] = {
            "title": metadata.get("title", "Unknown Title"),
            "abstract": metadata.get("abstract", ""),
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year"),
            "venue_full": metadata.get("venue_full", ""),
            "venue_acronym": metadata.get("venue_acronym", ""),
            "paper_type": metadata.get("paper_type", "unknown"),
            "doi": metadata.get("doi"),
            "url": metadata.get("url"),
            "category": metadata.get("category"),
            "arxiv_id": metadata.get("arxiv_id"),
            "openreview_id": metadata.get("openreview_id"),
            "dblp_key": metadata.get("dblp_key"),
            "openalex_id": metadata.get("openalex_id"),
            "semantic_scholar_id": metadata.get("semantic_scholar_id"),
            "volume": metadata.get("volume"),
            "issue": metadata.get("issue"),
            "pages": metadata.get("pages"),
        }
        if overrides:
            data.update({k: v for k, v in overrides.items() if v is not None})
        return normalize_paper_data(data)

    def _resolve_path(self, path: str) -> str:
        """Resolve a user-provided file path to an absolute path."""
        return os.path.abspath(os.path.expanduser(path))

    def add_arxiv_paper(self, arxiv_id: str) -> Dict[str, Any]:
        """Add a paper from arXiv."""
        metadata = self.metadata_extractor.extract_from_arxiv(arxiv_id)
        paper_data = self._build_paper_data(
            metadata,
            overrides={
                "paper_type": "preprint",
                "url": arxiv_pdf_url(arxiv_id),
            },
        )

        # Add to database first (without PDF)
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )

        # Download PDF
        pdf_dir = get_pdf_directory()
        pdf_path, pdf_error, download_duration = self.system_service.download_pdf(
            "arxiv", arxiv_id, pdf_dir, paper_data
        )

        return {
            "paper": paper,
            "pdf_path": pdf_path,
            "pdf_error": pdf_error,
            "download_duration": download_duration,
        }

    def add_arxiv_paper_async(self, arxiv_id: str) -> Dict[str, Any]:
        """Add a paper from arXiv (step 1: metadata only, for background processing)."""
        # Extract metadata from arXiv
        metadata = self.metadata_extractor.extract_from_arxiv(arxiv_id)

        # Prepare paper data (without PDF initially)
        paper_data = {
            "title": metadata["title"],
            "abstract": metadata.get("abstract", ""),
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year"),
            "venue_full": metadata.get("venue_full", ""),
            "venue_acronym": metadata.get("venue_acronym", ""),
            "paper_type": metadata.get("paper_type", "preprint"),
            "arxiv_id": metadata.get("arxiv_id"),
            "category": metadata.get("category"),
            "doi": metadata.get("doi"),
            "url": arxiv_pdf_url(arxiv_id),
        }

        paper_data = normalize_paper_data(paper_data)

        # Add to database first (without PDF)
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )

        return {"paper": paper, "arxiv_id": arxiv_id, "paper_data": paper_data}

    def download_and_update_pdf(
        self, paper_id: int, source: str, identifier: str, paper_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Background task to download PDF and update paper record."""
        try:
            # Log start of download process
            self.app._add_log(
                "pdf_download_start",
                f"Starting PDF download for paper_id={paper_id}, source={source}, identifier={identifier}",
            )

            # Download PDF
            pdf_dir = get_pdf_directory()

            try:
                pdf_path, pdf_error, download_duration = (
                    self.system_service.download_pdf(
                        source, identifier, pdf_dir, paper_data
                    )
                )
                pass
            except Exception as e:
                self.app._add_log(
                    "pdf_download_exception",
                    f"Exception calling system_service.download_pdf: {str(e)}",
                )
                self.app._add_log(
                    "pdf_download_traceback", f"Traceback: {traceback.format_exc()}"
                )
                raise

            # Summarize result in a readable way
            if pdf_path and not pdf_error:
                summary = PDFService(app=self.app).create_download_summary(
                    pdf_path, download_duration
                )
                self.app._add_log("pdf_download_result", summary)
            else:
                self.app._add_log(
                    "pdf_download_error",
                    f"Download failed: {pdf_error or 'Unknown error'}",
                )

            if pdf_path and not pdf_error:
                # Success implied by result; skip extra stage logs

                # Convert absolute path to relative for storage
                relative_pdf_path = os.path.relpath(pdf_path, pdf_dir)

                # Update the paper with PDF path
                update_data = {"pdf_path": relative_pdf_path}

                updated_paper, update_error = self.paper_service.update_paper(
                    paper_id, update_data
                )
                self.app._add_log(
                    "pdf_update_result",
                    f"paper_updated={updated_paper is not None}, error='{update_error}'",
                )

                if update_error:
                    self.app._add_log(
                        "pdf_update_error",
                        f"Database update failed: {update_error}",
                    )
                    return {
                        "success": False,
                        "error": f"PDF downloaded but database update failed: {update_error}",
                    }

                # Completed
                self.app._add_log(
                    "pdf_download_complete",
                    f"Updated paper {paper_id} with PDF path: {relative_pdf_path}",
                )
                return {
                    "success": True,
                    "pdf_path": relative_pdf_path,
                    "paper": updated_paper,
                    "download_duration": download_duration,
                }
            else:
                error_msg = pdf_error or "Unknown PDF download error"
                self.app._add_log(
                    "pdf_download_error", f"PDF download failed: {error_msg}"
                )
                return {
                    "success": False,
                    "error": error_msg,
                    "download_duration": download_duration,
                }

        except Exception as e:
            error_msg = f"Failed to download and update PDF: {str(e)}"
            self.app._add_log(
                "pdf_download_exception",
                f"Exception in download_and_update_pdf: {error_msg}",
            )
            self.app._add_log(
                "pdf_download_traceback", f"Traceback: {traceback.format_exc()}"
            )
            return {"success": False, "error": error_msg, "download_duration": 0.0}

    def add_dblp_paper(self, dblp_url: str) -> Dict[str, Any]:
        """Add a paper from DBLP URL."""
        # Extract metadata from DBLP
        metadata = self.metadata_extractor.extract_from_dblp(dblp_url)

        # Prepare paper data
        paper_data = {
            "title": metadata.get("title", "Unknown Title"),
            "abstract": metadata.get("abstract", ""),
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year"),
            "venue_full": metadata.get("venue_full", ""),
            "venue_acronym": metadata.get("venue_acronym", ""),
            "paper_type": metadata.get("paper_type", "conference"),
            "doi": metadata.get("doi"),
            "url": dblp_url,
            "dblp_key": metadata.get("dblp_key"),
        }

        paper_data = normalize_paper_data(paper_data)

        # Add to database
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )
        if self.app:
            self.app._add_log(
                "paper_add_dblp",
                f"Added DBLP paper '{paper.title}' (ID {paper.id})",
            )

        return {"paper": paper, "pdf_path": None, "pdf_error": None}

    def add_openreview_paper(self, openreview_id: str) -> Dict[str, Any]:
        """Add a paper from OpenReview."""
        metadata = self.metadata_extractor.extract_from_openreview(openreview_id)
        paper_data = self._build_paper_data(
            metadata,
            overrides={
                "paper_type": metadata.get("paper_type", "conference"),
                "url": metadata.get(
                    "url", f"https://openreview.net/forum?id={openreview_id}"
                ),
            },
        )

        # Add to database
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )
        if self.app:
            self.app._add_log(
                "paper_add_openreview",
                f"Added OpenReview metadata for '{paper.title}' (ID {paper.id})",
            )

        # Download PDF
        pdf_dir = get_pdf_directory()
        pdf_path, pdf_error, download_duration = self.system_service.download_pdf(
            "openreview", openreview_id, pdf_dir, paper_data
        )

        return {
            "paper": paper,
            "pdf_path": pdf_path,
            "pdf_error": pdf_error,
            "download_duration": download_duration,
        }

    def add_openreview_paper_async(self, openreview_id: str) -> Dict[str, Any]:
        """Add a paper from OpenReview (step 1: metadata only, for background processing)."""
        # Extract metadata from OpenReview
        metadata = self.metadata_extractor.extract_from_openreview(openreview_id)

        # Prepare paper data
        paper_data = {
            "title": metadata.get("title", "Unknown Title"),
            "abstract": metadata.get("abstract", ""),
            "authors": metadata.get("authors", ""),
            "year": metadata.get("year"),
            "venue_full": metadata.get("venue_full", ""),
            "venue_acronym": metadata.get("venue_acronym", ""),
            "paper_type": metadata.get("paper_type", "conference"),
            "category": metadata.get("category"),
            "url": metadata.get(
                "url", f"https://openreview.net/forum?id={openreview_id}"
            ),
        }

        paper_data = normalize_paper_data(paper_data)

        # Add to database
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )

        return {
            "paper": paper,
            "openreview_id": openreview_id,
            "paper_data": paper_data,
        }

    def add_pdf_paper_async(self, pdf_path: str) -> Dict[str, Any]:
        """Add a paper from local PDF file by copying the file and creating a minimal record."""
        pdf_path = os.path.expanduser(pdf_path)
        pdf_path = os.path.abspath(pdf_path)

        if not os.path.exists(pdf_path):
            raise Exception(f"PDF file not found: {pdf_path}")

        if not pdf_path.lower().endswith(".pdf"):
            raise Exception(f"File is not a PDF: {pdf_path}")

        temp_paper_data = {
            "title": "PDF Paper",
            "authors": ["Unknown"],
            "year": datetime.now().year,
        }

        pdf_manager = PDFManager(app=self.app)
        relative_pdf_path, pdf_error = pdf_manager.process_pdf_path(
            pdf_path, temp_paper_data
        )

        if pdf_error:
            raise Exception(f"Failed to copy PDF: {pdf_error}")

        paper_data = {
            "title": "PDF Paper (imported from local file)",
            "abstract": "",
            "authors": ["Unknown"],
            "year": datetime.now().year,
            "venue_full": "",
            "venue_acronym": "",
            "paper_type": "unknown",
            "doi": None,
            "url": None,
            "pdf_path": relative_pdf_path,
        }

        paper_data = normalize_paper_data(paper_data)

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, paper_data.get("authors", []), []
        )

        if self.app:
            self.app._add_log(
                "paper_add_pdf_async",
                f"Added local PDF '{pdf_path}' as paper ID {paper.id}",
            )

        return {"paper": paper, "pdf_path": pdf_path, "paper_data": paper_data}


    def add_bib_papers(self, bib_path: str) -> Tuple[List[Paper], List[str]]:
        """Add papers from .bib file."""
        # Resolve path and do simple validation
        bib_path = self._resolve_path(bib_path)
        if not os.path.exists(bib_path) or not bib_path.lower().endswith(
            (".bib", ".bibtex")
        ):
            raise Exception(f"Invalid BibTeX file: {bib_path}")

        # Extract metadata from BibTeX file
        papers_metadata = self.metadata_extractor.extract_from_bibtex(bib_path)

        added_papers = []
        errors = []

        for metadata in papers_metadata:
            try:
                # Prepare and normalize paper data
                paper_data = self._build_paper_data(metadata)

                # Add to database first
                authors = paper_data.get("authors", [])
                collections = []

                paper = self.paper_service.add_paper_from_metadata(
                    paper_data, authors, collections
                )
                if self.app:
                    self.app._add_log(
                        "paper_add_bib_entry",
                        (
                            "Added paper from BIB entry '"
                            + paper_data.get("title", "Unknown Title")[:80]
                            + f"...' (ID {paper.id})"
                        ),
                    )

                # Try to download or process PDF if URL is provided
                if metadata.get("url"):
                    pdf_manager = PDFManager(app=self.app)

                    try:
                        pdf_path, pdf_error = pdf_manager.process_pdf_path(
                            metadata["url"], paper_data
                        )
                        download_duration = (
                            0.0  # process_pdf_path doesn't return duration
                        )

                        if pdf_path and not pdf_error:
                            # process_pdf_path returns a relative path; ensure we store it as-is
                            relative_pdf_path = pdf_path
                            absolute_pdf_path = pdf_manager.get_absolute_path(
                                relative_pdf_path
                            )

                            update_data = {"pdf_path": relative_pdf_path}
                            updated_paper, update_error = (
                                self.paper_service.update_paper(paper.id, update_data)
                            )

                            if not update_error and self.app:
                                summary = PDFService(
                                    app=self.app
                                ).create_download_summary(
                                    absolute_pdf_path, download_duration
                                )
                                preview = format_title_by_words(
                                    paper_data.get("title", "") or ""
                                )
                                self.app.notify(
                                    f"PDF available for '{preview}': {summary}",
                                    severity="information",
                                )

                    except Exception as pdf_e:
                        # Don't fail the entire paper addition if PDF download fails
                        if self.app:
                            self.app._add_log(
                                "bib_pdf_warning",
                                f"Could not download PDF for '{paper_data['title']}': {str(pdf_e)}",
                            )

                added_papers.append(paper)

            except Exception as e:
                errors.append(
                    f"Failed to add paper '{metadata.get('title', 'Unknown')}': {e}"
                )

        return added_papers, errors

    def add_ris_papers(self, ris_path: str) -> Tuple[List[Paper], List[str]]:
        """Add papers from .ris file."""
        # Resolve path and do simple validation
        ris_path = self._resolve_path(ris_path)
        if not os.path.exists(ris_path) or not ris_path.lower().endswith(
            (".ris", ".txt")
        ):
            raise Exception(f"Invalid RIS file: {ris_path}")

        # Extract metadata from RIS file
        papers_metadata = self.metadata_extractor.extract_from_ris(ris_path)

        added_papers = []
        errors = []

        for metadata in papers_metadata:
            try:
                # Prepare and normalize paper data
                paper_data = self._build_paper_data(metadata)

                # Add to database
                authors = paper_data.get("authors", [])
                collections = []

                paper = self.paper_service.add_paper_from_metadata(
                    paper_data, authors, collections
                )

                added_papers.append(paper)

            except Exception as e:
                errors.append(
                    f"Failed to add paper '{metadata.get('title', 'Unknown')}': {e}"
                )

        return added_papers, errors

    def add_doi_paper(self, doi: str) -> Dict[str, Any]:
        """Add a paper from DOI."""
        # arXiv registers DOIs under the 10.48550 prefix; Crossref doesn't index them.
        # Detect this prefix and route to the arXiv importer instead.
        doi_clean = doi.strip()
        if doi_clean.startswith("http"):
            m = re.search(r"10\.\d+/[^\s]+", doi_clean)
            doi_clean = m.group(0) if m else doi_clean
        if doi_clean.lower().startswith("10.48550/arxiv."):
            arxiv_id = doi_clean.split("/", 1)[1]  # e.g. "arXiv.2301.00001" → strip prefix
            arxiv_id = arxiv_id.split(".", 1)[1] if "." in arxiv_id else arxiv_id
            return self.add_arxiv_paper(arxiv_id)

        # Extract metadata from DOI using Crossref first, then free API fallbacks.
        metadata = self._fetch_doi_metadata(doi_clean)

        # Prepare and normalize paper data
        paper_data = self._build_paper_data(
            metadata,
            overrides={
                "paper_type": metadata.get("paper_type", "journal"),
                "doi": doi_clean,
                "url": metadata.get("url", f"https://doi.org/{doi_clean}"),
            },
        )

        # Add to database
        authors = paper_data.get("authors", [])
        collections = []

        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, collections
        )
        pdf_dir = get_pdf_directory()
        pdf_path, pdf_error, download_duration = self.system_service.download_pdf(
            "doi", doi_clean, pdf_dir, paper_data
        )

        return {
            "paper": paper,
            "pdf_path": pdf_path,
            "pdf_error": pdf_error,
            "download_duration": download_duration,
        }

    def add_by_identifier(self, raw_input: str) -> Dict[str, Any]:
        """Add a paper from the unified identifier entrypoint."""
        detected = detect(raw_input)
        if detected.type == IdentifierType.PDF:
            result = self.add_pdf_paper_async(detected.value)
            return {
                "paper": result["paper"],
                "pdf_path": None,
                "pdf_error": None,
                "identifier_type": detected.type.value,
            }
        if detected.type == IdentifierType.BIBTEX:
            papers, errors = self.add_bib_papers(detected.value)
            return {
                "papers": papers,
                "errors": errors,
                "count": len(papers),
                "identifier_type": detected.type.value,
            }
        if detected.type == IdentifierType.RIS:
            papers, errors = self.add_ris_papers(detected.value)
            return {
                "papers": papers,
                "errors": errors,
                "count": len(papers),
                "identifier_type": detected.type.value,
            }
        if detected.type == IdentifierType.ARXIV:
            result = self.add_arxiv_paper(detected.value)
        elif detected.type == IdentifierType.DOI:
            result = self.add_doi_paper(detected.value)
        elif detected.type == IdentifierType.OPENREVIEW:
            result = self.add_openreview_paper(detected.value)
        elif detected.type == IdentifierType.DBLP:
            result = self.add_dblp_paper(detected.value)
        elif detected.type == IdentifierType.TITLE:
            result = self.add_title_paper(detected.value)
        else:
            raise ValueError(f"Unsupported identifier type: {detected.type}")
        result["identifier_type"] = detected.type.value
        return result

    def add_title_paper(self, title: str) -> Dict[str, Any]:
        """Search for a paper by title using OpenAlex, then Semantic Scholar."""
        metadata = None
        errors = []
        for name, fetcher in (
            ("OpenAlex", lambda: openalex.search_by_title(title)),
            ("Semantic Scholar", lambda: semantic_scholar.search_by_title(title)),
        ):
            try:
                metadata = fetcher()
                if metadata:
                    break
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        if not metadata:
            detail = "; ".join(errors) if errors else "No matches found"
            raise Exception(f"Failed to find metadata for title '{title}': {detail}")

        paper_data = self._build_paper_data(metadata)
        authors = paper_data.get("authors", [])
        paper = self.paper_service.add_paper_from_metadata(
            paper_data, authors, []
        )
        pdf_path = None
        pdf_error = None
        download_duration = 0.0
        if paper_data.get("doi") or paper_data.get("pdf_url"):
            pdf_path, pdf_error, download_duration = self.system_service.download_pdf(
                "metadata", paper_data.get("doi") or title, get_pdf_directory(), paper_data
            )
        return {
            "paper": paper,
            "pdf_path": pdf_path,
            "pdf_error": pdf_error,
            "download_duration": download_duration,
        }

    def _fetch_doi_metadata(self, doi: str) -> Dict[str, Any]:
        errors = []
        for name, fetcher in (
            ("Crossref", lambda: self.metadata_extractor.extract_from_doi(doi)),
            ("OpenAlex", lambda: openalex.search_by_doi(doi)),
            ("Semantic Scholar", lambda: semantic_scholar.search_by_doi(doi)),
        ):
            try:
                metadata = fetcher()
                if metadata:
                    return metadata
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        raise Exception(f"Failed to fetch DOI metadata: {'; '.join(errors)}")

    def add_manual_paper(self, title: str = "") -> Dict[str, Any]:
        """Add a paper manually with basic defaults."""
        try:
            current_year = datetime.now().year
            paper_data = {
                "title": title if title.strip() else "Untitled",
                "abstract": "",
                "year": current_year,
                "venue_full": "",
                "venue_acronym": "",
                "paper_type": "unknown",
            }

            # Normalize paper data for database storage
            paper_data = normalize_paper_data(paper_data)

            authors = []
            collections = []

            paper = self.paper_service.add_paper_from_metadata(
                paper_data, authors, collections
            )

            return {"paper": paper, "pdf_path": None, "pdf_error": None}

        except Exception as e:
            raise Exception(f"Failed to add manual paper: {str(e)}")
