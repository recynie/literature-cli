---
name: literature-cli
description: "Manage research papers from the command line: import papers with a unified identifier entrypoint, search, filter, edit/fetch metadata, export citations, organize collections, manage authors/affiliations, PDFs, and database maintenance. Use when the user wants to create a literature base, conduct academic research, or mentions papers, arXiv IDs, DOIs, BibTeX, RIS, citations, lit cli, literature CLI, literature search, paper organization, reference management, or bibliography export."
---

# LiteratureCLI

Use `lit` for academic paper management. Prefer `--json` for all commands whose output must be parsed; human-readable output is for display only.

## Routing

| User intent | Command |
|---|---|
| Import one paper or file | `lit add <identifier-or-path-or-title> --json` |
| Import from arXiv | `lit add <arxiv-id-or-url> --json` |
| Import from DOI | `lit add <doi-or-doi-url> --json` |
| Import from OpenReview | `lit add <openreview-url> --json` |
| Import from DBLP | `lit add <dblp-url> --json` |
| Import by title search | `lit add "paper title" --json` |
| Import local PDF | `lit add <path.pdf> --json` |
| Bulk import BibTeX | `lit add <path.bib> --json` |
| Bulk import RIS | `lit add <path.ris> --json` |
| Manual entry | `lit add manual --title "..." --json` |
| Search papers | `lit search "<query>" --json` |
| Fuzzy search | `lit search "<query>" --fuzzy --threshold 60 --json` |
| Filter papers | `lit filter --author/--year/--year-range/--venue/--type/--collection/--affiliation/--query --json` |
| List papers | `lit list --json` |
| Show details | `lit show <id> --json` |
| Edit metadata | `lit edit <id> --title/--venue-full/--venue-acronym/--paper-type/--doi/--url/--notes/--year <value> --json` |
| Fetch missing metadata | `lit edit <id> --fetch --json` |
| Refresh metadata with overwrite | `lit edit <id> --fetch --overwrite --json` |
| Extract PDF metadata | `lit edit <id> --extract-pdf --json` (needs OPENAI_API_KEY) |
| Summarize paper | `lit edit <id> --summarize --json` (needs OPENAI_API_KEY) |
| Delete papers | `lit delete <id> --force --json` or `lit delete --ids 1,2,3 --force --json` |
| Export citations | `lit export --format bibtex/ieee/markdown/html/json --ids 1,2 --json` |
| Export by collection | `lit export --format bibtex --collection "name" --json` |
| Export to file | `lit export --format bibtex --output /path/to/file --ids 1,2 --json` |
| List authors | `lit author list --json` |
| Search authors | `lit author search "<name>" --json` |
| Show author | `lit author show <id> --json` |
| Add author | `lit author add "<full-name>" --email/--personal-url/--faculty-url/--scholar-url/--orcid/--institution/--department --json` |
| Edit author | `lit author edit <id> --email/--personal-url/--faculty-url/--scholar-url/--orcid/--institution/--department <value> --json` |
| Delete author | `lit author delete <id> --force --json` |
| Merge duplicate authors | `lit author merge --target <id> --sources 2,3 --json` |
| List affiliations | `lit affiliation list --json` |
| Show affiliation | `lit affiliation show <id> --json` |
| Add affiliation | `lit affiliation add "<institution>" --department "<department>" --url "<url>" --json` |
| Edit affiliation | `lit affiliation edit <id> --institution/--department/--url <value> --json` |
| Delete affiliation | `lit affiliation delete <id> --force --json` |
| List collections | `lit collect list --json` |
| Show collection | `lit collect show "name" --json` |
| Create collection | `lit collect create "name" --json` |
| Rename collection | `lit collect rename "old-name" "new-name" --json` |
| Delete collection | `lit collect delete "name" --force --json` |
| Purge empty collections | `lit collect purge --json` |
| Add to collection | `lit collect add "name" --ids 1,2 --json` |
| Remove from collection | `lit collect remove "name" --ids 1,2 --json` |
| Get PDF path | `lit pdf path <id> --json` |
| Open PDF | `lit pdf open <id>` |
| Download PDF | `lit pdf download <id> --json` |
| Database health check | `lit db check --json` |
| Clean orphaned files | `lit db clean --json` |

For import, prefer `lit add <identifier>` unless the user explicitly asks for a legacy subcommand. The importer detects local `.pdf` / `.bib` / `.ris` files, arXiv IDs and URLs, DOI strings and URLs, OpenReview URLs, DBLP URLs, and otherwise treats the input as a title search.

PDF download uses a fallback chain when metadata is available: arXiv direct link, OpenReview direct link, Unpaywall, OpenAlex, then Semantic Scholar. PDF downloads only save/link the file. To parse downloaded PDF content, run `lit edit <id> --extract-pdf --json`; to generate notes from the PDF, run `lit edit <id> --summarize --json`.

## Workflows

### Find And Import

```bash
# 1. Import from arXiv, DOI, URL, file, or title through the unified entrypoint
lit add 1706.03762 --json
# Verify: list shows new paper with PDF

# 2. Import from DOI
lit add 10.1038/s41586-023-06139-9 --json
# Verify: metadata fetched; PDF may be downloaded through fallback providers

# 3. Bulk import from BibTeX/RIS file
lit add ./references.bib --json
# Verify: count matches expected, check errors list for duplicates
```

### Enrich Existing Metadata

```bash
# Fill only empty fields using arXiv / DOI / title metadata
lit edit 42 --fetch --json

# Overwrite existing fields only when the user asks to refresh metadata
lit edit 42 --fetch --overwrite --json
```

### Search And Export

```bash
# 1. Search papers
lit search "watermark detection" --json
# Verify: relevant results returned

# 2. Export selected papers as BibTeX
lit export --format bibtex --ids 1,3,7 --json
# Verify: content field contains valid BibTeX entries

# 3. Export a collection as Markdown
lit export --format markdown --collection "my-papers" --json
# Verify: markdown has correct headings and abstracts
```

### Build A Reading List

```bash
# 1. Create collection
lit collect create "to-read" --json
# Verify: `lit collect list --json` shows new collection

# 2. Search and add papers
lit search "diffusion model" --json
lit collect add "to-read" --ids 2,5,8 --json
# Verify: `lit filter --collection "to-read" --json` returns 3 papers

# 3. Export as reading list
lit export --format markdown --collection "to-read" --json
# Verify: markdown output contains all 3 papers
```

### Read A Paper

```bash
# 1. Show full details
lit show 42 --json
# Verify: abstract, authors, metadata visible

# 2. Get or open PDF
lit pdf path 42 --json
lit pdf open 42
# Verify: path is valid file, open launches viewer
```

### Bulk Import

```bash
# Import BibTeX (errors for duplicates are returned separately)
lit add ./exported_refs.bib --json
# Verify: check errors[] for already-existing papers

# Import RIS
lit add ./exported_refs.ris --json
```

### Manage Authors And Affiliations

Author URL fields:
- `--personal-url`: 作者的个人主页，如 GitHub Pages、个人博客等（`https://yann.lecun.com`）
- `--faculty-url`: 机构为作者建立的教职主页，如大学院系页面（`https://cs.nyu.edu/~yann`）
- `--scholar-url`: 学术档案页，如 Google Scholar、Semantic Scholar

```bash
# Create a standalone author and affiliation
lit author add "Yann LeCun" --institution "New York University" --department "CILVR Lab" --json
# Verify: response contains author.id and affiliation object

# Find an imported author and enrich metadata
lit author search "Vaswani" --json
lit author edit 7 \
  --email "..." \
  --personal-url "https://example.com" \
  --faculty-url "https://cs.university.edu/~vaswani" \
  --institution "Google" --json

# Explore institution-linked papers
lit author list --institution "Google" --json
lit filter --affiliation "Google" --json

# Merge duplicate author records after manual review
lit author merge --target 3 --sources 15 --json
```

Use merge only when the user confirms records are the same person; do not auto-merge same-name authors.

### Manage Collections

```bash
# Create and populate
lit collect create "my-collection" --json
lit collect add "my-collection" --ids 1,2,3 --json

# Verify contents
lit collect show "my-collection" --json

# Rename if needed
lit collect rename "my-collection" "important-papers" --json

# Remove papers
lit collect remove "important-papers" --ids 3 --json

# Clean up empty collections later
lit collect purge --json
```

## Reference

| File | Contents |
|------|----------|
| [references/schema.md](references/schema.md) | JSON object schemas returned by `--json` and edge-case notes |
| [references/config.md](references/config.md) | Configuration files (`config.toml` / `auth.toml`): locations, all fields, defaults |
| [references/compatibility.md](references/compatibility.md) | Backward-compatible explicit `lit add` subcommands retained for scripts |
| [references/db.md](references/db.md) | SQLite schema: all tables, columns, types, constraints, and ER summary |
| [scripts/config.example.toml](scripts/config.example.toml) | Ready-to-copy general config template |
| [scripts/auth.example.toml](scripts/auth.example.toml) | Ready-to-copy secrets template |
