---
name: literature-cli
description: "Manage research papers from the command line: import (arXiv/DOI/BibTeX/RIS/manual/PDF), search, filter, edit, export (BibTeX/Markdown/IEEE/HTML/JSON), collections, and database maintenance. Use when the user mentions papers, citations, arXiv IDs, DOIs, BibTeX, RIS, literature search, paper organization, reference management, or bibliography export."
---

# LiteratureCLI

Use `lit` for academic paper management. Prefer `--json` for all commands whose output must be parsed; human-readable output is for display only.

## Routing

| User intent | Command |
|---|---|
| Import from arXiv | `lit add arxiv <id-or-url> --json` |
| Import from DBLP | `lit add dblp <url> --json` |
| Import from OpenReview | `lit add openreview <id-or-url> --json` |
| Import from DOI | `lit add doi <doi> --json` |
| Import local PDF | `lit add pdf <path> --json` |
| Manual entry | `lit add manual --title "..." --json` |
| Bulk import BibTeX | `lit add bib <path> --json` |
| Bulk import RIS | `lit add ris <path> --json` |
| Search papers | `lit search "<query>" --json` |
| Fuzzy search | `lit search "<query>" --fuzzy --threshold 60 --json` |
| Filter papers | `lit filter --author/--year/--year-range/--venue/--type/--collection/--query --json` |
| List papers | `lit list --json` |
| Show details | `lit show <id> --json` |
| Edit metadata | `lit edit <id> --title/--venue-full/--venue-acronym/--paper-type/--doi/--url/--notes/--year <value> --json` |
| Extract PDF metadata | `lit edit <id> --extract-pdf --json` (needs OPENAI_API_KEY) |
| Summarize paper | `lit edit <id> --summarize --json` (needs OPENAI_API_KEY) |
| Delete papers | `lit delete <id> --force --json` or `lit delete --ids 1,2,3 --force --json` |
| Export citations | `lit export --format bibtex/ieee/markdown/html/json --ids 1,2 --json` |
| Export by collection | `lit export --format bibtex --collection "name" --json` |
| Export to file | `lit export --format bibtex --output /path/to/file --ids 1,2 --json` |
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

## Workflows

### Find And Import

```bash
# 1. Import from arXiv
lit add arxiv 1706.03762 --json
# Verify: list shows new paper with PDF

# 2. Import from DOI
lit add doi 10.1038/s41586-023-06139-9 --json
# Verify: metadata fetched from Crossref

# 3. Bulk import from BibTeX/RIS file
lit add bib ./references.bib --json
# Verify: count matches expected, check errors list for duplicates
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
lit add bib ./exported_refs.bib --json
# Verify: check errors[] for already-existing papers

# Import RIS
lit add ris ./exported_refs.ris --json
```

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

See [REFERENCE.md](REFERENCE.md) for JSON object schemas and notes.
