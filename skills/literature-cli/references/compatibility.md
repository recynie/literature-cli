# Compatibility Reference

Prefer the unified entrypoint in new workflows:

```bash
lit add <identifier-or-path-or-title> --json
```

The following explicit source subcommands are retained for backward compatibility with older scripts and for cases where the user asks for a specific backend.

| Source | Compatible command |
|--------|--------------------|
| arXiv | `lit add arxiv <id-or-url> --json` |
| DBLP | `lit add dblp <url-or-key> --json` |
| OpenReview | `lit add openreview <id-or-url> --json` |
| DOI | `lit add doi <doi-or-url> --json` |
| Local PDF | `lit add pdf <path> --json` |
| BibTeX | `lit add bib <path> --json` |
| RIS | `lit add ris <path> --json` |
| Manual placeholder | `lit add manual --title "..." --json` |

Use these commands only when preserving old automation or when source dispatch must be explicit. Otherwise use `lit add <identifier> --json` so the CLI can apply source detection, metadata fallback, and PDF fallback consistently.
