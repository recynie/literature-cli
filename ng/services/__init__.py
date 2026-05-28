"""Convenience imports for services package.

Ordered to avoid circular imports during module initialization.
"""

# Level 1: Core utilities with no dependencies
from . import http_utils
from . import constants
from .utils import fix_broken_lines, normalize_paper_data, sanitize_for_logging
from .constants import (
    DEFAULT_EXTRACTION_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_PDF_SUMMARY_PAGES,
    DEFAULT_PDF_METADATA_PAGES,
)
from .logger import Logger, NullLogger

# Level 2: Formatting utilities
from .formatting import (
    format_file_size,
    format_authors_list,
    format_title_by_words,
    format_field_change,
    format_collections_list,
    format_download_speed,
)

# Level 3: Independent modules
from . import validation
from . import prompts
from . import llm_utils

# Level 4: Metadata extractor
from .metadata import MetadataExtractor

# Level 5: PDF services
from .pdf import (
    PDFManager,
    PDFService,
    PDFDownloadHandler,
    PDFExtractionHandler,
    PDFDownloadTaskFactory,
)

# Level 6: Database health service
from .database import DatabaseHealthService

# Level 7: Core services
from .affiliation import AffiliationService
from .author import AuthorService
from .collection import CollectionService
from .search import SearchService
from . import export

# Level 8: Higher-level services
from .paper import PaperService
from .system import SystemService
from .add_paper import AddPaperService

__all__ = [
    "AddPaperService",
    "AffiliationService",
    "AuthorService",
    "CollectionService",
    "DatabaseHealthService",
    "export",
    "http_utils",
    "MetadataExtractor",
    "PaperService",
    "PDFManager",
    "PDFService",
    "PDFDownloadHandler",
    "PDFExtractionHandler",
    "PDFDownloadTaskFactory",
    "SearchService",
    "SystemService",
    "fix_broken_lines",
    "normalize_paper_data",
    "sanitize_for_logging",
    "validation",
    "prompts",
    "llm_utils",
    "constants",
    "Logger",
    "NullLogger",
    # Formatting utilities
    "format_file_size",
    "format_authors_list",
    "format_title_by_words",
    "format_field_change",
    "format_collections_list",
    "format_download_speed",
    # Constants
    "DEFAULT_EXTRACTION_MODEL",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_PDF_SUMMARY_PAGES",
    "DEFAULT_PDF_METADATA_PAGES",
]
