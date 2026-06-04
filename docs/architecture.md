# LiteratureCLI 架构说明

## 项目定位

面向 code agent 的文献管理工具。提供 CLI 接口和 pi skill，让 agent 能够导入、检索、管理和导出学术论文。

---

## 目录结构

```
LiteratureCLI/
├── ng/                         # 核心业务逻辑（从 papercli 移植并精简）
│   ├── db/                     # 数据库层
│   │   ├── models.py           # SQLAlchemy ORM 模型
│   │   └── database.py         # 连接管理、session 工厂
│   ├── services/               # 服务层
│   │   ├── metadata.py         # 元数据提取（各来源）
│   │   ├── identifier.py       # 统一导入 identifier 识别
│   │   ├── openalex.py         # OpenAlex API 封装
│   │   ├── semantic_scholar.py # Semantic Scholar API 封装
│   │   ├── unpaywall.py        # Unpaywall API 封装
│   │   ├── fetch.py            # 远端 metadata 补全
│   │   ├── references.py       # Crossref 参考文献检索
│   │   ├── add_paper.py        # 论文导入逻辑
│   │   ├── paper.py            # 论文 CRUD
│   │   ├── search.py           # 搜索与过滤
│   │   ├── collection.py       # Collection 管理
│   │   ├── export.py           # 多格式导出
│   │   ├── pdf.py              # PDF 下载与文件管理
│   │   ├── database.py         # 数据库健康检查
│   │   ├── system.py           # 系统工具（剪贴板、文件打开）
│   │   ├── validation.py       # 数据校验
│   │   ├── formatting.py       # 显示格式化
│   │   ├── utils.py            # 通用工具函数
│   │   ├── constants.py        # 常量定义
│   │   ├── http_utils.py       # HTTP 请求封装
│   │   ├── prompts.py          # LLM prompt 模板
│   │   └── llm_utils.py        # LLM 参数构建工具
│   └── alembic/                # 数据库 schema 迁移
│       ├── alembic.ini
│       ├── env.py
│       └── versions/           # 迁移脚本
├── lit/                        # CLI 层（基于 typer）
│   ├── main.py              # typer app 入口，注册所有子命令
│   ├── config.py            # TOML 配置加载，支持用户级与项目级
│   ├── logger.py            # CliLogger，实现 _add_log / notify 接口
│   ├── output.py            # JSON / human-readable 统一输出（rich）
│   └── commands/            # 各子命令实现
│       ├── __init__.py      # 共享 helper：service 初始化、ID 解析、错误输出
│       ├── add.py           # lit add（统一入口 + 旧子命令）
│       ├── search.py        # lit search / lit filter
│       ├── list.py          # lit list
│       ├── show.py          # lit show
│       ├── references.py    # lit references
│       ├── edit.py          # lit edit
│       ├── delete.py        # lit delete
│       ├── export.py        # lit export
│       ├── collect.py       # lit collect
│       ├── pdf.py           # lit pdf
│       └── db.py            # lit db
├── skills/
│   └── literature-cli/
│       ├── SKILL.md         # pi skill 定义：路由规则、典型工作流
│       └── REFERENCE.md     # JSON schema 和注意事项
├── docs/                       # 文档
├── references/                 # 参考项目（papercli 原始代码，只读）
├── .litcli/
│   ├── config.example.toml     # 通用配置示例
│   └── auth.example.toml       # 敏感配置示例
├── requirements.txt            # Python 依赖
└── pyproject.toml              # 项目配置
```

---

## 各层职责

### `ng/db/` — 数据库层

**不应修改**，直接复用 papercli 的成熟实现。

- `models.py`：定义四个核心模型
  - `Paper`：论文主体，含 UUID、标题、摘要、venue、年份、DOI、pdf_path 等字段
  - `Author`：作者，通过 `PaperAuthor` 关联表与 Paper 多对多（含顺序）
  - `Collection`：自定义分组，与 Paper 多对多
  - `PaperAuthor`：Paper-Author 关联对象，记录作者顺序 position
- `database.py`：SQLite 连接管理，提供 `get_db_session()` context manager

数据存储路径默认 `~/.litcli/`，可通过 `LITCLI_DATA_DIR` 环境变量或 TOML 配置覆盖。
CLI 启动时会读取用户级 `~/.config/litcli/config.toml` / `auth.toml` 和当前目录或父目录中的项目级 `.litcli/config.toml` / `auth.toml`。

### `ng/alembic/` — Schema 迁移

使用 Alembic 管理数据库版本，共 4 个迁移：

1. `b0c3d711` — 初始 schema（papers、authors、collections、paper_authors、paper_collections）
2. `10f8534b` — 添加 UUID 字段（用于跨设备唯一标识）
3. `2be4589a` — collections 添加 last_modified
4. `03b4cd44` — papers 添加 html_snapshot_path（保留字段，暂不使用）

### `ng/services/` — 服务层

业务逻辑的核心，CLI 层直接调用这里的服务类。

#### 元数据提取

`metadata.py` — `MetadataExtractor` 类，按来源分两类策略：

| 来源 | 策略 | 外部依赖 |
|------|------|---------|
| arXiv | arXiv Atom API，解析 XML | 无 |
| DBLP | 转换为 `.bib` 端点，复用 BibTeX 解析 | OpenAI（venue 规范化）|
| OpenReview | OpenReview API v2/v1，JSON 解析 | OpenAI（venue 规范化）|
| DOI | Crossref API，JSON 解析 | 无 |
| DOI fallback | OpenAlex、Semantic Scholar | 无（S2 key 可选）|
| 标题搜索 | OpenAlex、Semantic Scholar | 无（S2 key 可选）|
| 本地 PDF | PyPDF2 提取文本，LLM 解析元数据 | OpenAI |
| BibTeX 文件 | bibtexparser 库批量解析 | 无 |
| RIS 文件 | rispy 库批量解析 | 无 |

LLM 依赖：需要 `OPENAI_API_KEY`，模型通过 `OPENAI_MODEL` 配置（默认 `gpt-4o-mini`）。

#### 论文导入

`add_paper.py` — `AddPaperService` 类，每种来源对应一个方法：

- `add_arxiv_paper(arxiv_id)` — 提取元数据 + 下载 PDF
- `add_dblp_paper(dblp_url)` — 提取元数据（内部规范化保存 `dblp_key`，无 PDF）
- `add_openreview_paper(openreview_id)` — 提取元数据 + 下载 PDF
- `add_doi_paper(doi)` — Crossref/OpenAlex/Semantic Scholar 提取元数据 + PDF fallback
- `add_by_identifier(raw_input)` — 统一入口 dispatch，自动识别文件、arXiv、DOI、OpenReview、DBLP、标题
- `add_title_paper(title)` — OpenAlex/Semantic Scholar 标题搜索导入
- `add_pdf_paper_async(pdf_path)` — 复制 PDF + LLM 提取元数据
- `add_bib_papers(bib_path)` — 批量导入，返回 `(papers, errors)`
- `add_ris_papers(ris_path)` — 批量导入，返回 `(papers, errors)`
- `add_manual_paper(title)` — 手动创建占位条目

#### 引用检索

`references.py` — `ReferenceService` 基于 Crossref 检索单篇论文的参考文献列表：

- `references_for_paper(paper_id)` — 给定本地论文，优先使用 DOI；没有 DOI 时用标题 `query.bibliographic` 匹配 Crossref DOI
- `references_for_doi(doi)` — 调用 Crossref `GET /works/{doi}` 并解析 `reference`
- `references_for_title(title)` — 先按标题匹配 DOI，再拉取完整 reference 列表

Crossref `reference` 字段是稀疏结构，服务层只提取常见字段并保留每条引用的原始 `raw` 内容；缺失 DOI 或标题等字段不视为错误。

#### 论文管理

`paper.py` — `PaperService` 类：CRUD 操作，处理 Author 关联和 PDF 文件联动；论文侧去重优先使用 `arxiv_id` / DOI / 标题。

`search.py` — `SearchService` 类：
- `search_papers(query, fields)` — SQLAlchemy `ilike` 精确匹配，支持 title/abstract/venue/authors/notes
- `fuzzy_search_papers(query, threshold)` — fuzzywuzzy 编辑距离匹配
- `filter_papers(filters)` — 多条件组合过滤（year、paper_type、venue、collection、author）

`collection.py` — `CollectionService` 类：Collection 增删改查，批量添加/移除论文。

#### 导出

`export.py` — 纯函数模块，5 种格式：

- `export_to_bibtex(papers)` — 标准 BibTeX，key 格式 `lastname+year+firstword`
- `export_to_ieee(papers)` — IEEE 引用格式
- `export_to_markdown(papers)` — Markdown 列表
- `export_to_html(papers)` — 带内联 CSS 的静态 HTML
- `export_to_json(papers)` — 完整字段 JSON

#### PDF 管理

`pdf.py` — `PDFManager` 类：PDF 文件路径管理、下载、复制到数据目录。存储路径为相对路径，绝对路径在运行时动态解析。

`system.py` — `SystemService.download_pdf()` 负责 PDF fallback 候选链：arXiv 直链、OpenReview 直链、Unpaywall、OpenAlex、Semantic Scholar。平台 ID 的规范化与 URL 派生集中在 `platform_ids.py`。

#### 工具模块

- `constants.py` — 默认模型名、页数限制等常量
- `prompts.py` — 所有 LLM prompt 模板（元数据提取、venue 规范化）
- `llm_utils.py` — OpenAI 参数构建，处理不同模型的参数差异
- `http_utils.py` — requests 封装，统一超时和错误处理
- `validation.py` — 输入数据校验
- `formatting.py` — 作者名、文件大小等显示格式化
- `utils.py` — `normalize_paper_data()`（统一字段格式）、`fix_broken_lines()`（修复 PDF 换行）
- `identifier.py` — `detect()` 统一识别 `lit add <identifier>` 输入类型
- `fetch.py` — `FetchMetadataService.fetch_metadata_for_paper()` 只填空字段；`--overwrite` 时覆盖已有值

### `lit/` — CLI 层

基于 `typer` 构建，每个子命令对应 `commands/` 下一个文件，直接调用 `ng/services/` 的服务类。

所有命令支持 `--json` 输出结构化数据，默认输出 human-readable 文本（基于 `rich`）。

全局 `--json` 可在 `lit --json <command>` 层面设置，也可在各子命令单独传入。

详见 [cli.md](cli.md)。

### `skills/literature-cli/` — pi Skill

`SKILL.md` 定义 agent 使用规范：路由规则、典型工作流。`REFERENCE.md` 包含 JSON schema 和注意事项。

详见 [skill.md](skill.md)。

---

## 服务层的 `app` 参数

papercli 原始代码中，所有服务类接受一个 `app` 参数（Textual TUI 实例），用于：
- `app._add_log(key, message)` — 写日志
- `app.notify(message)` — 显示通知

CLI 实现时，传入一个简单的 logger 对象替代，实现相同接口：

```python
class CliLogger:
    def _add_log(self, key: str, message: str):
        logging.debug(f"[{key}] {message}")
    def notify(self, message: str, severity: str = "information"):
        if severity == "error":
            logging.error(message)
```

---

## 配置

CLI 启动时按以下优先级加载配置，后者作为默认值，前者覆盖后者：

1. 已导出的环境变量，例如 `export OPENAI_API_KEY=...`
2. 当前目录或父目录中的项目级 `.litcli/config.toml` / `.litcli/auth.toml`
3. 用户级 `~/.config/litcli/config.toml` / `~/.config/litcli/auth.toml`

TOML 配置示例见 `.litcli/config.example.toml` 和 `.litcli/auth.example.toml`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | — | 必填，用于 PDF 元数据提取和 venue 规范化 |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM 模型 |
| `OPENAI_MAX_TOKENS` | `4000` | 最大输出 token |
| `OPENAI_TEMPERATURE` | `0.7` | 温度（元数据提取强制为 0）|
| `LITCLI_DATA_DIR` | `~/.litcli` | 数据目录（数据库 + PDF）|
| `LITCLI_PDF_PAGES` | `10` | PDF 元数据提取读取页数 |
| `UNPAYWALL_EMAIL` | — | Unpaywall polite email |
| `OPENALEX_EMAIL` | — | OpenAlex polite pool email |
| `SEMANTIC_SCHOLAR_API_KEY` | — | Semantic Scholar 可选 API key |

---

## 数据流

```
用户 / agent
    ↓ lit <command> [--json]
lit/commands/*.py
    ↓ 调用服务
ng/services/add_paper.py | search.py | export.py ...
    ↓ 元数据提取
ng/services/metadata.py  ←→  外部 API / LLM
    ↓ 数据库读写
ng/db/database.py + models.py  →  ~/.litcli/papers.db
    ↓ PDF 文件操作
ng/services/pdf.py  →  ~/.litcli/pdfs/
```
