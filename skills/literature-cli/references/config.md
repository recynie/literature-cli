# Configuration Reference

LiteratureCLI uses two separate TOML files to separate shareable settings from secrets.

## File Locations

Config files are loaded in order — project-level overrides user-level:

| File | Purpose |
|------|---------|
| `~/.config/litcli/config.toml` | User-level general settings |
| `~/.config/litcli/auth.toml` | User-level secrets |
| `.litcli/config.toml` | Project-level general settings |
| `.litcli/auth.toml` | Project-level secrets |

Example files are provided in the project at `.litcli/config.example.toml` and `.litcli/auth.example.toml`.

---

## config.toml

General settings.

```toml
[openai]
base_url = "https://api.openai.com/v1"   # OpenAI-compatible endpoint
model    = "gpt-4o-mini"                  # Model used for summarization and venue normalization
max_tokens  = 4000
temperature = 0.7

[litcli]
data_dir  = "~/.litcli"   # Root directory for the SQLite database and downloaded PDFs
pdf_pages = 10             # Max PDF pages used when generating summaries

[services]
unpaywall_email = "you@example.com"      # Optional, used for Unpaywall requests
openalex_email = "you@example.com"       # Optional, enables OpenAlex polite pool
# semantic_scholar_api_key = ""          # Optional, raises S2 rate limits

[mineru]
# Optional MinerU PDF parsing settings.
# model: "vlm" (default, best quality) | "pipeline" | "html"
model = "vlm"
ocr = true
language = "en"
```

### Field Notes

| Key | Default | Description |
|-----|---------|-------------|
| `openai.base_url` | `https://api.openai.com/v1` | Any OpenAI-compatible base URL (e.g. local Ollama, Azure) |
| `openai.model` | `gpt-4o-mini` | Used by `--summarize` and DBLP venue normalization |
| `openai.max_tokens` | `4000` | Token budget for LLM responses |
| `openai.temperature` | `0.7` | Sampling temperature |
| `litcli.data_dir` | `~/.litcli` | Expanded at runtime; contains `papers.db` and `pdfs/` |
| `litcli.pdf_pages` | `10` | Limits pages parsed per PDF to control cost and latency |
| `services.unpaywall_email` | — | Optional email for Unpaywall PDF fallback |
| `services.openalex_email` | — | Optional email for OpenAlex polite pool |
| `services.semantic_scholar_api_key` | — | Optional Semantic Scholar API key for higher rate limits |
| `mineru.api_key` | — | Optional MinerU API key for PDF parsing |
| `mineru.model` | `vlm` | MinerU model (`vlm`, `pipeline`, `html`) |
| `mineru.ocr` | `true` | Whether to enable OCR for MinerU |
| `mineru.language` | `en` | MinerU language code |

---

## auth.toml

Secrets only.

```toml
[openai]
api_key = "sk-..."

[mineru]
api_key = "mk-..."
```

The API key can also be supplied via the `OPENAI_API_KEY` environment variable, which takes precedence over the file. Service settings can also be supplied with `UNPAYWALL_EMAIL`, `OPENALEX_EMAIL`, and `SEMANTIC_SCHOLAR_API_KEY`.

---

## data_dir Layout

```
~/.litcli/          ← data_dir
├── papers.db       ← SQLite database
└── pdfs/           ← downloaded PDF files
```

See [db.md](db.md) for the database schema.
