# AGENTS.md

当前 workspace 是一个面向 code agent 的学术文献管理工具，提供 CLI 接口和 pi skill，支持从多个来源导入论文、检索管理和导出引用。

> **Workspace Map** 描述当前目录的文件和结构，帮助 agent 快速定位目标。当下述任意情况发生时，应更新本文件：创建文件/目录；修改文件内容使现有描述过时；移动或复制文件/目录。

---

## Virtual Environment

使用 `uv` 管理环境，Python 3.12。

```bash
# 运行命令
uv run python ...
uv run pytest ...

# 安装依赖
uv pip install -e ".[dev]"
```

---

## Workspace Map

### 根目录

| 路径 | 描述 |
|------|------|
| `README.md` | 项目概览、快速开始、功能列表 |
| `pyproject.toml` | 项目配置，入口点 `lit = "lit.main:app"` |
| `requirements.txt` | Python 依赖列表 |
| `.gitignore` | Git 忽略规则，排除虚拟环境、缓存、本地配置和运行时数据 |
| `.litcli/config.example.toml` | 通用配置模板（可提交）：model、base_url、data_dir、免费 API email/key 等 |
| `.litcli/auth.example.toml` | 敏感配置模板（不可提交）：api_key |
| `.venv/` | uv 虚拟环境（不提交） |

### `ng/` — 核心业务逻辑

从 papercli 移植并精简，移除了 TUI、同步、chat 等功能。

| 路径 | 描述 |
|------|------|
| `ng/db/models.py` | SQLAlchemy ORM 模型：Paper、Author、Affiliation、Collection、PaperAuthor |
| `ng/db/database.py` | SQLite 连接管理，`get_db_session()` context manager |
| `ng/alembic/` | Alembic schema 迁移脚本，含作者/机构 schema 变更 |
| `ng/services/arxiv_utils.py` | arXiv 标识符集中处理：ID 清洗、从 Paper 提取 ID、判断是否 arXiv 论文、构建 PDF URL |
| `ng/services/platform_ids.py` | 平台标识符工具：规范化/解析 arXiv、OpenReview、DBLP、OpenAlex、Semantic Scholar、ORCID，并派生平台 URL |
| `ng/services/metadata.py` | 元数据提取：arXiv API、DBLP、OpenReview、DOI/Crossref、PDF（LLM）、BibTeX、RIS |
| `ng/services/identifier.py` | 统一导入入口 identifier 识别：文件、arXiv、DOI、OpenReview、DBLP、标题 |
| `ng/services/openalex.py` | OpenAlex API 封装：按 DOI/标题检索 metadata、提取开放 PDF URL |
| `ng/services/semantic_scholar.py` | Semantic Scholar API 封装：按 DOI/标题检索 metadata、提取开放 PDF URL |
| `ng/services/unpaywall.py` | Unpaywall API 封装：按 DOI 获取开放 PDF URL |
| `ng/services/fetch.py` | `lit edit --fetch` 补全逻辑：按 arXiv/DOI/标题拉取远端 metadata，只填空字段或 overwrite |
| `ng/services/references.py` | Crossref 参考文献检索：按本地论文、DOI 或标题匹配 DOI 拉取 reference 列表 |
| `ng/services/add_paper.py` | 各来源论文导入逻辑，含统一 `add_by_identifier()` dispatch |
| `ng/services/paper.py` | 论文 CRUD，导入/更新作者时复用 Author 并可关联 Affiliation |
| `ng/services/author.py` | 作者 CRUD、筛选、合并、查询作者论文 |
| `ng/services/affiliation.py` | 机构 CRUD、搜索、get_or_create |
| `ng/services/search.py` | 全文搜索、模糊搜索、多字段过滤（含 affiliation） |
| `ng/services/collection.py` | Collection 增删改查，批量添加/移除论文 |
| `ng/services/export.py` | 导出：BibTeX、IEEE、Markdown、HTML、JSON |
| `ng/services/pdf.py` | PDF 下载、本地路径管理 |
| `ng/services/logger.py` | 服务层日志协议 `Logger` 与空实现 `NullLogger` |
| `ng/services/prompts.py` | LLM prompt 模板（元数据提取、venue 规范化） |
| `ng/services/llm_utils.py` | OpenAI 参数构建工具 |
| `ng/services/constants.py` | 默认模型名、页数限制等常量 |
| `ng/services/utils.py` | `normalize_paper_data()`、`fix_broken_lines()` 等工具函数 |
| `ng/services/validation.py` | 输入数据校验 |
| `ng/services/formatting.py` | 作者名、文件大小等显示格式化 |
| `ng/services/http_utils.py` | HTTP 请求封装 |
| `ng/services/system.py` | 系统工具：剪贴板、文件打开、PDF fallback 下载链 |
| `ng/services/database.py` | 数据库健康检查：孤立文件检测与清理 |

### `lit/` — CLI 层

基于 `typer` 的命令行接口，调用 `ng/services/` 完成实际操作。

| 路径 | 描述 |
|------|------|
| `lit/__init__.py` | CLI package init |
| `lit/config.py` | TOML 配置加载，分 `config.toml`（通用）和 `auth.toml`（敏感），支持用户级（`~/.config/litcli/`）与项目级（`.litcli/`） |
| `lit/main.py` | typer app 入口，加载用户级与项目级配置、初始化数据库、注册所有子命令 |
| `lit/logger.py` | `CliLogger`，实现 `_add_log`/`notify` 接口替代 TUI app |
| `lit/output.py` | JSON / human-readable 统一输出，含 Paper / Author / Affiliation / Collection 序列化；默认平台 URL 输出，`--key` 可切换原始 ID/key |
| `lit/commands/__init__.py` | 子命令共享 helper：service 初始化、ID 解析、错误输出 |
| `lit/commands/add.py` | `lit add` 来源导入：统一 identifier 入口和 arXiv、DBLP、OpenReview、DOI、PDF、BibTeX、RIS、manual 子命令 |
| `lit/commands/search.py` | `lit search` 和 `lit filter`，支持 `--affiliation` 与 `--key` |
| `lit/commands/list.py` | `lit list`，支持 `--key` |
| `lit/commands/show.py` | `lit show`，支持 `--key` |
| `lit/commands/references.py` | `lit references`，支持按本地论文 ID、DOI 或标题检索 Crossref 参考文献 |
| `lit/commands/edit.py` | `lit edit`，支持字段更新、平台标识符更新、`--fetch` 补全、PDF 元数据提取、PDF 摘要写入 notes |
| `lit/commands/delete.py` | `lit delete`，支持单个 ID、批量 `--ids` 和 `--force` |
| `lit/commands/export.py` | `lit export`，支持 BibTeX、IEEE、Markdown、HTML、JSON |
| `lit/commands/author.py` | `lit author` 作者管理：list/search/show/add/edit/delete/merge，支持作者平台 ID 字段与 `--key` |
| `lit/commands/affiliation.py` | `lit affiliation` 机构管理：list/show/add/edit/delete |
| `lit/commands/collect.py` | `lit collect` collection 管理 |
| `lit/commands/pdf.py` | `lit pdf` 路径、打开、重新下载 |
| `lit/commands/db.py` | `lit db check` / `lit db clean` |

### `skills/literature-cli/` — pi Skill

| 路径 | 描述 |
|------|------|
| `skills/literature-cli/SKILL.md` | pi skill 定义：推荐路由规则、典型工作流和使用注意事项 |
| `skills/literature-cli/references/compatibility.md` | 兼容用法参考：旧版显式 `lit add arxiv/doi/...` 子命令 |
| `skills/literature-cli/references/config.md` | skill 配置参考：TOML 文件、环境变量、免费 API 设置 |
| `skills/literature-cli/references/schema.md` | skill JSON 输出 schema 与边界说明 |
| `skills/literature-cli/scripts/config.example.toml` | skill 内置通用配置模板 |
| `skills/literature-cli/scripts/auth.example.toml` | skill 内置敏感配置模板 |

### `docs/` — 文档

| 路径 | 描述 |
|------|------|
| `docs/architecture.md` | 架构说明：目录结构、各层职责、数据流、`app` 参数约定 |
| `docs/cli.md` | CLI 命令完整设计，含 JSON 输出 schema 和实现说明 |
| `docs/skill.md` | pi skill 规范草稿：路由规则、JSON schema、工作流示例 |

### `references/` — 参考代码（只读）

| 路径 | 描述 |
|------|------|
| `references/papercli/` | papercli 原始代码，`ng/` 层的移植来源，仅供参考 |
