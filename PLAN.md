# LiteratureCLI Implementation Plan

## Context

The `ng/` core layer (database models, services, migrations) is fully ported from papercli and working. What's missing is the CLI layer (`lit/`) and the pi skill definition (`skills/literature-cli/SKILL.md`). This plan covers implementing both, as specified in `docs/cli.md` and `docs/skill.md`.

## Architecture Overview

```
lit <command> [--json]
    → lit/main.py (typer app, DB init, --json global flag)
    → lit/commands/*.py (thin command handlers)
    → ng/services/*.py (business logic, already built)
    → lit/output.py (JSON or human-readable formatting)
```

All services require an `app` object with `_add_log(key, msg)` and `notify(msg, severity)` — the CLI layer provides `CliLogger` for this.

## Implementation Phases

### Phase 1: Foundation (3 files)

**`lit/logger.py`** — CliLogger implementing the `app` interface services expect:
```python
class CliLogger:
    def _add_log(self, key: str, message: str): logging.debug(...)
    def notify(self, message: str, severity: str = "information"): logging.info/error(...)
```

**`lit/output.py`** — Unified output + paper serialization:
- `paper_to_dict(paper: Paper) -> dict` — converts ORM model to the JSON schema from docs
- `collection_to_dict(col: Collection) -> dict` — same for collections
- `print_result(data, as_json)` — prints JSON (indented) or rich-formatted text
- `error(message, code, as_json)` — prints error + sys.exit(1)
- Human-readable formatting uses `rich` for tables and colored output

**`lit/main.py`** — typer app entry point:
- Global `--json` flag via typer callback
- On startup: load `.env`, init database (`init_database(db_path)`)
- Register all sub-commands from `lit/commands/`
- DB path: `PAPERCLI_DATA_DIR` env var or `~/.papercli/papers.db`

### Phase 2: Commands (9 files in `lit/commands/`)

Each command file:
1. Creates a `typer.Typer` instance (or uses `@app.command` decorators)
2. Accepts `--json` via typer Context
3. Initializes needed services with `CliLogger()`
4. Calls service methods
5. Formats output via `output.py`

**`add.py`** — `lit add <source> <identifier> [--json]`
- Sources: `arxiv`, `dblp`, `openreview`, `doi`, `pdf`, `bib`, `ris`, `manual`
- Creates: `PDFManager`, `MetadataExtractor(pdf_manager, app)`, `PaperService(app)`, `SystemService(pdf_manager, app)`, `AddPaperService(paper_service, metadata_extractor, system_service, app)`
- For `manual`: calls `AddPaperService.add_manual_paper(title)`
- Returns paper dict (single) or `{papers, errors, count}` (batch)

**`search.py`** — `lit search <query> [--fields] [--fuzzy] [--threshold] [--json]`
- `SearchService(app).search_papers(query, fields)` or `.fuzzy_search_papers(query, threshold)`
- Human output: rich table with title, authors, year, venue

**`list.py`** — `lit list [--limit] [--sort] [--json]`
- `PaperService(app).get_all_papers()`, apply sort/limit in Python
- Also handles `lit filter` as the same command group (typer allows both `lit search` and `lit filter`)
- Actually, `filter` should be its own command: `SearchService(app).filter_papers(filters_dict)`

**`show.py`** — `lit show <id> [--json]`
- `PaperService(app).get_paper_by_id(id)`
- Human output: full detail view with abstract, notes, collections

**`edit.py`** — `lit edit <id> --title/--notes/--year/--venue-full/--venue-acronym/--paper-type/--doi/--url [--json]`
- Build dict of non-None field overrides, call `PaperService(app).update_paper(id, data)`
- `--extract-pdf`: re-extract metadata from linked PDF via LLM
- `--summarize`: LLM summary → notes field

**`delete.py`** — `lit delete <id>` or `lit delete --ids 1,2,3`
- `PaperService(app).delete_paper(id)` or `.delete_papers(ids)`
- Confirmation prompt (skip with `--force`)

**`export.py`** — `lit export --format <fmt> [--ids] [--collection] [--output] [--json]`
- Get papers via `PaperService` or `CollectionService`
- Call `ng/services/export.py` functions directly (they take `List[Paper]`)
- `--output` writes to file; otherwise stdout

**`collect.py`** — `lit collect <action> [args]`
- Actions: `list`, `show`, `create`, `rename`, `delete`, `add`, `remove`, `purge`
- Uses `CollectionService(app)`

**`pdf.py`** — `lit pdf <action> <id>`
- Actions: `path` (prints absolute path), `open` (opens in system viewer), `download` (re-downloads)
- Uses `PDFManager(app)`, `SystemService(pdf_manager, app)`

**`db.py`** — `lit db check [--json]` and `lit db clean`
- Uses `DatabaseHealthService(db_path, app)`
- `check`: runs `run_full_diagnostic()`, prints summary
- `clean`: runs clean methods

### Phase 3: Pi Skill (1 file)

**`skills/literature-cli/SKILL.md`** — copy from `docs/skill.md` content:
- Frontmatter with name/description
- Routing table mapping user intent → `lit` commands
- Typical workflow patterns (5 patterns from docs)
- JSON schema for Paper and Collection objects
- Usage notes (always use --json, API key requirements, etc.)

## Key Design Decisions

1. **Service initialization per-command**: Each command initializes its own service instances with CliLogger. This is simple and avoids global state. Services are lightweight — they just hold references.

2. **No async**: The papercli reference code uses some `_async` methods for background processing. CLI commands are synchronous — we only call the non-async variants.

3. **`paper_to_dict` in output.py**: A single serialization function converting Paper ORM objects to the JSON schema. All commands use it.

4. **Human-readable output via rich**: Use `rich.table.Table` and `rich.console.Console` for formatted terminal output when not in `--json` mode.

5. **Error handling**: Wrap service calls in try/except, convert exceptions to `{"ok": false, "error": ..., "code": ...}` via `output.error()`.

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `lit/__init__.py` | Create | Package init |
| `lit/logger.py` | Create | CliLogger class |
| `lit/output.py` | Create | JSON/human output + paper_to_dict |
| `lit/main.py` | Create | typer app, DB init, global --json |
| `lit/commands/__init__.py` | Create | Package init |
| `lit/commands/add.py` | Create | lit add subcommands |
| `lit/commands/search.py` | Create | lit search + lit filter |
| `lit/commands/list.py` | Create | lit list |
| `lit/commands/show.py` | Create | lit show |
| `lit/commands/edit.py` | Create | lit edit |
| `lit/commands/delete.py` | Create | lit delete |
| `lit/commands/export.py` | Create | lit export |
| `lit/commands/collect.py` | Create | lit collect |
| `lit/commands/pdf.py` | Create | lit pdf |
| `lit/commands/db.py` | Create | lit db |
| `skills/literature-cli/SKILL.md` | Create | Pi skill definition |

## Verification

1. **Install**: `uv pip install -e .` — should succeed with entry point `lit`
2. **Help**: `lit --help` shows all commands; `lit add --help` shows subcommand options
3. **Import test**: `uv run python -c "from lit.main import app; print('OK')"`
4. **Add arXiv paper**: `lit add arxiv 1706.03762 --json` — should return valid paper JSON
5. **Search**: `lit search "attention" --json` — should return matching papers
6. **List**: `lit list --json` — should show all papers
7. **Show**: `lit show 1 --json` — full paper detail
8. **Export**: `lit export --format bibtex --collection "my-papers"` — valid BibTeX output
9. **Full flow**: add → search → collect → export → delete — each step returning valid JSON
10. **Error case**: `lit add arxiv invalid_id` — should return `{"ok": false, "error": "...", "code": "NOT_FOUND"}`

## Execution Order

1. `lit/logger.py` + `lit/output.py` + `lit/main.py` (foundation, no deps)
2. `lit/commands/add.py` (most complex, validates the pattern)
3. `lit/commands/show.py` + `lit/commands/list.py` + `lit/commands/search.py`
4. `lit/commands/delete.py` + `lit/commands/edit.py`
5. `lit/commands/export.py` + `lit/commands/collect.py`
6. `lit/commands/pdf.py` + `lit/commands/db.py`
7. `skills/literature-cli/SKILL.md`
