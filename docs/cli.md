# CLI 接口

## 概览

`lit` 是 LiteratureCLI 的命令行入口，基于 `typer` 构建。所有命令默认输出 human-readable 文本（基于 `rich`），加 `--json` 输出结构化 JSON，供 agent 解析。

全局 `--json` 可在顶层设置，对所有子命令生效：

```bash
lit --json list
lit --json search "transformer"
```

---

## 安装与入口

```bash
# 开发模式
uv pip install -e ".[dev]"

# 全局安装
uv tool install .

lit --help
```

入口点：`lit/main.py` → `typer` app，子命令注册在 `lit/commands/` 下。

---

## JSON 输出规范

### 成功（单篇论文）
```json
{
  "ok": true,
  "paper": {
    "id": 42,
    "title": "Attention Is All You Need",
    "authors": ["Ashish Vaswani", "Noam Shazeer"],
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
    "pdf_path": "/home/user/.litcli/pdfs/vaswani2017attention.pdf",
    "collections": ["transformers", "to-read"],
    "added_date": "2024-01-01T00:00:00",
    "modified_date": "2024-01-01T00:00:00"
  }
}
```

### 成功（多篇论文）
```json
{
  "ok": true,
  "papers": [ ...paper objects... ],
  "count": 3
}
```

### 错误
```json
{
  "ok": false,
  "error": "Paper not found on arXiv",
  "code": "NOT_FOUND"
}
```

错误码：`NOT_FOUND` | `ALREADY_EXISTS` | `INVALID_INPUT` | `NETWORK_ERROR` | `LLM_ERROR`

---

## 命令参考

### `lit add` — 导入论文

```bash
# 统一入口：自动识别来源
lit add 1706.03762 [--json]
lit add https://arxiv.org/abs/1706.03762 [--json]
lit add 10.5555/3295222.3295349 [--json]
lit add https://doi.org/10.5555/3295222.3295349 [--json]
lit add https://openreview.net/forum?id=abc123XYZ [--json]
lit add https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17 [--json]
lit add "Attention Is All You Need" [--json]
lit add ./paper.pdf [--json]
lit add ./refs.bib [--json]
lit add ./refs.ris [--json]

# arXiv（ID 或完整 URL）
lit add arxiv 1706.03762 [--json]
lit add arxiv https://arxiv.org/abs/1706.03762 [--json]

# DBLP
lit add dblp https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17 [--json]

# OpenReview（ID 或完整 URL）
lit add openreview abc123XYZ [--json]
lit add openreview https://openreview.net/forum?id=abc123XYZ [--json]

# DOI
lit add doi 10.5555/3295222.3295349 [--json]

# 本地 PDF（LLM 提取元数据，需要 OPENAI_API_KEY）
lit add pdf ./paper.pdf [--json]

# BibTeX 文件（批量）
lit add bib ./refs.bib [--json]

# RIS 文件（批量）
lit add ris ./refs.ris [--json]

# 手动创建
lit add manual --title "Paper Title" [--json]
```

**返回**：单篇返回 paper 对象；批量（bib/ris）返回 `{ "ok": true, "papers": [...], "errors": [...], "count": N }`

`lit add arxiv`、`lit add openreview`、`lit add doi` 以及统一入口会按可用 metadata 尝试下载 PDF。fallback 顺序为 arXiv 直链、OpenReview 直链、Unpaywall、OpenAlex、Semantic Scholar，返回结果中含 `pdf_path` 和 `pdf_error` 字段。

---

### `lit search` — 搜索

```bash
# 全字段搜索
lit search "attention mechanism" [--json]

# 指定字段（title、abstract、venue、authors、notes）
lit search "transformer" --fields title,abstract [--json]

# 模糊搜索
lit search "atention" --fuzzy [--threshold 60] [--json]
```

---

### `lit filter` — 过滤

```bash
lit filter --author "Vaswani" [--json]
lit filter --year 2017 [--json]
lit filter --year-range 2020-2023 [--json]
lit filter --venue "NeurIPS" [--json]
lit filter --type conference [--json]   # conference|journal|preprint|workshop
lit filter --collection "to-read" [--json]
lit filter --affiliation "MIT" [--json]
lit filter --query "diffusion" [--json]  # 全字段关键词过滤

# 组合过滤
lit filter --author "LeCun" --year 2020 --type journal [--json]
```

---

### `lit list` — 列出所有论文

```bash
lit list [--json]
lit list --limit 20 [--json]
lit list --sort year|title|added_date [--json]
```

默认按 `added_date` 降序排列。

---

### `lit show` — 论文详情

```bash
lit show 42 [--json]
```

**返回**：完整 paper 对象，含 abstract、notes、collections。

---

### `lit edit` — 编辑元数据

```bash
# 编辑单个字段
lit edit 42 --title "New Title"
lit edit 42 --notes "Key insight: ..."
lit edit 42 --year 2023
lit edit 42 --venue-full "International Conference on Machine Learning"
lit edit 42 --venue-acronym "ICML"
lit edit 42 --paper-type conference
lit edit 42 --doi "10.1145/..."
lit edit 42 --url "https://..."
lit edit 42 --pdf-path "/path/to/paper.pdf"

# LLM 重新提取 PDF 元数据（需要 OPENAI_API_KEY，论文须有关联 PDF）
lit edit 42 --extract-pdf [--json]

# 根据已有 arXiv ID / DOI / 标题补全空字段；--overwrite 覆盖已有值
lit edit 42 --fetch [--json]
lit edit 42 --fetch --overwrite [--json]

# LLM 生成摘要写入 notes（需要 OPENAI_API_KEY，论文须有关联 PDF）
lit edit 42 --summarize [--json]
```

---

### `lit delete` — 删除

```bash
# 删除单篇（交互确认）
lit delete 42

# 批量删除
lit delete --ids 1,2,3

# 跳过确认（自动化场景）
lit delete 42 --force
lit delete --ids 1,2,3 --force [--json]
```

同时删除关联的本地 PDF 文件，不可恢复。

---

### `lit export` — 导出

```bash
# 格式：bibtex | ieee | markdown | html | json
lit export --format bibtex                        # 全库
lit export --format bibtex --ids 1,3,7            # 指定 ID
lit export --format bibtex --collection "to-read" # 指定 collection

# 输出到文件
lit export --format bibtex --output refs.bib

# JSON 输出（--json 时 content 字段为解析后的对象）
lit export --format json --json
```

---

### `lit author` — 作者管理

```bash
lit author list [--json]
lit author list --institution "MIT" [--json]
lit author list --department "CSAIL" [--json]
lit author list --has-email --has-url [--json]
lit author list --no-affiliation [--json]

lit author search "Hinton" [--json]
lit author show 7 [--json]

lit author add "Geoffrey Hinton" \
  --first-name Geoffrey \
  --last-name Hinton \
  --email "hinton@cs.toronto.edu" \
  --personal-url "https://www.cs.toronto.edu/~hinton/" \
  --scholar-url "https://scholar.google.com/citations?user=JicYPdAAAAAJ" \
  --orcid "0000-0001-2345-6789" \
  --institution "University of Toronto" \
  --department "Department of Computer Science" \
  [--json]

lit author edit 7 --email "" [--json]  # 传空字符串清除字段
lit author edit 7 --institution "Google DeepMind" --department "" [--json]
lit author delete 7 [--force] [--json]
lit author merge --target 3 --sources 15,18 [--json]
```

`lit author show` 返回 author 对象和该作者关联论文列表。未加 `--force` 时，删除有关联论文的作者会被拒绝；`--force` 会解除论文关联后删除作者。

Author JSON schema：

```json
{
  "id": 1,
  "full_name": "Geoffrey Hinton",
  "first_name": "Geoffrey",
  "last_name": "Hinton",
  "email": "hinton@cs.toronto.edu",
  "personal_url": "https://www.cs.toronto.edu/~hinton/",
  "scholar_url": "https://scholar.google.com/citations?user=JicYPdAAAAAJ",
  "orcid": "0000-0001-2345-6789",
  "affiliation": {
    "id": 3,
    "institution": "University of Toronto",
    "department": "Department of Computer Science",
    "url": "https://www.cs.toronto.edu",
    "author_count": 5
  },
  "paper_count": 12
}
```

---

### `lit affiliation` — 机构管理

```bash
lit affiliation list [--json]
lit affiliation show 3 [--json]
lit affiliation add "Tsinghua University" \
  --department "Department of Computer Science" \
  --url "https://www.cs.tsinghua.edu.cn" \
  [--json]
lit affiliation edit 3 --institution "..." --department "..." --url "..." [--json]
lit affiliation delete 3 [--force] [--json]
```

Affiliation JSON schema：

```json
{
  "id": 3,
  "institution": "University of Toronto",
  "department": "Department of Computer Science",
  "url": "https://www.cs.toronto.edu",
  "author_count": 5
}
```

---

### `lit collect` — Collection 管理

```bash
lit collect list [--json]
lit collect show "deep-learning" [--json]
lit collect create "deep-learning" [--json]
lit collect rename "deep-learning" "dl-papers" [--json]
lit collect delete "deep-learning" [--force] [--json]

# 添加/移除论文
lit collect add "deep-learning" --ids 1,2,3 [--json]
lit collect remove "deep-learning" --ids 1,2,3 [--json]

# 清理空 collection
lit collect purge [--json]
```

`lit collect show` 返回 collection 元数据 + 该 collection 下所有论文列表。

---

### `lit pdf` — PDF 操作

```bash
# 获取 PDF 绝对路径
lit pdf path 42 [--json]

# 用系统默认程序打开
lit pdf open 42

# 重新下载（支持 arXiv、OpenReview、DOI fallback、直接 PDF URL）
lit pdf download 42 [--json]
```

---

### `lit db` — 数据库维护

```bash
# 检查孤立记录和文件
lit db check [--json]

# 清理孤立 PDF 文件、数据库记录、修复绝对路径等
lit db clean [--json]
```

`lit db clean` 执行：清理孤立数据库记录、孤立 PDF 文件、孤立 HTML 文件、修复绝对 PDF 路径、规范化 PDF 文件名。

---

## 实现说明

### 目录结构

```
lit/
├── main.py              # typer app，注册所有子命令
├── config.py            # JSON 配置加载（用户级 + 项目级）
├── output.py            # JSON / human-readable 统一输出（rich）
├── logger.py            # CliLogger，实现 _add_log / notify 接口
└── commands/
    ├── __init__.py      # 共享 helper：service 初始化、ID 解析、错误处理
    ├── add.py
    ├── author.py
    ├── affiliation.py
    ├── search.py
    ├── list.py
    ├── show.py
    ├── edit.py
    ├── delete.py
    ├── export.py
    ├── collect.py
    ├── pdf.py
    └── db.py
```

### CliLogger

所有服务类需要一个 `app` 参数用于日志和通知，CLI 层传入 `CliLogger`：

```python
# lit/logger.py
class CliLogger:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def _add_log(self, key: str, message: str):
        logging.debug("[%s] %s", key, message)

    def notify(self, message: str, severity: str = "information"):
        if severity == "error":
            logging.error(message)
        elif severity == "warning":
            logging.warning(message)
        else:
            logging.info(message)
```

### 输出格式化

`lit/output.py` 提供两条路径：

- `--json`：`json.dumps` 输出，`default=str` 处理日期等非标准类型
- human-readable：`rich` 表格（列表）或 `Panel`（详情）

`paper_to_dict()` 将 ORM 对象转为公开 JSON schema，`pdf_path` 自动解析为绝对路径。`author_to_dict()` / `affiliation_to_dict()` 分别序列化作者与机构对象。
