"""MinerU API integration for full-text PDF parsing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from ng.services.logger import Logger, NullLogger


@dataclass
class MinerUConfig:
    api_key: str
    model: str = "vlm"
    ocr: bool = True
    language: str = "en"


@dataclass
class MinerUParseResult:
    """Paths of files written to disk after a successful parse."""

    markdown_path: str           # absolute path to .md file
    json_path: str               # absolute path to content_list .json file
    extra_paths: list[str] = field(default_factory=list)  # html / docx / latex


class MinerUService:
    """Wraps the MinerU Open API SDK for PDF full-text parsing."""

    def __init__(self, app: Logger | None = None):
        self.app = app or NullLogger()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_pdf(
        self,
        pdf_path: str,
        paper_id: int,
        output_dir: str,
        config: MinerUConfig,
        extra_formats: list[str] | None = None,
    ) -> MinerUParseResult:
        """Parse *pdf_path* with MinerU and save results under *output_dir*.

        Args:
            pdf_path:      Absolute path to the local PDF file.
            paper_id:      Used as the stem for output file names.
            output_dir:    Directory where results are written (created if absent).
            config:        MinerU API config (key, model, ocr, language).
            extra_formats: Optional additional formats to request, e.g. ["html", "docx"].

        Returns:
            MinerUParseResult with paths of all written files.

        Raises:
            RuntimeError: on any API or I/O error.
        """
        extra_formats = extra_formats or []
        os.makedirs(output_dir, exist_ok=True)

        self.app._add_log("mineru_start", f"Parsing PDF {pdf_path} with MinerU")

        try:
            from mineru import MinerU  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "mineru-open-sdk is not installed. "
                "Run: uv pip install 'mineru-open-sdk>=0.2.5'"
            ) from exc

        # Map our format names to SDK kwarg names
        _format_kwarg_map = {"html": "html", "docx": "docx", "latex": "latex"}
        sdk_extra = [f for f in extra_formats if f in _format_kwarg_map]

        try:
            with MinerU(config.api_key) as client:
                result = client.extract(
                    pdf_path,
                    model=config.model,
                    ocr=config.ocr,
                    language=config.language,
                    extra_formats=sdk_extra if sdk_extra else None,
                )
        except Exception as exc:
            raise RuntimeError(f"MinerU API error: {exc}") from exc

        if result.state != "done":
            raise RuntimeError(
                f"MinerU parsing did not complete successfully (state={result.state})"
            )

        # --- Write markdown ---
        md_path = os.path.join(output_dir, f"{paper_id}.md")
        try:
            result.save_markdown(md_path, with_images=True)
        except Exception as exc:
            raise RuntimeError(f"Failed to save markdown: {exc}") from exc

        self.app._add_log("mineru_md_saved", f"Markdown saved to {md_path}")

        # --- Write content_list JSON ---
        json_path = os.path.join(output_dir, f"{paper_id}.json")
        try:
            content_list = result.content_list or []
            with open(json_path, "w", encoding="utf-8") as fh:
                json.dump(content_list, fh, ensure_ascii=False, indent=2)
        except Exception as exc:
            raise RuntimeError(f"Failed to save content_list JSON: {exc}") from exc

        self.app._add_log("mineru_json_saved", f"content_list saved to {json_path}")

        # --- Write extra formats ---
        extra_paths: list[str] = []
        _save_methods = {
            "html": ("save_html", ".html"),
            "docx": ("save_docx", ".docx"),
            "latex": ("save_latex", ".latex"),
        }
        for fmt in sdk_extra:
            method_name, ext = _save_methods[fmt]
            save_fn = getattr(result, method_name, None)
            if save_fn is None:
                continue
            fmt_path = os.path.join(output_dir, f"{paper_id}{ext}")
            try:
                save_fn(fmt_path)
                extra_paths.append(fmt_path)
                self.app._add_log("mineru_extra_saved", f"{fmt} saved to {fmt_path}")
            except Exception as exc:
                # Extra format failures are non-fatal: log and continue.
                self.app._add_log(
                    "mineru_extra_warning",
                    f"Could not save {fmt}: {exc}",
                )

        return MinerUParseResult(
            markdown_path=md_path,
            json_path=json_path,
            extra_paths=extra_paths,
        )


# ---------------------------------------------------------------------------
# Config helpers (read from environment, set by lit/config.py)
# ---------------------------------------------------------------------------

def mineru_config_from_env() -> Optional[MinerUConfig]:
    """Build a MinerUConfig from environment variables.

    Returns None if MINERU_API_KEY is not set (MinerU not configured).
    """
    api_key = os.environ.get("MINERU_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.environ.get("MINERU_MODEL", "vlm").strip()
    language = os.environ.get("MINERU_LANGUAGE", "en").strip()

    ocr_raw = os.environ.get("MINERU_OCR", "true").strip().lower()
    ocr = ocr_raw not in ("false", "0", "no")

    return MinerUConfig(api_key=api_key, model=model, ocr=ocr, language=language)
