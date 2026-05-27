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
  "preprint_id": "arXiv 1706.03762",
  "category": "cs.CL",
  "url": "https://arxiv.org/abs/1706.03762",
  "pdf_path": "/home/user/.papercli/pdfs/vaswani2017attention.pdf",
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

- `lit add pdf`, `lit edit --extract-pdf`, and `lit edit --summarize` require `OPENAI_API_KEY` to be set in `.env`.
- `lit add arxiv` and `lit add openreview` download PDFs and may take longer on slow networks.
- `lit add bib` and `lit add ris` return `errors` for failed entries while importing valid ones.
- `lit delete` removes linked local PDF files. Use `--force` in automated workflows.
- All mutating commands return `"ok": true/false` — check this before proceeding with the next step.
