# LiteratureCLI Reference

## JSON Objects

### Paper object

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
  "arxiv_url": "https://arxiv.org/abs/1706.03762",
  "openreview_url": null,
  "dblp_url": null,
  "openalex_url": null,
  "semantic_scholar_url": null,
  "category": "cs.CL",
  "url": "https://arxiv.org/abs/1706.03762",
  "pdf_path": "/home/user/.litcli/pdfs/vaswani2017attention.pdf",
  "collections": ["transformers"],
  "added_date": "2024-01-01T00:00:00"
}
```

### Collection object

```json
{
  "id": 3,
  "name": "transformers",
  "paper_count": 12,
  "created_at": "2024-01-01T00:00:00"
}
```

## Notes

- Prefer `lit add <identifier-or-path-or-title> --json` for imports. It detects PDF/BibTeX/RIS files, arXiv, DOI, OpenReview, DBLP, and title search.
- By default, platform-backed identifier fields are exposed as URLs. Use `--key` on read/list/search/show commands to request raw IDs/keys instead.
- `lit edit --summarize` requires an OpenAI API key from the shell environment, project `.litcli/auth.toml`, or `~/.config/litcli/auth.toml`.
- `lit add <path.pdf>` imports a local PDF and creates a minimal record; it does not extract PDF metadata.
- Imports with available metadata may download PDFs through arXiv, OpenReview, Unpaywall, OpenAlex, or Semantic Scholar and may take longer on slow networks.
- `lit add <path.bib>` and `lit add <path.ris>` return `errors` for failed entries while importing valid ones.
- `lit edit <id> --fetch` fills missing fields only; add `--overwrite` only when the user explicitly wants remote metadata to replace existing values.
- `lit delete` removes linked local PDF files. Use `--force` in automated workflows.
- All mutating commands return `"ok": true/false` — check this before proceeding with the next step.
