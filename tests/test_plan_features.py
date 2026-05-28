from __future__ import annotations

from types import SimpleNamespace

from typer.testing import CliRunner

from lit.commands import add as add_command
from ng.services import openalex, semantic_scholar, unpaywall
from ng.services.fetch import FetchMetadataService
from ng.services.identifier import IdentifierType, detect
from ng.services.logger import NullLogger
from ng.services.system import SystemService


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_identifier_detection_rules(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{x,title={X}}")
    ris = tmp_path / "refs.ris"
    ris.write_text("TY  - JOUR")

    assert detect(str(pdf)).type == IdentifierType.PDF
    assert detect(str(bib)).type == IdentifierType.BIBTEX
    assert detect(str(ris)).type == IdentifierType.RIS
    assert detect("https://arxiv.org/abs/2505.15134").value == "2505.15134"
    assert detect("2505.15134v2").type == IdentifierType.ARXIV
    assert detect("https://doi.org/10.1145/123.456").value == "10.1145/123.456"
    assert detect("https://openreview.net/forum?id=abc123").value == "abc123"
    assert detect("https://dblp.org/rec/conf/test/item.html").type == IdentifierType.DBLP
    assert detect("A Search Title").type == IdentifierType.TITLE


def test_openalex_metadata_mapping(monkeypatch):
    def fake_get(url, **kwargs):
        return FakeResponse(
            {
                "title": "sample paper",
                "publication_year": 2025,
                "doi": "https://doi.org/10.1234/example",
                "abstract_inverted_index": {"hello": [0], "world": [1]},
                "authorships": [
                    {
                        "author": {"display_name": "Ada Lovelace"},
                        "institutions": [{"display_name": "Analytical University"}],
                    }
                ],
                "primary_location": {
                    "landing_page_url": "https://example.test/paper",
                    "source": {"display_name": "Journal of Tests"},
                },
                "best_oa_location": {"pdf_url": "https://example.test/paper.pdf"},
                "biblio": {"volume": "1", "issue": "2", "first_page": "3", "last_page": "9"},
                "type": "article",
            }
        )

    monkeypatch.setattr(openalex.http_utils, "get", fake_get)

    metadata = openalex.search_by_doi("10.1234/example")

    assert metadata["title"] == "Sample Paper"
    assert metadata["abstract"] == "hello world"
    assert metadata["authors"][0]["full_name"] == "Ada Lovelace"
    assert metadata["authors"][0]["affiliation"]["institution"] == "Analytical University"
    assert metadata["venue_full"] == "Journal of Tests"
    assert metadata["paper_type"] == "journal"
    assert metadata["pdf_url"] == "https://example.test/paper.pdf"


def test_semantic_scholar_and_unpaywall_pdf_mapping(monkeypatch):
    monkeypatch.setattr(semantic_scholar.time, "sleep", lambda seconds: None)
    def fake_get(url, **kwargs):
        if "semanticscholar" in url:
            return FakeResponse(
                {
                    "title": "semantic paper",
                    "authors": [{"name": "Grace Hopper"}],
                "year": 2024,
                "venue": "S2 Conf",
                    "externalIds": {"DOI": "10.1/s2", "ArXiv": "2401.00001"},
                    "openAccessPdf": {"url": "https://example.test/s2.pdf"},
                }
            )
        return FakeResponse(
            {"best_oa_location": {"url_for_pdf": "https://example.test/upw.pdf"}}
        )

    monkeypatch.setattr(semantic_scholar.http_utils, "get", fake_get)

    s2_metadata = semantic_scholar.search_by_doi("10.1/s2")

    assert s2_metadata["authors"] == [{"full_name": "Grace Hopper"}]
    assert s2_metadata["preprint_id"] == "arXiv 2401.00001"
    assert s2_metadata["pdf_url"] == "https://example.test/s2.pdf"
    assert unpaywall.get_oa_pdf_url("10.1/s2") == "https://example.test/upw.pdf"


def test_fetch_metadata_fills_only_empty_fields_unless_overwrite():
    paper = SimpleNamespace(
        id=7,
        title="Existing Title",
        abstract="",
        year=None,
        venue_full="Local Venue",
        venue_acronym=None,
        paper_type=None,
        doi="10.1/example",
        url=None,
        preprint_id=None,
        category=None,
        volume=None,
        issue=None,
        pages=None,
        get_ordered_authors=lambda: [],
    )

    class PaperService:
        def __init__(self):
            self.updates = None

        def update_paper(self, paper_id, updates):
            self.updates = updates
            for key, value in updates.items():
                setattr(paper, key, value)
            return paper, ""

    class MetadataExtractor:
        def extract_from_doi(self, doi):
            return {
                "title": "Remote Title",
                "abstract": "Remote abstract",
                "authors": ["Remote Author"],
                "year": 2023,
                "venue_full": "Remote Venue",
                "paper_type": "journal",
                "url": "https://doi.org/10.1/example",
            }

    service = FetchMetadataService(PaperService(), MetadataExtractor(), NullLogger())

    result = service.fetch_metadata_for_paper(paper, overwrite=False)

    assert set(result["updated"]) == {"abstract", "authors", "paper_type", "url", "year"}
    assert paper.title == "Existing Title"
    assert paper.venue_full == "Local Venue"

    result = service.fetch_metadata_for_paper(paper, overwrite=True)

    assert "title" in result["updated"]
    assert paper.title == "Remote Title"
    assert paper.venue_full == "Remote Venue"


def test_pdf_download_fallback_tries_unpaywall_then_openalex(monkeypatch, tmp_path):
    class PDFManager:
        def __init__(self):
            self.pdf_dir = None
            self.app = None
            self.urls = []

        def download_pdf_from_url_with_proper_naming(self, url, paper_data):
            self.urls.append(url)
            if "unpaywall" in url:
                return "", "bad pdf", 0.1
            return str(tmp_path / "paper.pdf"), "", 0.2

    pdf_manager = PDFManager()
    service = SystemService(pdf_manager, NullLogger())
    monkeypatch.setattr(unpaywall, "get_oa_pdf_url", lambda doi: "https://unpaywall.test/p.pdf")
    monkeypatch.setattr(openalex, "get_pdf_url", lambda doi: "https://openalex.test/p.pdf")
    monkeypatch.setattr(semantic_scholar, "get_pdf_url", lambda doi: None)

    path, error, duration = service.download_pdf(
        "doi",
        "10.1/example",
        str(tmp_path),
        {"title": "Paper", "authors": ["A"], "year": 2024, "doi": "10.1/example"},
    )

    assert error == ""
    assert path == str(tmp_path / "paper.pdf")
    assert duration == 0.30000000000000004
    assert pdf_manager.urls == [
        "https://unpaywall.test/p.pdf",
        "https://openalex.test/p.pdf",
    ]


def test_lit_add_identifier_routes_unknown_subcommand(monkeypatch):
    class AddService:
        def add_by_identifier(self, identifier):
            assert identifier == "10.1145/example"
            return {"paper": SimpleNamespace(id=1), "pdf_path": None, "pdf_error": None}

    monkeypatch.setattr(
        add_command,
        "services",
        lambda ctx: {"add": AddService(), "pdf_manager": object(), "paper": object()},
    )
    monkeypatch.setattr(add_command.output, "paper_to_dict", lambda paper: {"id": paper.id})

    result = CliRunner().invoke(add_command.app, ["10.1145/example", "--json"])

    assert result.exit_code == 0
    assert '"id": 1' in result.output


def test_add_doi_uses_clean_doi_for_metadata_and_pdf(monkeypatch, tmp_path):
    calls = []

    class PaperService:
        def add_paper_from_metadata(self, paper_data, authors, collections):
            calls.append(("paper_data", paper_data))
            return SimpleNamespace(id=1)

    class MetadataExtractor:
        def extract_from_doi(self, doi):
            calls.append(("metadata", doi))
            return {
                "title": "DOI Paper",
                "authors": ["Author"],
                "doi": doi,
                "url": f"https://doi.org/{doi}",
            }

    class System:
        def download_pdf(self, source, identifier, pdf_dir, paper_data):
            calls.append(("download", source, identifier, paper_data["doi"]))
            return None, "No PDF URL candidates found", 0.0

    from ng.services.add_paper import AddPaperService
    import ng.services.add_paper as add_paper

    monkeypatch.setattr(add_paper, "get_pdf_directory", lambda: str(tmp_path))
    service = AddPaperService(
        PaperService(),
        MetadataExtractor(),
        System(),
        NullLogger(),
    )

    service.add_doi_paper("https://doi.org/10.1145/example")

    assert ("metadata", "10.1145/example") in calls
    assert ("download", "doi", "10.1145/example", "10.1145/example") in calls
    paper_data = next(value for kind, value in calls if kind == "paper_data")
    assert paper_data["doi"] == "10.1145/example"
