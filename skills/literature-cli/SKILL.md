---
name: literature-cli
description: Manage research papers from the command line. Use when the user needs to add, search, export, edit, delete, or organize academic papers and citations with LiteratureCLI. Supports arXiv, DBLP, OpenReview, DOI, local PDF, BibTeX, RIS, collection, PDF path, and database maintenance workflows.
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
| Bulk import BibTeX | `lit add bib <path> --json` |
| Bulk import RIS | `lit add ris <path> --json` |
| Search papers | `lit search "<query>" --json` |
| Fuzzy search | `lit search "<query>" --fuzzy --threshold 60 --json` |
| Filter papers | `lit filter --author/--year/--year-range/--venue/--type/--collection --json` |
| List papers | `lit list --json` |
| Show details | `lit show <id> --json` |
| Edit metadata | `lit edit <id> --<field> <value> --json` |
| Delete papers | `lit delete <id> --force --json` or `lit delete --ids 1,2,3 --force --json` |
| Export citations | `lit export --format bibtex --ids 1,2 --json` |
| List collections | `lit collect list --json` |
| Create collection | `lit collect create "<name>" --json` |
| Add to collection | `lit collect add "<name>" --ids 1,2 --json` |
| Remove from collection | `lit collect remove "<name>" --ids 1,2 --json` |
| Get PDF path | `lit pdf path <id> --json` |
| Open PDF | `lit pdf open <id>` |
| Database check | `lit db check --json` |

## Workflows

### Find And Import

```bash
lit add arxiv 1706.03762 --json
lit add dblp https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17 --json
```

### Search And Export

```bash
lit search "vision transformer" --json
lit export --format bibtex --ids 1,3,7 --json
lit export --format bibtex --collection "my-papers"
```

### Build A Reading List

```bash
lit collect create "to-read" --json
lit search "diffusion model" --json
lit collect add "to-read" --ids 2,5,8 --json
lit export --format markdown --collection "to-read"
```

### Read A Paper

```bash
lit show 42 --json
lit pdf path 42 --json
```

### Bulk Import

```bash
lit add bib ./exported_refs.bib --json
lit add ris ./exported_refs.ris --json
```

## JSON Objects

Paper objects include:

```json
{
  "id": 42,
  "title": "Attention Is All You Need",
  "authors": ["Ashish Vaswani"],
  "year": 2017,
  "venue_full": "Neural Information Processing Systems",
  "venue_acronym": "NeurIPS",
  "paper_type": "conference",
  "abstract": "...",
  "notes": "...",
  "doi": null,
  "preprint_id": "arXiv 1706.03762",
  "category": "cs.CL",
  "url": "https://arxiv.org/abs/1706.03762",
  "pdf_path": "/home/user/.papercli/pdfs/vaswani2017attention.pdf",
  "collections": ["transformers"],
  "added_date": "2024-01-01T00:00:00"
}
```

Collection objects include:

```json
{
  "id": 3,
  "name": "transformers",
  "paper_count": 12,
  "created_at": "2024-01-01T00:00:00"
}
```

## Notes

- `lit add pdf`, `lit edit --extract-pdf`, and `lit edit --summarize` require `OPENAI_API_KEY`.
- `lit add arxiv` and `lit add openreview` download PDFs and may take longer on slow networks.
- `lit add bib` and `lit add ris` return `errors` for failed entries while importing valid entries.
- `lit delete` removes linked local PDF files. Use `--force` in automated workflows.
