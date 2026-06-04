from __future__ import annotations

import os
import platform
import subprocess
import traceback
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

import pyperclip

from ng.services.arxiv_utils import arxiv_pdf_url
from ng.services import openalex, semantic_scholar, unpaywall
from ng.services.identifier import IdentifierType, detect
from ng.services.logger import Logger, NullLogger
from ng.services.platform_ids import parse_openreview_id

if TYPE_CHECKING:
    from ng.services import PDFManager


class SystemService:
    """Service for system integrations."""

    def __init__(self, pdf_manager: PDFManager, app: Logger | None = None):
        self.pdf_manager = pdf_manager
        self.app = app or NullLogger()

    def open_pdf(self, pdf_path: str) -> Tuple[bool, str]:
        """Open PDF file in system default viewer. Returns (success, error_message)."""
        try:
            if not os.path.exists(pdf_path):
                return False, f"PDF file not found: {pdf_path}"

            # Cross-platform PDF opening
            if platform.system() == "Windows":  # Windows
                os.startfile(pdf_path)
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["open", pdf_path], capture_output=True, text=True
                )
                if result.returncode != 0:
                    return False, f"Failed to open PDF: {result.stderr}"
            else:  # Linux and other Unix-like systems
                # Check if xdg-open is available
                try:
                    result = subprocess.run(
                        ["which", "xdg-open"], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return (
                            False,
                            "xdg-open not found. Please install xdg-utils or set a PDF viewer.",
                        )

                    result = subprocess.run(
                        ["xdg-open", pdf_path], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return False, f"Failed to open PDF: {result.stderr}"
                except FileNotFoundError:
                    return (
                        False,
                        "xdg-open not found. Please install xdg-utils or set a PDF viewer.",
                    )

            return True, ""

        except Exception as e:
            return False, f"Error opening PDF: {str(e)}"

    def open_file(self, file_path: str, file_type: str = "file") -> Tuple[bool, str]:
        """Open file in system default application. Returns (success, error_message)."""
        try:
            if not os.path.exists(file_path):
                return False, f"{file_type} file not found: {file_path}"

            # Cross-platform file opening
            if platform.system() == "Windows":  # Windows
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                result = subprocess.run(
                    ["open", file_path], capture_output=True, text=True
                )
                if result.returncode != 0:
                    return False, f"Failed to open {file_type}: {result.stderr}"
            else:  # Linux and other Unix-like systems
                # Check if xdg-open is available
                try:
                    result = subprocess.run(
                        ["which", "xdg-open"], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return (
                            False,
                            "xdg-open not found. Please install xdg-utils.",
                        )

                    result = subprocess.run(
                        ["xdg-open", file_path], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return False, f"Failed to open {file_type}: {result.stderr}"
                except FileNotFoundError:
                    return (
                        False,
                        "xdg-open not found. Please install xdg-utils.",
                    )

            return True, ""

        except Exception as e:
            return False, f"Error opening {file_type}: {str(e)}"

    def copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard."""
        pyperclip.copy(text)
        return True

    def download_pdf(
        self,
        source: str,
        identifier: str,
        download_dir: str,
        paper_data: Dict[str, Any] = None,
    ) -> Tuple[Optional[str], str, float]:
        """
        Download PDF from various sources (arXiv, OpenReview, etc.).

        Returns:
            tuple[Optional[str], str, float]: (pdf_path, error_message, download_duration_seconds)
            If successful: (path, "", duration)
            If error: (None, error_message, duration)
        """
        try:
            self.app._add_log(
                "system_download_start",
                f"SystemService.download_pdf called with source='{source}', identifier='{identifier}', download_dir='{download_dir}'",
            )

            # Create download directory
            os.makedirs(download_dir, exist_ok=True)
            self.app._add_log(
                "system_download_debug",
                f"Created/verified download directory: {download_dir}",
            )

            # Generate URL candidates based on source, then append metadata fallbacks.
            candidates: list[tuple[str, str]] = []
            if source == "arxiv":
                candidates.append(("arXiv", arxiv_pdf_url(identifier)))
                self.app._add_log(
                    "system_download_debug",
                    f"arXiv: original_id='{identifier}'",
                )
            elif source == "openreview":
                candidates.append(("OpenReview", f"https://openreview.net/pdf?id={identifier}"))
                self.app._add_log(
                    "system_download_debug",
                    f"OpenReview: identifier='{identifier}'",
                )
            elif source in {"doi", "metadata"}:
                candidates.extend(self._metadata_pdf_candidates(identifier, paper_data or {}))
            else:
                error_msg = f"Unsupported source: {source}"
                self.app._add_log("system_download_error", error_msg)
                return None, error_msg

            candidates.extend(self._metadata_pdf_candidates(identifier, paper_data or {}))
            candidates = self._dedupe_candidates(candidates)
            if not candidates:
                return None, "No PDF URL candidates found", 0.0

            # Use PDFManager to handle everything with proper naming
            self.app._add_log(
                "system_download_debug",
                f"Setting PDFManager pdf_dir to: {download_dir}",
            )
            self.pdf_manager.pdf_dir = download_dir  # Set download directory
            # Set app reference for PDFManager logging
            self.pdf_manager.app = self.app

            errors = []
            total_duration = 0.0
            for label, pdf_url in candidates:
                self.app._add_log(
                    "system_download_debug",
                    f"Trying {label} PDF candidate: {pdf_url}",
                )
                pdf_path, error_msg, download_duration = (
                    self.pdf_manager.download_pdf_from_url_with_proper_naming(
                        pdf_url, paper_data or {}
                    )
                )
                total_duration += download_duration

                self.app._add_log(
                    "system_download_timing",
                    f"{label} PDFManager operation took {download_duration:.2f} seconds",
                )

                self.app._add_log(
                    "system_download_result",
                    f"{label} result: pdf_path='{pdf_path}', error_msg='{error_msg}'",
                )

                if not error_msg:
                    self.app._add_log(
                        "system_download_success",
                        f"PDF download successful via {label}: {pdf_path}",
                    )
                    return pdf_path, "", total_duration
                errors.append(f"{label}: {error_msg}")

            error_msg = "PDF download failed from all candidates: " + "; ".join(errors)
            self.app._add_log("system_download_error", error_msg)
            return None, error_msg, total_duration

        except Exception as e:
            error_msg = f"Error downloading PDF: {str(e)}\n{traceback.format_exc()}"
            self.app._add_log(
                "system_download_exception",
                f"Exception in SystemService.download_pdf: {error_msg}",
            )
            return None, error_msg, 0.0

    def _metadata_pdf_candidates(
        self, identifier: str, paper_data: Dict[str, Any]
    ) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []
        doi = (paper_data.get("doi") or "").strip()
        arxiv_id = (paper_data.get("arxiv_id") or "").strip()
        openreview_id = (paper_data.get("openreview_id") or "").strip()
        url = (paper_data.get("url") or "").strip()

        if not doi and identifier:
            try:
                detected = detect(identifier)
                if detected.type == IdentifierType.DOI:
                    doi = detected.value
            except Exception:
                pass

        if arxiv_id:
            candidates.append(("arXiv", arxiv_pdf_url(arxiv_id)))

        openreview_id = openreview_id or (parse_openreview_id(url) if url else None)
        if openreview_id:
            candidates.append(("OpenReview", f"https://openreview.net/pdf?id={openreview_id}"))

        if doi:
            try:
                pdf_url = unpaywall.get_oa_pdf_url(doi)
                if pdf_url:
                    candidates.append(("Unpaywall", pdf_url))
            except Exception as exc:
                self.app._add_log("pdf_candidate_warning", f"Unpaywall: {exc}")
            try:
                pdf_url = openalex.get_pdf_url(doi)
                if pdf_url:
                    candidates.append(("OpenAlex", pdf_url))
            except Exception as exc:
                self.app._add_log("pdf_candidate_warning", f"OpenAlex: {exc}")
            try:
                pdf_url = semantic_scholar.get_pdf_url(doi)
                if pdf_url:
                    candidates.append(("Semantic Scholar", pdf_url))
            except Exception as exc:
                self.app._add_log("pdf_candidate_warning", f"Semantic Scholar: {exc}")

        explicit_pdf = paper_data.get("pdf_url")
        if explicit_pdf:
            candidates.append(("metadata", explicit_pdf))

        return candidates

    def _dedupe_candidates(self, candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
        seen = set()
        deduped = []
        for label, url in candidates:
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append((label, url))
        return deduped

    def open_file_location(self, file_path: str) -> Tuple[bool, str]:
        """Open file location in Finder/File Explorer and select the file. Returns (success, error_message)."""
        try:
            if not os.path.exists(file_path):
                return False, f"File not found: {file_path}"

            # Cross-platform file location opening
            if platform.system() == "Windows":  # Windows
                # Use explorer.exe with /select to highlight the file
                subprocess.run(["explorer.exe", "/select,", file_path], check=True)
            elif platform.system() == "Darwin":  # macOS
                # Use open -R to reveal in Finder
                result = subprocess.run(
                    ["open", "-R", file_path], capture_output=True, text=True
                )
                if result.returncode != 0:
                    return False, f"Failed to open file location: {result.stderr}"
            else:  # Linux and other Unix-like systems
                # Try to open the parent directory
                parent_dir = os.path.dirname(file_path)
                try:
                    result = subprocess.run(
                        ["which", "xdg-open"], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return (
                            False,
                            "xdg-open not found. Please install xdg-utils or set a file manager.",
                        )

                    result = subprocess.run(
                        ["xdg-open", parent_dir], capture_output=True, text=True
                    )
                    if result.returncode != 0:
                        return False, f"Failed to open file location: {result.stderr}"
                except FileNotFoundError:
                    return (
                        False,
                        "xdg-open not found. Please install xdg-utils or set a file manager.",
                    )

            return True, ""

        except Exception as e:
            return False, f"Error opening file location: {str(e)}"
