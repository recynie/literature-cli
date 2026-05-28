# Database Schema Reference

LiteratureCLI uses a SQLite database (`papers.db`) managed by SQLAlchemy ORM with Alembic migrations.

## Tables Overview

```
papers
authors
affiliations
paper_authors      ← join table (papers ↔ authors, with ordering)
paper_collections  ← join table (papers ↔ collections)
collections
```

---

## `papers`

Core table. One row per paper.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key, auto-increment |
| `uuid` | VARCHAR(36) | No | UUID v4, unique, indexed; stable cross-device identifier |
| `title` | VARCHAR(500) | No | Full paper title |
| `abstract` | TEXT | Yes | Paper abstract |
| `venue_full` | VARCHAR(255) | Yes | Full venue name, e.g. `Neural Information Processing Systems` |
| `venue_acronym` | VARCHAR(50) | Yes | Short venue name, e.g. `NeurIPS` |
| `year` | INTEGER | Yes | Publication year |
| `volume` | VARCHAR(20) | Yes | Journal volume |
| `issue` | VARCHAR(20) | Yes | Journal issue |
| `pages` | VARCHAR(50) | Yes | Page range, e.g. `1234–1245` |
| `paper_type` | VARCHAR(50) | Yes | One of: `conference`, `journal`, `preprint`, `workshop`, `website` |
| `doi` | VARCHAR(255) | Yes | DOI string, e.g. `10.1038/s41586-023-06139-9` |
| `preprint_id` | VARCHAR(100) | Yes | Preprint identifier, e.g. `arXiv 1706.03762` |
| `category` | VARCHAR(50) | Yes | arXiv category, e.g. `cs.LG` |
| `url` | VARCHAR(500) | Yes | Canonical URL (abstract page, project page, etc.) |
| `pdf_path` | VARCHAR(500) | Yes | Absolute path to local PDF file |
| `html_snapshot_path` | VARCHAR(500) | Yes | Absolute path to local HTML snapshot (reserved, not yet used) |
| `notes` | TEXT | Yes | Free-form user notes; populated by `--summarize` |
| `added_date` | DATETIME | No | Timestamp when the record was created |
| `modified_date` | DATETIME | No | Timestamp of last update (auto-updated on write) |

---

## `authors`

One row per unique person. Authors are reused across papers.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key |
| `full_name` | VARCHAR(255) | No | Display name, e.g. `Ashish Vaswani` |
| `first_name` | VARCHAR(100) | Yes | Given name |
| `last_name` | VARCHAR(100) | Yes | Family name |
| `email` | VARCHAR(255) | Yes | Contact email |
| `affiliation_id` | INTEGER | Yes | FK → `affiliations.id` |
| `personal_url` | VARCHAR(500) | Yes | Personal homepage (GitHub Pages, blog, etc.) |
| `faculty_url` | VARCHAR(500) | Yes | Institutional faculty page |
| `scholar_url` | VARCHAR(500) | Yes | Google Scholar or Semantic Scholar profile |
| `orcid` | VARCHAR(50) | Yes | ORCID identifier, e.g. `0000-0001-2345-6789` |

---

## `affiliations`

Deduplicated institution/department pairs. Unique constraint on `(institution, department)`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key |
| `institution` | VARCHAR(255) | No | Institution name, e.g. `Google DeepMind` |
| `department` | VARCHAR(255) | Yes | Department or lab, e.g. `Brain Team` |
| `url` | VARCHAR(500) | Yes | Institution or department URL |

---

## `paper_authors`

Join table linking papers to authors with explicit author ordering.

| Column | Type | Description |
|--------|------|-------------|
| `paper_id` | INTEGER | FK → `papers.id` (CASCADE DELETE) |
| `author_id` | INTEGER | FK → `authors.id` (CASCADE DELETE) |
| `position` | INTEGER | 0-based author order on the paper |

Primary key is `(paper_id, author_id, position)`.

---

## `paper_collections`

Simple join table linking papers to collections.

| Column | Type | Description |
|--------|------|-------------|
| `paper_id` | INTEGER | FK → `papers.id` |
| `collection_id` | INTEGER | FK → `collections.id` |

Primary key is `(paper_id, collection_id)`.

---

## `collections`

Named groups of papers.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | INTEGER | No | Primary key |
| `name` | VARCHAR(255) | No | Unique collection name |
| `description` | TEXT | Yes | Optional description |
| `created_at` | DATETIME | No | Creation timestamp |
| `last_modified` | DATETIME | Yes | Last modification timestamp |

---

## Entity-Relationship Summary

```
Paper ──< PaperAuthor >── Author ──> Affiliation
  │
  └──< paper_collections >── Collection
```

- A paper has **many authors** (ordered via `paper_authors.position`).
- An author belongs to **at most one** affiliation at a time.
- A paper can belong to **many collections**; a collection holds **many papers**.
- Deleting a paper cascades to `paper_authors` and `paper_collections`. Authors and affiliations are not deleted automatically.

---

## Migrations

Schema changes are managed with Alembic. Migration scripts live in `ng/alembic/versions/`. To apply pending migrations:

```bash
uv run alembic upgrade head
```
