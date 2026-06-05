from types import SimpleNamespace

from lit import output


class FakePaper:
    id = 1
    title = "Attention Is All You Need"
    year = 2017
    venue_full = "NeurIPS"
    venue_acronym = "NeurIPS"
    paper_type = "conference"
    abstract = "..."
    notes = None
    doi = "10.1/example"
    arxiv_id = "1706.03762"
    openreview_id = "abc123"
    dblp_key = "conf/nips/VaswaniSPUJGKP17"
    openalex_id = "https://openalex.org/W2741809807"
    semantic_scholar_id = "012345"
    category = "cs.CL"
    url = "https://example.test/paper"
    pdf_path = None
    parsed_pdf_path = None
    collections = []
    added_date = None
    modified_date = None

    def get_ordered_authors(self):
        return [SimpleNamespace(full_name="Ada Lovelace")]


class FakeAuthor:
    id = 2
    full_name = "Ada Lovelace"
    first_name = "Ada"
    last_name = "Lovelace"
    email = None
    personal_url = None
    faculty_url = None
    scholar_url = None
    orcid = "0000-0001-2345-6789"
    openalex_id = "https://openalex.org/A123"
    semantic_scholar_id = "456"
    dblp_pid = "12/3456"
    affiliation = None
    paper_authors = []


def test_paper_to_dict_defaults_to_urls():
    data = output.paper_to_dict(FakePaper())
    assert data["arxiv_url"] == "https://arxiv.org/abs/1706.03762"
    assert data["openreview_url"] == "https://openreview.net/forum?id=abc123"
    assert data["dblp_url"] == "https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17"
    assert data["openalex_url"] == "https://openalex.org/W2741809807"
    assert data["semantic_scholar_url"] == "https://www.semanticscholar.org/paper/012345"
    assert "arxiv_id" not in data


def test_paper_to_dict_key_mode_returns_raw_ids():
    data = output.paper_to_dict(FakePaper(), use_keys=True)
    assert data["arxiv_id"] == "1706.03762"
    assert data["openreview_id"] == "abc123"
    assert data["dblp_key"] == "conf/nips/VaswaniSPUJGKP17"
    assert data["openalex_id"] == "https://openalex.org/W2741809807"
    assert data["semantic_scholar_id"] == "012345"
    assert "arxiv_url" not in data


def test_author_to_dict_defaults_to_urls():
    data = output.author_to_dict(FakeAuthor())
    assert data["orcid_url"] == "https://orcid.org/0000-0001-2345-6789"
    assert data["openalex_url"] == "https://openalex.org/A123"
    assert data["semantic_scholar_url"] == "https://www.semanticscholar.org/author/456"
    assert data["dblp_url"] == "https://dblp.org/pid/12/3456.html"
    assert "orcid" not in data


def test_author_to_dict_key_mode_returns_raw_ids():
    data = output.author_to_dict(FakeAuthor(), use_keys=True)
    assert data["orcid"] == "0000-0001-2345-6789"
    assert data["openalex_id"] == "https://openalex.org/A123"
    assert data["semantic_scholar_id"] == "456"
    assert data["dblp_pid"] == "12/3456"
    assert "orcid_url" not in data
