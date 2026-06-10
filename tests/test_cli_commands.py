from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from lit.commands import affiliation as affiliation_command
from lit.commands import author as author_command
from lit.commands import collect as collect_command
from lit.commands import config as config_command
from lit.commands import db as db_command
from lit.commands import delete as delete_command
from lit.commands import edit as edit_command
from lit.commands import export as export_command
from lit.commands import list as list_command
from lit.commands import pdf as pdf_command
from lit.commands import search as search_command
from lit.commands import show as show_command


runner = CliRunner()


class FakeAuthor:
    def __init__(self, id=1, full_name="Ada Lovelace", affiliation=None):
        self.id = id
        self.full_name = full_name
        self.first_name = full_name.split()[0]
        self.last_name = full_name.split()[-1]
        self.email = None
        self.personal_url = None
        self.faculty_url = None
        self.scholar_url = None
        self.orcid = None
        self.openalex_id = None
        self.semantic_scholar_id = None
        self.dblp_pid = None
        self.affiliation = affiliation
        self.paper_authors = []


class FakeAffiliation:
    def __init__(self, id=1, institution="Test University", department="CS", url=None):
        self.id = id
        self.institution = institution
        self.department = department
        self.url = url
        self.authors = []


class FakeCollection:
    def __init__(self, id=1, name="reading"):
        self.id = id
        self.name = name
        self.papers = []
        self.created_at = None
        self.last_modified = None


class FakePaper:
    def __init__(
        self,
        id=1,
        title="Paper A",
        year=2024,
        venue_full="TestConf",
        authors=None,
        pdf_path=None,
        parsed_pdf_path=None,
        doi=None,
        arxiv_id=None,
        openreview_id=None,
        dblp_key=None,
        openalex_id=None,
        semantic_scholar_id=None,
        url=None,
        collections=None,
        notes=None,
    ):
        self.id = id
        self.title = title
        self.year = year
        self.venue_full = venue_full
        self.venue_acronym = venue_full
        self.paper_type = "conference"
        self.abstract = None
        self.notes = notes
        self.doi = doi
        self.category = None
        self.url = url
        self.pdf_path = pdf_path
        self.parsed_pdf_path = parsed_pdf_path
        self.collections = collections or []
        self.added_date = None
        self.modified_date = None
        self.arxiv_id = arxiv_id
        self.openreview_id = openreview_id
        self.dblp_key = dblp_key
        self.openalex_id = openalex_id
        self.semantic_scholar_id = semantic_scholar_id
        self._authors = authors or [FakeAuthor()]

    def get_ordered_authors(self):
        return self._authors


@pytest.fixture
def json_ctx():
    return typer.Context(typer.Typer(), obj={"json": True, "db_path": "/tmp/test.db"})


def test_list_papers_supports_sort_and_limit(monkeypatch):
    papers = [
        FakePaper(id=1, title="Beta", year=2022),
        FakePaper(id=2, title="Alpha", year=2024),
        FakePaper(id=3, title="Gamma", year=2023),
    ]

    class PaperService:
        def get_all_papers(self):
            return list(papers)

    monkeypatch.setattr(list_command, "services", lambda ctx: {"paper": PaperService()})

    app = typer.Typer()
    app.command()(list_command.list_papers)
    result = runner.invoke(app, ["--sort", "title", "--limit", "2", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [paper["title"] for paper in data["papers"]] == ["Alpha", "Beta"]
    assert data["count"] == 2


def test_show_returns_not_found(monkeypatch):
    class PaperService:
        def get_paper_by_id(self, paper_id):
            return None

    monkeypatch.setattr(show_command, "services", lambda ctx: {"paper": PaperService()})

    app = typer.Typer()
    app.command()(show_command.show)
    result = runner.invoke(app, ["9", "--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["code"] == "NOT_FOUND"


def test_search_routes_exact_and_fuzzy(monkeypatch):
    calls = []
    paper = FakePaper()

    class SearchService:
        def search_papers(self, query, fields):
            calls.append(("exact", query, fields))
            return [paper]

        def fuzzy_search_papers(self, query, threshold):
            calls.append(("fuzzy", query, threshold))
            return [paper]

    monkeypatch.setattr(search_command, "services", lambda ctx: {"search": SearchService()})

    app = typer.Typer()
    app.command()(search_command.search)

    result = runner.invoke(app, ["transformer", "--fields", "title,abstract", "--json"])
    assert result.exit_code == 0
    assert calls[0] == ("exact", "transformer", ["title", "abstract"])

    result = runner.invoke(app, ["trnsformer", "--fuzzy", "--threshold", "77", "--json"])
    assert result.exit_code == 0
    assert calls[1] == ("fuzzy", "trnsformer", 77)


def test_filter_builds_all_supported_filters(monkeypatch):
    captured = {}

    class SearchService:
        def filter_papers(self, filters):
            captured.update(filters)
            return [FakePaper()]

    monkeypatch.setattr(search_command, "services", lambda ctx: {"search": SearchService()})

    app = typer.Typer()
    app.command("filter")(search_command.filter)
    result = runner.invoke(
        app,
        [
            "--author",
            "Ada",
            "--year",
            "2024",
            "--year-range",
            "2020-2024",
            "--venue",
            "NeurIPS",
            "--type",
            "conference",
            "--collection",
            "reading",
            "--affiliation",
            "MIT",
            "--query",
            "attention",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "author": "Ada",
        "year": 2024,
        "year_range": (2020, 2024),
        "venue": "NeurIPS",
        "paper_type": "conference",
        "collection": "reading",
        "affiliation": "MIT",
        "all": "attention",
    }


def test_edit_updates_fetches_and_summarizes(monkeypatch):
    paper = FakePaper(id=5, title="Old", pdf_path="files/paper.pdf")
    updated_paper = FakePaper(id=5, title="New", pdf_path="files/paper.pdf", notes="summary")
    calls = {"update": [], "fetch": [], "summary": []}

    class PaperService:
        def get_paper_by_id(self, paper_id):
            return updated_paper if calls["update"] else paper

        def update_paper(self, paper_id, updates):
            calls["update"].append(updates)
            return updated_paper, ""

    class MetadataService:
        def generate_paper_summary(self, pdf_path):
            calls["summary"].append(pdf_path)
            return "summary"

    class FetchService:
        def fetch_metadata_for_paper(self, paper_obj, overwrite=False):
            calls["fetch"].append((paper_obj.id, overwrite))
            return {
                "paper": updated_paper,
                "updated": ["title"],
                "metadata": {"title": "Remote"},
                "warning": "remote",
            }

    monkeypatch.setattr(
        edit_command,
        "services",
        lambda ctx: {
            "paper": PaperService(),
            "metadata": MetadataService(),
            "fetch": FetchService(),
        },
    )

    app = typer.Typer()
    app.command()(edit_command.edit)
    result = runner.invoke(
        app,
        [
            "5",
            "--title",
            "New",
            "--summarize",
            "--fetch",
            "--overwrite",
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["paper"]["title"] == "New"
    assert data["fetched_fields"] == ["title"]
    assert data["fetched_metadata"] == {"title": "Remote"}
    assert calls["summary"] == ["files/paper.pdf"]
    assert calls["fetch"] == [(5, True)]
    assert {"title": "New", "notes": "summary"} in calls["update"]


def test_config_command_reports_detected_files(tmp_path, monkeypatch):
    project_dir = tmp_path / "workspace"
    project_config_dir = project_dir / ".litcli"
    project_config_dir.mkdir(parents=True)
    (project_config_dir / "config.toml").write_text("[openai]\nmodel = \"project-model\"\n")

    user_config_dir = tmp_path / "user-config"
    user_config_dir.mkdir()
    (user_config_dir / "auth.toml").write_text("[openai]\napi_key = \"secret\"\n")

    monkeypatch.setattr(config_command, "USER_CONFIG_DIR", user_config_dir)
    monkeypatch.chdir(project_dir)
    monkeypatch.setenv("OPENAI_MODEL", "project-model")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = runner.invoke(config_command.app, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["project_config_dir"] == str(project_config_dir)
    assert data["files"]["project_config"] == str(project_config_dir / "config.toml")
    assert data["files"]["user_auth"] == str(user_config_dir / "auth.toml")
    assert data["resolved"]["OPENAI_MODEL"] == "project-model"
    assert data["resolved"]["OPENAI_API_KEY_SET"] is False


def test_delete_supports_multiple_ids_and_reports_count(monkeypatch):
    class PaperService:
        def delete_papers(self, ids):
            assert ids == [1, 2, 3]
            return 3

    monkeypatch.setattr(delete_command, "services", lambda ctx: {"paper": PaperService()})

    app = typer.Typer()
    app.command()(delete_command.delete)
    result = runner.invoke(app, ["1", "--ids", "2,3", "--force", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["deleted"] == 3
    assert data["ids"] == [1, 2, 3]


def test_export_json_writes_output_file(monkeypatch, tmp_path):
    papers = [FakePaper(id=1, title="Paper A")]
    out = tmp_path / "export.json"

    class PaperService:
        def get_paper_by_id(self, paper_id):
            return papers[0]

    monkeypatch.setattr(export_command, "services", lambda ctx: {"paper": PaperService(), "search": None})

    app = typer.Typer()
    app.command()(export_command.export)
    result = runner.invoke(
        app,
        ["--format", "json", "--ids", "1", "--output", str(out), "--json"],
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["format"] == "json"
    assert data["count"] == 1
    assert out.exists()
    saved = json.loads(out.read_text())
    assert saved[0]["title"] == "Paper A"


def test_collection_commands_cover_crud_and_membership(monkeypatch):
    collection = FakeCollection(id=7, name="reading")
    renamed = FakeCollection(id=7, name="done")
    paper = FakePaper(collections=[collection])

    class CollectionService:
        def get_all_collections(self):
            return [collection]

        def add_collection(self, name):
            assert name == "reading"
            return collection

        def get_collection_by_name(self, name):
            return {"reading": collection, "done": renamed}.get(name)

        def update_collection_name(self, collection_id, new_name):
            assert collection_id == 7
            assert new_name == "done"
            return True

        def delete_collection(self, collection_id):
            assert collection_id == 7
            return True

        def add_papers_to_collection(self, ids, name):
            assert ids == [1, 2]
            assert name == "reading"
            return 2

        def remove_papers_from_collection(self, ids, name):
            assert ids == [1]
            assert name == "reading"
            return 1, []

        def purge_empty_collections(self):
            return 1

    class SearchService:
        def filter_papers(self, filters):
            assert filters == {"collection": "reading"}
            return [paper]

    monkeypatch.setattr(
        collect_command,
        "services",
        lambda ctx: {"collection": CollectionService(), "search": SearchService()},
    )

    result = runner.invoke(collect_command.app, ["create", "reading", "--json"])
    assert result.exit_code == 0

    result = runner.invoke(collect_command.app, ["show", "reading", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["count"] == 1

    result = runner.invoke(collect_command.app, ["rename", "reading", "done", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["collection"]["name"] == "done"

    result = runner.invoke(collect_command.app, ["add", "reading", "--ids", "1,2", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["added"] == 2

    result = runner.invoke(collect_command.app, ["remove", "reading", "--ids", "1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["removed"] == 1

    result = runner.invoke(collect_command.app, ["purge", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["purged"] == 1

    result = runner.invoke(collect_command.app, ["delete", "reading", "--force", "--json"])
    assert result.exit_code == 0


def test_author_commands_cover_filters_crud_and_merge(monkeypatch):
    affiliation = FakeAffiliation()
    author = FakeAuthor(id=3, affiliation=affiliation)
    paper = FakePaper(id=8, authors=[author])
    calls = {"filters": None, "add": None, "edit": None, "merge": None}

    class AuthorService:
        def get_all_authors(self, filters):
            calls["filters"] = filters
            return [author]

        def search_authors(self, query):
            assert query == "Ada"
            return [author]

        def get_author_by_id(self, author_id):
            return author if author_id == 3 else None

        def get_author_papers(self, author_id):
            assert author_id == 3
            return [paper]

        def add_author(self, data):
            calls["add"] = data
            return author

        def update_author(self, author_id, data):
            calls["edit"] = (author_id, data)
            return author, ""

        def delete_author(self, author_id, force=False):
            return True

        def merge_authors(self, target, source_ids):
            calls["merge"] = (target, source_ids)
            return author

    monkeypatch.setattr(author_command, "services", lambda ctx: {"author": AuthorService()})

    result = runner.invoke(
        author_command.app,
        ["list", "--institution", "Test University", "--has-email", "--json"],
    )
    assert result.exit_code == 0
    assert calls["filters"] == {"institution": "Test University", "has_email": True}

    result = runner.invoke(author_command.app, ["search", "Ada", "--json"])
    assert result.exit_code == 0

    result = runner.invoke(author_command.app, ["show", "3", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["count"] == 1

    result = runner.invoke(
        author_command.app,
        ["add", "Ada Lovelace", "--institution", "Test University", "--department", "CS", "--json"],
    )
    assert result.exit_code == 0
    assert calls["add"]["institution"] == "Test University"

    result = runner.invoke(author_command.app, ["edit", "3", "--email", "ada@example.com", "--json"])
    assert result.exit_code == 0
    assert calls["edit"] == (3, {"email": "ada@example.com"})

    result = runner.invoke(author_command.app, ["merge", "--target", "3", "--sources", "4,5", "--json"])
    assert result.exit_code == 0
    assert calls["merge"] == (3, [4, 5])

    result = runner.invoke(author_command.app, ["delete", "3", "--force", "--json"])
    assert result.exit_code == 0


def test_affiliation_commands_cover_crud(monkeypatch):
    affiliation = FakeAffiliation(id=4)
    calls = {"edit": None}

    class AffiliationService:
        def get_all_affiliations(self):
            return [affiliation]

        def get_affiliation_by_id(self, affiliation_id):
            return affiliation if affiliation_id == 4 else None

        def add_affiliation(self, data):
            assert data["institution"] == "Test University"
            return affiliation

        def update_affiliation(self, affiliation_id, data):
            calls["edit"] = (affiliation_id, data)
            return affiliation, ""

        def delete_affiliation(self, affiliation_id, force=False):
            return True

    monkeypatch.setattr(
        affiliation_command,
        "services",
        lambda ctx: {"affiliation": AffiliationService()},
    )

    result = runner.invoke(affiliation_command.app, ["list", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["count"] == 1

    result = runner.invoke(affiliation_command.app, ["show", "4", "--json"])
    assert result.exit_code == 0

    result = runner.invoke(affiliation_command.app, ["add", "Test University", "--department", "CS", "--json"])
    assert result.exit_code == 0

    result = runner.invoke(affiliation_command.app, ["edit", "4", "--url", "https://example.test", "--json"])
    assert result.exit_code == 0
    assert calls["edit"] == (4, {"url": "https://example.test"})

    result = runner.invoke(affiliation_command.app, ["delete", "4", "--force", "--json"])
    assert result.exit_code == 0


def test_pdf_commands_cover_path_open_download_and_parse_skip(monkeypatch, tmp_path):
    pdf_file = tmp_path / "paper.pdf"
    pdf_file.write_bytes(b"%PDF-1.4")
    parsed_dir = tmp_path / "parsed"
    parsed_dir.mkdir()
    parsed_md = parsed_dir / "1.md"
    parsed_md.write_text("parsed")

    paper = FakePaper(id=1, title="PDF Paper", pdf_path="rel/paper.pdf", parsed_pdf_path="parsed/1.md")
    calls = {"download": None, "update": []}

    class PaperService:
        def get_paper_by_id(self, paper_id):
            return paper if paper_id == 1 else None

        def update_paper(self, paper_id, updates):
            calls["update"].append(updates)
            return paper, ""

    class PDFManager:
        def get_absolute_path(self, rel):
            return str(pdf_file)

        def process_pdf_path(self, url, paper_data, existing):
            return "saved/paper.pdf", ""

    class SystemService:
        def open_pdf(self, path):
            return True, ""

        def download_pdf(self, source, identifier, pdf_dir, paper_data):
            calls["download"] = (source, identifier, pdf_dir, paper_data["title"])
            return str(pdf_file), "", 1.25

    monkeypatch.setattr(
        pdf_command,
        "services",
        lambda ctx: {
            "paper": PaperService(),
            "pdf_manager": PDFManager(),
            "system": SystemService(),
            "app": object(),
        },
    )
    monkeypatch.setattr(pdf_command, "get_pdf_directory", lambda: str(tmp_path))
    monkeypatch.setattr(pdf_command, "mineru_config_from_env", lambda: object())
    monkeypatch.setattr(pdf_command, "get_db_manager", lambda: SimpleNamespace(db_path=str(tmp_path / "papers.db")))

    result = runner.invoke(pdf_command.app, ["path", "1", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["path"] == str(pdf_file)

    result = runner.invoke(pdf_command.app, ["open", "1", "--json"])
    assert result.exit_code == 0

    paper.arxiv_id = "2501.00001"
    result = runner.invoke(pdf_command.app, ["download", "1", "--no-parse", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["pdf_path"] == str(pdf_file)
    assert calls["download"][0:2] == ("arxiv", "2501.00001")

    result = runner.invoke(pdf_command.app, ["parse", "1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["skipped"] is True
    assert data["markdown_path"].endswith("parsed/1.md")


def test_db_commands_cover_check_and_clean(monkeypatch):
    class HealthService:
        def run_full_diagnostic(self):
            return {"status": "ok"}

        def clean_orphaned_records(self):
            return 1

        def clean_orphaned_pdfs(self):
            return 2

        def clean_orphaned_htmls(self):
            return 3

        def fix_absolute_pdf_paths(self):
            return 4

        def clean_pdf_filenames(self):
            return 5

    monkeypatch.setattr(db_command, "_service", lambda ctx: HealthService())

    result = runner.invoke(db_command.app, ["check", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["report"] == {"status": "ok"}

    result = runner.invoke(db_command.app, ["clean", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["cleaned"] == {
        "orphaned_records": 1,
        "orphaned_pdfs": 2,
        "orphaned_htmls": 3,
        "absolute_pdf_paths": 4,
        "pdf_filenames": 5,
    }
