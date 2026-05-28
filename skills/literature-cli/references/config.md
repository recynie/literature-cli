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
model    = "gpt-4o-mini"                  # Model used for PDF extraction and summarization
max_tokens  = 4000
temperature = 0.7

[litcli]
data_dir  = "~/.litcli"   # Root directory for the SQLite database and downloaded PDFs
pdf_pages = 10             # Max pages sent to the LLM when extracting PDF metadata
```

### Field Notes

| Key | Default | Description |
|-----|---------|-------------|
| `openai.base_url` | `https://api.openai.com/v1` | Any OpenAI-compatible base URL (e.g. local Ollama, Azure) |
| `openai.model` | `gpt-4o-mini` | Used by `--extract-pdf` and `--summarize`; pick a model with vision if PDFs contain figures |
| `openai.max_tokens` | `4000` | Token budget for LLM responses |
| `openai.temperature` | `0.7` | Sampling temperature |
| `litcli.data_dir` | `~/.litcli` | Expanded at runtime; contains `papers.db` and `pdfs/` |
| `litcli.pdf_pages` | `10` | Limits pages parsed per PDF to control cost and latency |

---

## auth.toml

Secrets only.

```toml
[openai]
api_key = "sk-..."
```

The API key can also be supplied via the `OPENAI_API_KEY` environment variable, which takes precedence over the file.

---

## data_dir Layout

```
~/.litcli/          ← data_dir
├── papers.db       ← SQLite database
└── pdfs/           ← downloaded PDF files
```

See [db.md](db.md) for the database schema.
